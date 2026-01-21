import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * Handle Tradovate OAuth callback redirect.
 *
 * This BFF route receives the redirect from Tradovate after the user
 * authorizes the application. It exchanges the authorization code
 * for tokens via the backend API and redirects the user to the
 * accounts settings page with the result.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');
  const errorDescription = searchParams.get('error_description');

  // Handle OAuth error response from Tradovate
  if (error) {
    const errorMessage = errorDescription || error;
    return NextResponse.redirect(
      new URL(
        `/dashboard/settings/accounts?error=${encodeURIComponent(errorMessage)}`,
        request.url
      )
    );
  }

  // Validate required parameters
  if (!code || !state) {
    return NextResponse.redirect(
      new URL(
        '/dashboard/settings/accounts?error=missing_params',
        request.url
      )
    );
  }

  try {
    // Exchange authorization code for tokens via backend
    const response = await fetch(
      `${BACKEND_URL}/api/v1/auth/tradovate/callback?${new URLSearchParams({
        code,
        state,
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
          `/dashboard/settings/accounts?error=${encodeURIComponent(errorMessage)}`,
          request.url
        )
      );
    }

    const tokens = await response.json();

    // Redirect with tokens in URL fragment (not sent to server)
    // Frontend JavaScript will read and securely store them
    return NextResponse.redirect(
      new URL(
        `/dashboard/settings/accounts?tradovate_connected=true#tokens=${encodeURIComponent(
          JSON.stringify(tokens)
        )}`,
        request.url
      )
    );
  } catch (error) {
    console.error('Tradovate OAuth callback error:', error);
    return NextResponse.redirect(
      new URL(
        '/dashboard/settings/accounts?error=token_exchange_failed',
        request.url
      )
    );
  }
}
