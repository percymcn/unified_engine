import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * POST /api/account-groups/[id]/accounts/[accountId]
 * Add an account to a group
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; accountId: string }> }
) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id, accountId } = await params;

    const response = await fetch(
      `${BACKEND_URL}/api/v1/account-groups/${id}/accounts/${accountId}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to add account to group' },
        { status: response.status }
      );
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error adding account to group:', error);
    return NextResponse.json(
      { error: 'Failed to add account to group' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/account-groups/[id]/accounts/[accountId]
 * Remove an account from a group
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; accountId: string }> }
) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id, accountId } = await params;

    const response = await fetch(
      `${BACKEND_URL}/api/v1/account-groups/${id}/accounts/${accountId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to remove account from group' },
        { status: response.status }
      );
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error removing account from group:', error);
    return NextResponse.json(
      { error: 'Failed to remove account from group' },
      { status: 500 }
    );
  }
}
