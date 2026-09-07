// client/proxy.ts
import { NextRequest, NextResponse } from "next/server";

const PROTECTED_PATHS = ["/dashboard", "/settings", "/audit"];
const PUBLIC_PATHS = ["/", "/login", "/signup", "/public"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only enforce for protected paths (prefix match)
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  if (!isProtected) {
    return NextResponse.next();
  }

  // Read HttpOnly cookie 'access_token'
  const token = request.cookies.get("access_token")?.value;

  if (!token) {
    // Redirect to login preserving original path
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Optionally, we could call an auth endpoint to validate token at the edge.
  // Keep edge logic minimal: allow request to proceed and let server-side endpoints validate token.
  return NextResponse.next();
}

// Apply middleware only to routes we care about
export const config = {
  matcher: ["/dashboard/:path*", "/settings/:path*", "/audit/:path*"],
};
