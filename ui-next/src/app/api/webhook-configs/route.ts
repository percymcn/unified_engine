import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/webhook-configs
 * BFF pattern: Proxy webhook configs list request to backend
 *
 * Error handling strategy:
 * - 401: Return unauthorized (user needs to log in)
 * - 404: Return empty array (user has no configs yet - normal case)
 * - Other errors: Return empty array to prevent UI crash (graceful degradation)
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

    const response = await fetch(`${BACKEND_URL}/api/v1/webhook-configs/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    // Handle 404 gracefully - user just has no configs yet
    if (response.status === 404) {
      return NextResponse.json([]);
    }

    // Handle 401 - user needs to re-authenticate
    if (response.status === 401) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    if (!response.ok) {
      // Log error but return empty for better UX
      console.error(`Backend returned ${response.status} for webhook-configs`);
      // For other errors, return empty array to prevent UI crash
      return NextResponse.json([]);
    }

    const configs = await response.json();

    return NextResponse.json(configs);
  } catch (error) {
    console.error('Error fetching webhook configs:', error);
    // Return empty array on network errors to prevent UI crash
    return NextResponse.json([]);
  }
}

/**
 * POST /api/webhook-configs
 * BFF pattern: Proxy webhook config creation to backend
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

    const response = await fetch(`${BACKEND_URL}/api/v1/webhook-configs/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to create webhook config' },
        { status: response.status }
      );
    }

    const config = await response.json();

    return NextResponse.json(config);
  } catch (error) {
    console.error('Error creating webhook config:', error);
    return NextResponse.json(
      { error: 'Failed to create webhook config' },
      { status: 500 }
    );
  }
}
