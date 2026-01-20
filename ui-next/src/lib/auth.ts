import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

/**
 * Auth token cookie configuration
 * Uses httpOnly cookies for JWT storage (NOT localStorage - security best practice)
 */
export const AUTH_COOKIE_NAME = 'auth-token';

/**
 * Cookie options for auth token
 * - httpOnly: Prevents XSS access to token
 * - secure: Only send over HTTPS in production
 * - sameSite: Protects against CSRF
 * - path: Cookie available for all routes
 */
const getCookieOptions = (maxAge?: number) => ({
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
  ...(maxAge !== undefined && { maxAge }),
});

/**
 * Server-side: Extract token from cookies
 * Use in API routes and server components
 */
export async function getTokenFromCookies(): Promise<string | undefined> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_NAME)?.value;
}

/**
 * Server-side: Set auth token as httpOnly cookie
 * Use in login API route after successful authentication
 *
 * @param response - NextResponse to set cookie on
 * @param token - JWT access token from backend
 * @param maxAge - Cookie lifetime in seconds (default: 24 hours)
 */
export function setTokenCookie(
  response: NextResponse,
  token: string,
  maxAge: number = 86400 // 24 hours default
): void {
  response.cookies.set(AUTH_COOKIE_NAME, token, getCookieOptions(maxAge));
}

/**
 * Server-side: Remove auth token cookie
 * Use in logout API route
 *
 * @param response - NextResponse to clear cookie on
 */
export function removeTokenCookie(response: NextResponse): void {
  response.cookies.set(AUTH_COOKIE_NAME, '', {
    ...getCookieOptions(0),
    maxAge: 0,
  });
}

/**
 * Client-side: Check if auth cookie exists
 * This is a simple presence check - does NOT validate the token
 * Token validation happens server-side via backend /api/auth/me endpoint
 *
 * @returns true if auth cookie appears to exist (client-side check only)
 */
export function isAuthenticated(): boolean {
  if (typeof document === 'undefined') {
    // Server-side, can't check document.cookie
    return false;
  }
  // Note: httpOnly cookies are not accessible via document.cookie
  // This function can only check non-httpOnly cookies
  // For proper auth state, use server-side check or /api/auth/me
  return false;
}
