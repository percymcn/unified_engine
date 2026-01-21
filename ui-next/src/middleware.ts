import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Cookie name for auth token (must match lib/auth.ts)
 */
const AUTH_COOKIE_NAME = 'auth-token';

/**
 * Routes that require authentication
 */
const protectedRoutes = ['/dashboard'];

/**
 * Routes that are only accessible when NOT authenticated
 * (e.g., login page - authenticated users should be redirected to dashboard)
 */
const authRoutes = ['/login'];

/**
 * Public routes that don't require any auth checks
 */
const publicRoutes = ['/api/auth'];

/**
 * Check if a path starts with any of the given prefixes
 */
function matchesPrefix(path: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => path.startsWith(prefix));
}

/**
 * Check if a path is a protected route
 */
function isProtectedRoute(path: string): boolean {
  return protectedRoutes.some(
    (route) => path === route || path.startsWith(`${route}/`)
  );
}

/**
 * Check if a path is an auth-only route (login, register, etc.)
 */
function isAuthRoute(path: string): boolean {
  return authRoutes.some(
    (route) => path === route || path.startsWith(`${route}/`)
  );
}

/**
 * Middleware for route protection
 *
 * - Root path (/): Show landing page to visitors, redirect to /dashboard if authenticated
 * - Protected routes (/dashboard/*): Require auth cookie, redirect to /login if missing
 * - Auth routes (/login): Redirect to /dashboard if already authenticated
 * - Public routes: No checks
 *
 * Note: This only checks cookie PRESENCE, not validity.
 * Token validation happens server-side via /api/auth/me endpoint.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public API routes
  if (matchesPrefix(pathname, publicRoutes)) {
    return NextResponse.next();
  }

  // Check for auth token cookie
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  const isAuthenticated = !!token;

  // Root path: Show landing page to visitors, dashboard to authenticated users
  if (pathname === '/') {
    if (isAuthenticated) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
    // Unauthenticated users see the landing page
    return NextResponse.next();
  }

  // Protected routes: Redirect to login if not authenticated
  if (isProtectedRoute(pathname)) {
    if (!isAuthenticated) {
      const loginUrl = new URL('/login', request.url);
      // Optionally add redirect parameter to return after login
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next();
  }

  // Auth routes: Redirect to dashboard if already authenticated
  if (isAuthRoute(pathname)) {
    if (isAuthenticated) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
    return NextResponse.next();
  }

  // All other routes: Allow through
  return NextResponse.next();
}

/**
 * Matcher configuration
 *
 * Run middleware on all routes except:
 * - _next/static (static files)
 * - _next/image (image optimization)
 * - favicon.ico (favicon)
 * - public files (images, etc.)
 */
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
