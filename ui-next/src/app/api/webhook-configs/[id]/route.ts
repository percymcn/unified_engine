import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/webhook-configs/[id]
 * BFF pattern: Proxy single webhook config request to backend
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

    const response = await fetch(`${BACKEND_URL}/api/v1/webhook-configs/${id}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch webhook config' },
        { status: response.status }
      );
    }

    const config = await response.json();

    return NextResponse.json(config);
  } catch (error) {
    console.error('Error fetching webhook config:', error);
    return NextResponse.json(
      { error: 'Failed to fetch webhook config' },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/webhook-configs/[id]
 * BFF pattern: Proxy webhook config update to backend
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

    const response = await fetch(`${BACKEND_URL}/api/v1/webhook-configs/${id}`, {
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
        { error: errorData.detail || 'Failed to update webhook config' },
        { status: response.status }
      );
    }

    const config = await response.json();

    return NextResponse.json(config);
  } catch (error) {
    console.error('Error updating webhook config:', error);
    return NextResponse.json(
      { error: 'Failed to update webhook config' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/webhook-configs/[id]
 * BFF pattern: Proxy webhook config deletion to backend
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

    const response = await fetch(`${BACKEND_URL}/api/v1/webhook-configs/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to delete webhook config' },
        { status: response.status }
      );
    }

    return NextResponse.json({ message: 'Webhook config deleted successfully' });
  } catch (error) {
    console.error('Error deleting webhook config:', error);
    return NextResponse.json(
      { error: 'Failed to delete webhook config' },
      { status: 500 }
    );
  }
}
