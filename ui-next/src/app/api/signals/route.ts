import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const TIMEOUT_MS = 5000; // 5 second timeout to avoid Cloudflare 524

/**
 * GET /api/signals
 * BFF pattern: Proxy signals request to backend
 * Uses auth_token cookie for authorization
 * Forwards query params: limit, offset, status, symbol, etc.
 */
export async function GET(request: NextRequest) {
  try {
    // Extract token from httpOnly cookie
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized - no auth token' },
        { status: 401 }
      );
    }

    // Forward query params to backend
    // Use trailing slash to avoid 307 redirect which strips Authorization header
    const { searchParams } = new URL(request.url);
    const queryString = searchParams.toString();
    const url = queryString
      ? `${BACKEND_URL}/api/v1/signals/?${queryString}`
      : `${BACKEND_URL}/api/v1/signals/`;

    // Fetch signals from backend with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      // Important: don't follow redirects that might strip auth header
      redirect: 'manual',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    // Handle redirect manually to preserve auth header
    if (response.status === 307 || response.status === 308) {
      const location = response.headers.get('location');
      if (location) {
        const redirectResponse = await fetch(location, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        if (!redirectResponse.ok) {
          const errorText = await redirectResponse.text();
          console.error(`Backend redirect error (${redirectResponse.status}):`, errorText);
          return NextResponse.json(
            { error: `Backend error: ${redirectResponse.status}` },
            { status: redirectResponse.status }
          );
        }
        const signals = await redirectResponse.json();
        return NextResponse.json(signals);
      }
    }

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend error (${response.status}):`, errorText);
      return NextResponse.json(
        { error: `Backend error: ${response.status}` },
        { status: response.status }
      );
    }

    const signals = await response.json();

    return NextResponse.json(signals);
  } catch (error) {
    console.error('Error fetching signals:', error);
    // Return empty array on error/timeout (graceful degradation)
    return NextResponse.json([], { status: 200 });
  }
}
