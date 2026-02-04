import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/accounts/[id]/symbol-settings
 * Get all symbol-specific settings for an account
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const token = await getTokenFromCookies();
    const { id } = await params;

    if (!token) {
      return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/accounts/${id}/symbol-settings`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch symbol settings' }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching symbol settings:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}

/**
 * POST /api/accounts/[id]/symbol-settings
 * Create or update symbol-specific settings
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const token = await getTokenFromCookies();
    const { id } = await params;

    if (!token) {
      return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();

    const response = await fetch(
      `${BACKEND_URL}/api/v1/accounts/${id}/symbol-settings`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to save symbol settings' }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error saving symbol settings:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
