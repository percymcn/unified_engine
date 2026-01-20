import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * POST /api/accounts/[id]/sync
 * BFF pattern: Trigger account sync with broker
 * Fetches latest account data from the broker API
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/accounts/${params.id}/sync`,
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
        { error: errorData.detail || 'Failed to sync account' },
        { status: response.status }
      );
    }

    const account = await response.json();

    return NextResponse.json(account);
  } catch (error) {
    console.error('Error syncing account:', error);
    return NextResponse.json(
      { error: 'Failed to sync account' },
      { status: 500 }
    );
  }
}
