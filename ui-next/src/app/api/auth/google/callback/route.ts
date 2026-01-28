import { NextResponse } from 'next/server';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
// Always use production URL for OAuth callback redirects
// This ensures OAuth works correctly in production
const FRONTEND_URL = 'https://tradeflow.fluxeo.net';

/**
 * Handle Google OAuth callback redirect.
 *
 * This BFF route receives the redirect from Google after the user
 * authorizes the application. It exchanges the authorization code
 * for tokens via the backend API and sets a session cookie.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');
  const errorDescription = searchParams.get('error_description');

  // Handle OAuth error response from Google
  if (error) {
    const errorMessage = errorDescription || error;
    return NextResponse.redirect(
      new URL(
        `/login?error=${encodeURIComponent(errorMessage)}`,
        FRONTEND_URL
      )
    );
  }

  // Validate required parameters
  if (!code) {
    return NextResponse.redirect(
      new URL(
        '/login?error=missing_code',
        FRONTEND_URL
      )
    );
  }

  try {
    // Exchange authorization code for tokens via backend
    const response = await fetch(
      `${BACKEND_URL}/api/v1/oauth/callback/google?${new URLSearchParams({
        code,
        ...(state && { state }),
      })}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || 'Token exchange failed';
      return NextResponse.redirect(
        new URL(
          `/login?error=${encodeURIComponent(errorMessage)}`,
          FRONTEND_URL
        )
      );
    }

    const authData = await response.json();

    // Set authentication cookie
    const redirectResponse = NextResponse.redirect(
      new URL('/dashboard', FRONTEND_URL)
    );

    // Set secure HTTP-only cookie (using AUTH_COOKIE_NAME for consistency)
    redirectResponse.cookies.set(AUTH_COOKIE_NAME, authData.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: authData.expires_in || 1800, // 30 minutes default
      path: '/',
    });

    return redirectResponse;
  } catch (error) {
    console.error('Google OAuth callback error:', error);
    return NextResponse.redirect(
      new URL(
        '/login?error=token_exchange_failed',
        FRONTEND_URL
      )
    );
  }
}
