import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export interface ExpiringContract {
  contractCode: string;
  symbolRoot: string;
  expirationDate: string;
  rolloverDate: string;
  nextContract: string | null;
  daysUntilExpiration: number;
  daysUntilRollover: number;
  accountId: number;
}

/**
 * GET /api/dashboard/contracts
 * BFF pattern: Fetch expiring contracts for the current user
 */
export async function GET(request: Request) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get days parameter from query string, default to 7
    const { searchParams } = new URL(request.url);
    const days = searchParams.get('days') || '7';

    const response = await fetch(
      `${BACKEND_URL}/api/v1/contracts/expiring?days=${days}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      // Return empty array on error (graceful degradation)
      console.error('Failed to fetch expiring contracts:', response.status);
      return NextResponse.json([]);
    }

    const data = await response.json();

    // Transform snake_case to camelCase for frontend
    const contracts: ExpiringContract[] = Array.isArray(data)
      ? data.map((c: Record<string, unknown>) => ({
          contractCode: c.contract_code as string,
          symbolRoot: c.symbol_root as string,
          expirationDate: c.expiration_date as string,
          rolloverDate: c.rollover_date as string,
          nextContract: c.next_contract as string | null,
          daysUntilExpiration: c.days_until_expiration as number,
          daysUntilRollover: c.days_until_rollover as number,
          accountId: c.account_id as number,
        }))
      : [];

    return NextResponse.json(contracts);
  } catch (error) {
    console.error('Error fetching expiring contracts:', error);
    // Return empty array on error (graceful degradation)
    return NextResponse.json([]);
  }
}
