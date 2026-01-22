import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * PUT /api/accounts/[id]/select
 * BFF pattern: Toggle account selection for signal routing
 *
 * When selected=true, the account will receive trading signals.
 * When selected=false, the account will not receive signals.
 *
 * @param id - Database account ID (not broker account ID)
 * @body { selected: boolean }
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const token = await getTokenFromCookies();
    const { id } = await params;

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Parse request body
    const body = await request.json();

    if (typeof body.selected !== 'boolean') {
      return NextResponse.json(
        { error: 'Invalid request: selected must be a boolean' },
        { status: 400 }
      );
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/accounts/${id}/select`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ selected: body.selected }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to update account selection' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Return the response from backend
    // Format: { account_id, account_number, broker, is_selected, message }
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating account selection:', error);
    return NextResponse.json(
      { error: 'Failed to update account selection' },
      { status: 500 }
    );
  }
}
