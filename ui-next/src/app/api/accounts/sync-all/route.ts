import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * POST /api/accounts/sync-all
 * BFF pattern: Sync all accounts from connected brokers
 *
 * Re-fetches and syncs account data from all connected brokers.
 * Updates stored accounts with latest balance/equity information.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function POST(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/accounts/sync-all`,
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
        { error: errorData.detail || 'Failed to sync accounts' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Return the response from backend
    // Format: { synced: boolean, message: string, results: [...] }
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error syncing accounts:', error);
    return NextResponse.json(
      { error: 'Failed to sync accounts' },
      { status: 500 }
    );
  }
}
