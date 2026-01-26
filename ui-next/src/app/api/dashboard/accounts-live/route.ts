import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export interface AccountSummaryItem {
  account_id: number;
  account_name: string | null;
  broker: string;
  balance: number;
  equity: number;
  margin_used: number;
  margin_available: number;
  unrealized_pnl: number;
  positions_count: number;
}

export interface AccountsSummaryResponse {
  accounts: AccountSummaryItem[];
  total_balance: number;
  total_equity: number;
  total_unrealized_pnl: number;
}

/**
 * GET /api/dashboard/accounts-live
 * BFF pattern: Fetch live account summaries from broker connections
 */
export async function GET() {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/dashboard/accounts/live`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      console.error('Failed to fetch live accounts:', response.status);
      // Return empty response on error (graceful degradation)
      return NextResponse.json({
        accounts: [],
        total_balance: 0,
        total_equity: 0,
        total_unrealized_pnl: 0,
      });
    }

    const data: AccountsSummaryResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching live accounts:', error);
    // Return empty response on error (graceful degradation)
    return NextResponse.json({
      accounts: [],
      total_balance: 0,
      total_equity: 0,
      total_unrealized_pnl: 0,
    });
  }
}
