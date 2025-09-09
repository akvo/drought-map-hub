import { NextResponse } from "next/server";
import { auth } from "./lib";
import { USER_ROLES } from "./static/config";

const protectedRoutes = ["/profile", "/publications", "/reviews", "/settings"];
const authRoutes = ["/login"];

export default async function middleware(request) {
  const session = request.cookies.get("currentUser")?.value;
  const pathName = request.nextUrl.pathname;
  const response = NextResponse.next();

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
      }
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
