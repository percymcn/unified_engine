import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/signal-intelligence/settings
 * Proxy to backend to get momentum settings
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

    const response = await fetch(`${BACKEND_URL}/api/v1/signal-intelligence/settings`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store',  // Disable caching to always get fresh data
    });

    console.log('[API Proxy] GET momentum settings - status:', response.status);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch momentum settings' }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    console.log('[API Proxy] GET momentum settings - returning profit_lock_enabled:', data.profit_lock_enabled);
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching momentum settings:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/signal-intelligence/settings
 * Proxy to backend to update momentum settings
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
    console.log('[API Proxy] PUT momentum settings - sending:', JSON.stringify(body, null, 2));

    const response = await fetch(`${BACKEND_URL}/api/v1/signal-intelligence/settings`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    console.log('[API Proxy] PUT momentum settings - status:', response.status);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to update momentum settings' }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    console.log('[API Proxy] PUT momentum settings - response profit_lock_enabled:', data.profit_lock_enabled);
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating momentum settings:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
