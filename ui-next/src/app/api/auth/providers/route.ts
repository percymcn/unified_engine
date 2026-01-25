import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
// For Google OAuth, always use the public URL that's registered in Google Console
const FRONTEND_URL = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://tradeflow.fluxeo.net';

/**
 * GET /api/auth/providers
 * BFF route to fetch OAuth providers from backend and ensure redirect_uri
 * matches what's registered in Google Cloud Console (the public URL).
 */
export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/oauth/providers`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      return NextResponse.json({ providers: [] }, { status: 200 });
    }

    const data = await response.json();

    // Always ensure redirect_uri matches the configured FRONTEND_URL
    // This must match what's registered in Google Cloud Console
    const providers = (data.providers || []).map((provider: {
      provider: string;
      name: string;
      auth_url: string;
    }) => {
      if (provider.provider === 'google' && provider.auth_url) {
        try {
          const url = new URL(provider.auth_url);
          // Always set redirect_uri to the configured frontend URL
          // This ensures it matches what's in Google Console
          url.searchParams.set('redirect_uri', `${FRONTEND_URL}/api/auth/google/callback`);
          provider.auth_url = url.toString();
        } catch (e) {
          console.error('Error parsing auth_url:', e);
        }
      }
      return provider;
    });

    return NextResponse.json({ providers });
  } catch (error) {
    console.error('Error fetching OAuth providers:', error);
    return NextResponse.json({ providers: [] }, { status: 200 });
  }
}
