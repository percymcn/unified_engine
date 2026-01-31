import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const TIMEOUT_MS = 5000; // 5 second timeout to avoid Cloudflare 524

export interface PositionAccountInfo {
  broker: string;
  account_name: string | null;
}

export interface PositionItem {
  id: string;  // String to preserve large TradeLocker position IDs
  symbol: string;
  side: string;
  volume: number;
  unrealized_pnl: number;
  account: PositionAccountInfo;
}

export interface PositionsResponse {
  positions: PositionItem[];
  total_pnl: number;
  total_positions: number;
}

/**
 * GET /api/dashboard/positions
 * BFF pattern: Fetch open positions for the dashboard
 */
export async function GET() {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const response = await fetch(
      `${BACKEND_URL}/api/v1/dashboard/positions`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      }
    );
    clearTimeout(timeoutId);

    if (!response.ok) {
      console.error('Failed to fetch positions:', response.status);
      // Return empty response on error (graceful degradation)
      return NextResponse.json({
        positions: [],
        total_pnl: 0,
        total_positions: 0,
      });
    }

    const data: PositionsResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching positions:', error);
    // Return empty response on error (graceful degradation)
    return NextResponse.json({
      positions: [],
      total_pnl: 0,
      total_positions: 0,
    });
  }
}
