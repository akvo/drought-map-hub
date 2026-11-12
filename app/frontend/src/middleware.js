import { NextResponse } from "next/server";
import { auth } from "./lib";
import { USER_ROLES } from "./static/config";

const protectedRoutes = ["/profile", "/publications", "/reviews", "/settings"];
const authRoutes = ["/login"];
const publicRoutes = ["/", "/about", "/browse", "/compare"];

export default async function middleware(request) {
  const session = request.cookies.get("currentUser")?.value;
  const pathName = request.nextUrl.pathname;
  const response = NextResponse.next();

  // After setup (re)configuration the httpOnly appConfig cookie would otherwise
  // keep stale values (admin_label, modules, theme) for up to a day. Drop it on
  // any /setup route so the next navigation refetches fresh config.
  if (pathName.startsWith("/setup")) {
    response.cookies.delete("appConfig");
    return response;
  }

  // check if app is cofigured
  const appConfig = request.cookies.get("appConfig")?.value;
  // Refresh a stale cookie that predates the `modules` or `admin_label`
  // fields, otherwise useModule/useAdminLabel read undefined and fall back to
  // defaults. (The cookie is still set-once per its 1-day expiry for ordinary
  // value changes.)
  let needsConfig = !appConfig;
  if (appConfig) {
    try {
      const parsed = JSON.parse(appConfig);
      needsConfig = !parsed?.modules || !parsed?.admin_label;
    } catch {
      needsConfig = true;
    }
  }
  const knownRoutes = [...publicRoutes, ...protectedRoutes, ...authRoutes];
  // Prefix match so dynamic detail pages (e.g. /reviews/4) also refresh a
  // stale cookie, not just the exact list entries.
  const isKnownRoute = knownRoutes.some(
    (r) => pathName === r || (r !== "/" && pathName.startsWith(`${r}/`)),
  );
  if (needsConfig && isKnownRoute) {
    /// check if app is configured from the API
    const reqConfig = await fetch(
      `${process.env.WEBDOMAIN}/api/v1/setup/?format=json`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-Setup-Secret": process.env.SETUP_SECRET_KEY,
        },
      },
    );
    const configData = await reqConfig.json();
    if (reqConfig.ok && configData?.is_configured) {
      response.cookies.set({
        name: "appConfig",
        value: JSON.stringify(configData),
        httpOnly: true,
        expires: new Date(Date.now() + 24 * 60 * 60 * 1000), // 1 day
      });
      return response;
    }
    return NextResponse.redirect(new URL("/setup", request.url));
  }

  if (!session && protectedRoutes.includes(pathName)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (session) {
    if (authRoutes.includes(pathName)) {
      return NextResponse.redirect(new URL("/profile", request.url));
    }
    const { token: authToken, role } = await auth.decrypt(session);
    const req = await fetch(
      `${process.env.WEBDOMAIN}/api/v1/users/me?format=json`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
      },
    );
    if (!req.ok) {
      response.cookies.set({
        name: "currentUser",
        value: "",
        httpOnly: true,
        expires: new Date(0),
      });
    }

    if (
      (role !== USER_ROLES.reviewer && pathName.startsWith("/reviews")) ||
      (role !== USER_ROLES.admin &&
        (pathName.startsWith("/publications") ||
          pathName.startsWith("/settings")))
    ) {
      return NextResponse.redirect(new URL("/unauthorized", request.url));
    }
  }
  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
