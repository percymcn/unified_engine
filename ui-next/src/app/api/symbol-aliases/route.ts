import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/symbol-aliases
 * BFF pattern: Proxy symbol aliases list request to backend
 * Returns aliases grouped by broker
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

    const response = await fetch(`${BACKEND_URL}/api/v1/symbol-aliases/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      // Preserve 401 for auth errors
      if (response.status === 401) {
        return NextResponse.json(
          { error: 'Unauthorized' },
          { status: 401 }
        );
      }
      throw new Error(`Backend returned ${response.status}`);
    }

    const aliases = await response.json();

    return NextResponse.json(aliases);
  } catch (error) {
    console.error('Error fetching symbol aliases:', error);
    return NextResponse.json(
      { error: 'Failed to fetch symbol aliases' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/symbol-aliases
 * BFF pattern: Proxy symbol alias creation to backend
 * Expects JSON body with sourceSymbol, brokerType, targetSymbol
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

    const response = await fetch(`${BACKEND_URL}/api/v1/symbol-aliases/`, {
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
        { detail: errorData.detail || 'Failed to create symbol alias' },
        { status: response.status }
      );
    }

    const alias = await response.json();

    return NextResponse.json(alias, { status: 201 });
  } catch (error) {
    console.error('Error creating symbol alias:', error);
    return NextResponse.json(
      { detail: 'Failed to create symbol alias' },
      { status: 500 }
    );
  }
}
