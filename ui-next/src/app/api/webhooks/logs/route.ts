import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/webhooks/logs
 * BFF pattern: Proxy webhook-log request to backend GET /api/v1/webhooks/logs.
 * Same auth-forward as signals/trades/webhook-configs: session cookie -> Bearer JWT.
 * Forwards query params (skip, limit, and any others the logs endpoint accepts).
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized - no auth token' },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const queryString = searchParams.toString();
    const url = queryString
      ? `${BACKEND_URL}/api/v1/webhooks/logs?${queryString}`
      : `${BACKEND_URL}/api/v1/webhooks/logs`;

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      redirect: 'manual',
    });

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
        return NextResponse.json(await redirectResponse.json());
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

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error('Error fetching webhook logs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch webhook logs' },
      { status: 500 }
    );
  }
}
