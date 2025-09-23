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

  // check if app is cofigured
  const appConfig = request.cookies.get("appConfig")?.value;
  if (
    !appConfig &&
    [...publicRoutes, ...protectedRoutes, ...authRoutes].includes(pathName)
  ) {
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
    if (reqConfig.ok) {
      console.log("App is configured", configData);
      response.cookies.set({
        name: "appConfig",
        value: "configured",
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
