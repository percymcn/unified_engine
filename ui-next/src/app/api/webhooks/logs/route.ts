import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/webhooks/logs
 * BFF proxy for the authenticated backend webhook log list.
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const skip = request.nextUrl.searchParams.get('skip') || '0';
    const limit = request.nextUrl.searchParams.get('limit') || '100';
    const response = await fetch(
      `${BACKEND_URL}/api/v1/webhooks/logs?skip=${encodeURIComponent(skip)}&limit=${encodeURIComponent(limit)}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (response.status === 401) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    if (response.status === 404) {
      return NextResponse.json([]);
    }

    if (!response.ok) {
      console.error(`Backend returned ${response.status} for webhook logs`);
      return NextResponse.json([]);
    }

    const logs = await response.json();
    return NextResponse.json(logs);
  } catch (error) {
    console.error('Error fetching webhook logs:', error);
    return NextResponse.json([]);
  }
}
