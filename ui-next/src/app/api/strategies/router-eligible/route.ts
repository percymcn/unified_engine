import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/strategies/router-eligible
 * BFF pattern: Proxy router-eligible strategies request to backend
 */
export async function GET() {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/strategies/router-eligible`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (response.status === 404) {
      return NextResponse.json({ strategies: [], total: 0 });
    }

    if (response.status === 401) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    if (!response.ok) {
      console.error(`Backend error ${response.status}:`, await response.text());
      return NextResponse.json({ strategies: [], total: 0 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to fetch router-eligible strategies:', error);
    return NextResponse.json({ strategies: [], total: 0 });
  }
}
