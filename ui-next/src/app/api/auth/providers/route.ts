import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const FRONTEND_URL = process.env.NEXT_PUBLIC_FRONTEND_URL || 'http://localhost:3456';

/**
 * GET /api/auth/providers
 * BFF route to fetch OAuth providers from backend and fix redirect URIs for local dev
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

    // For local development, override redirect_uri to point to local callback
    // This requires the local redirect_uri to be registered in Google Console
    const providers = (data.providers || []).map((provider: {
      provider: string;
      name: string;
      auth_url: string;
    }) => {
      if (provider.provider === 'google' && provider.auth_url) {
        // Parse the auth_url and update redirect_uri for local dev
        try {
          const url = new URL(provider.auth_url);
          const currentRedirectUri = url.searchParams.get('redirect_uri');

          // If we're in local dev and redirect_uri points to production, update it
          if (currentRedirectUri && !currentRedirectUri.includes('localhost')) {
            // Check if we should use local callback (FRONTEND_URL contains localhost)
            if (FRONTEND_URL.includes('localhost') || FRONTEND_URL.includes('127.0.0.1')) {
              url.searchParams.set('redirect_uri', `${FRONTEND_URL}/api/auth/google/callback`);
              provider.auth_url = url.toString();
            }
          }
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
