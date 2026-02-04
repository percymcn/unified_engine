import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * DELETE /api/accounts/[id]/symbol-settings/[symbol]
 * Delete symbol-specific settings
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; symbol: string }> }
) {
  try {
    const token = await getTokenFromCookies();
    const { id, symbol } = await params;

    if (!token) {
      return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/accounts/${id}/symbol-settings/${encodeURIComponent(symbol)}`,
      {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to delete symbol settings' }));
      return NextResponse.json(error, { status: response.status });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting symbol settings:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
