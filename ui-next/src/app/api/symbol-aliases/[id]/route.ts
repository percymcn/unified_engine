import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/symbol-aliases/:id
 * BFF pattern: Proxy symbol aliases by broker type request
 * Note: :id is broker_type (tradelocker, tradovate, etc.)
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/symbol-aliases/${id}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        return NextResponse.json(
          { error: 'Unauthorized' },
          { status: 401 }
        );
      }
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || 'Failed to fetch symbol aliases' },
        { status: response.status }
      );
    }

    const aliases = await response.json();

    return NextResponse.json(aliases);
  } catch (error) {
    console.error('Error fetching symbol aliases:', error);
    return NextResponse.json(
      { detail: 'Failed to fetch symbol aliases' },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/symbol-aliases/:id
 * BFF pattern: Proxy symbol alias update to backend
 * :id is the alias ID (numeric)
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/v1/symbol-aliases/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || 'Failed to update symbol alias' },
        { status: response.status }
      );
    }

    const alias = await response.json();

    return NextResponse.json(alias);
  } catch (error) {
    console.error('Error updating symbol alias:', error);
    return NextResponse.json(
      { detail: 'Failed to update symbol alias' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/symbol-aliases/:id
 * BFF pattern: Proxy symbol alias deletion to backend
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/symbol-aliases/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || 'Failed to delete symbol alias' },
        { status: response.status }
      );
    }

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error('Error deleting symbol alias:', error);
    return NextResponse.json(
      { detail: 'Failed to delete symbol alias' },
      { status: 500 }
    );
  }
}
