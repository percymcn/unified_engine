import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/risk/settings
 * Proxy to backend to get risk settings
 */
export async function GET() {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/risk/settings`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch risk settings' }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching risk settings:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/risk/settings
 * Proxy to backend to update risk settings
 */
export async function PUT(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { detail: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();

    // Debug: Log what we're sending to backend
    console.log('[Risk Settings PUT] Sending to backend:', JSON.stringify(body, null, 2));
    console.log('[Risk Settings PUT] default_max_daily_profit:', body.default_max_daily_profit);
    console.log('[Risk Settings PUT] default_max_open_positions:', body.default_max_open_positions);

    const response = await fetch(`${BACKEND_URL}/api/v1/risk/settings`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to update risk settings' }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating risk settings:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
