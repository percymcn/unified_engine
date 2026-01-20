import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/trades
 * BFF pattern: Proxy trades request to backend with optional filters
 * Uses auth_token cookie for authorization
 *
 * Query params:
 * - date_from: ISO date string (YYYY-MM-DD)
 * - date_to: ISO date string (YYYY-MM-DD)
 * - broker: Broker type filter
 * - status: Trade status filter (open, closed, pending, cancelled)
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
    const backendParams = new URLSearchParams();

    // Map frontend params to backend params
    const dateFrom = searchParams.get('date_from');
    const dateTo = searchParams.get('date_to');
    const broker = searchParams.get('broker');
    const status = searchParams.get('status');

    if (dateFrom) backendParams.append('date_from', dateFrom);
    if (dateTo) backendParams.append('date_to', dateTo);
    if (broker) backendParams.append('broker', broker);
    if (status) backendParams.append('status', status);

    const queryString = backendParams.toString();
    const url = `${BACKEND_URL}/api/v1/trades${queryString ? `?${queryString}` : ''}`;

    // Fetch trades from backend
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const trades = await response.json();

    return NextResponse.json(trades);
  } catch (error) {
    console.error('Error fetching trades:', error);
    return NextResponse.json(
      { error: 'Failed to fetch trades' },
      { status: 500 }
    );
  }
}
