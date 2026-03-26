import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/strategies
 * BFF pattern: Proxy strategy registry request to backend
 *
 * Error handling strategy:
 * - 401: Return unauthorized (user needs to log in)
 * - 404: Return empty strategies array
 * - Other errors: Return empty strategies array (graceful degradation)
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Get query parameters for filtering
    const searchParams = request.nextUrl.searchParams;
    const statusFilter = searchParams.get('status');
    const typeFilter = searchParams.get('type');

    // Build backend URL with filters
    let backendUrl = `${BACKEND_URL}/api/strategies`;
    const params = new URLSearchParams();
    if (statusFilter) params.append('status', statusFilter);
    if (typeFilter) params.append('type', typeFilter);
    if (params.toString()) backendUrl += `?${params.toString()}`;

    const response = await fetch(backendUrl, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    // Handle 404 gracefully - no strategies
    if (response.status === 404) {
      return NextResponse.json({ strategies: [], total: 0 });
    }

    // Handle 401 - user needs to re-authenticate
    if (response.status === 401) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Check for other errors
    if (!response.ok) {
      console.error(`Backend error ${response.status}:`, await response.text());
      return NextResponse.json({ strategies: [], total: 0 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to fetch strategies:', error);
    return NextResponse.json({ strategies: [], total: 0 });
  }
}

/**
 * POST /api/strategies
 * BFF pattern: Proxy strategy creation/actions to backend
 */
export async function POST(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/strategies`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: errorText || 'Backend error' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to create/action strategy:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
