import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * Available broker account returned from backend
 */
interface BrokerAccountInfo {
  id: string;
  name: string;
  account_type: string;
  balance: number | null;
  equity: number | null;
  currency: string | null;
  server: string | null;
  login: string | null;
  broker_type: string;
  is_active: boolean;
  is_stored: boolean;
  is_selected: boolean;
  stored_account_id: number | null;
}

/**
 * GET /api/accounts/available/[broker]
 * BFF pattern: Fetch available accounts from broker SDK
 *
 * Returns list of accounts available on the broker, with selection status
 * cross-referenced against stored TradingAccounts.
 *
 * @param broker - Broker type (tradelocker, projectx, tradovate, mt4, mt5)
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ broker: string }> }
) {
  try {
    const token = await getTokenFromCookies();
    const { broker } = await params;

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/accounts/available/${broker}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch available accounts' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Return the response from backend
    // Format: { broker_type: string, accounts: BrokerAccountInfo[], total: number, message?: string }
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching available accounts:', error);
    return NextResponse.json(
      { error: 'Failed to fetch available accounts' },
      { status: 500 }
    );
  }
}
