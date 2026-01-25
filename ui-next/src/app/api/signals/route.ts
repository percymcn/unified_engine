import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

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
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Forward query params to backend
    const { searchParams } = new URL(request.url);
    const queryString = searchParams.toString();
    const url = queryString
      ? `${BACKEND_URL}/api/v1/signals?${queryString}`
      : `${BACKEND_URL}/api/v1/signals`;

    // Fetch signals from backend
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const signals = await response.json();

    return NextResponse.json(signals);
  } catch (error) {
    console.error('Error fetching signals:', error);
    return NextResponse.json(
      { error: 'Failed to fetch signals' },
      { status: 500 }
    );
  }
}
