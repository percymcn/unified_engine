import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/tradovate/authorize
 * BFF route to initiate Tradovate OAuth flow.
 *
 * Proxies the request to the backend OAuth authorize endpoint,
 * which generates the authorization URL with proper state parameter.
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const environment = searchParams.get('environment') || 'demo';

  // Get auth token from cookies
  const token = await getTokenFromCookies();

  if (!token) {
    return NextResponse.json(
      { error: 'Not authenticated' },
      { status: 401 }
    );
  }

  try {
    const response = await fetch(
      `${BACKEND_URL}/api/v1/auth/tradovate/authorize?environment=${environment}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: data.detail || 'Failed to initiate OAuth' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('OAuth initiation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
