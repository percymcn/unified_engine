import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';
import { Trade } from '@/types/trade';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

interface ExecutionItem {
  id: number;
  signal_id?: string;
  account: {
    broker: string;
    account_id?: number;
  };
  symbol: string;
  action: string;
  volume: number;
  price?: number;
  status: string;
  execution_time_ms?: number;
  created_at: string;
  // Enhanced risk management fields (migration 027)
  stop_loss?: number;
  take_profit?: number;
  trailing_stop?: number;
  entry_price?: number;
  order_id?: string;
  close_reason?: string;
  pnl?: number;
  pnl_pct?: number;
  closed_at?: string;
}

/**
 * Transform execution log to Trade format for UI
 */
function executionToTrade(exec: ExecutionItem): Trade {
  // Map action to side
  const actionLower = exec.action.toLowerCase();
  const side: 'buy' | 'sell' = actionLower.includes('sell') || actionLower === 'close_sell'
    ? 'sell'
    : 'buy';

  // Map status
  let status: Trade['status'] = 'closed';
  if (exec.status === 'pending') status = 'pending';
  else if (exec.status === 'failed' || exec.status === 'error') status = 'cancelled';
  else if (exec.status === 'success') status = 'closed';

  return {
    id: exec.id,
    symbol: exec.symbol,
    side,
    quantity: exec.volume,
    entry_price: exec.entry_price || exec.price || 0,
    status,
    broker: exec.account.broker,
    account_id: exec.account.account_id || 0,
    opened_at: exec.created_at,
    // Enhanced risk management fields (migration 027)
    stop_loss: exec.stop_loss,
    take_profit: exec.take_profit,
    trailing_stop: exec.trailing_stop,
    close_reason: exec.close_reason as Trade['close_reason'],
    profit_loss: exec.pnl,
    profit_loss_pct: exec.pnl_pct,
    closed_at: exec.closed_at,
    order_id: exec.order_id,
  };
}

/**
 * GET /api/trades
 * BFF pattern: Fetch execution logs from backend and transform to Trade format
 * Uses auth_token cookie for authorization
 *
 * Query params:
 * - date_from: ISO date string (YYYY-MM-DD)
 * - date_to: ISO date string (YYYY-MM-DD)
 * - broker: Broker type filter
 * - status: Trade status filter (open, closed, pending, cancelled)
 */
export async function GET(request: NextRequest) {
  try {
    // Extract token from httpOnly cookie
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Forward query params to backend (max 50 per backend limit)
    const { searchParams } = new URL(request.url);
    const limit = Math.min(Number(searchParams.get('limit')) || 50, 50).toString();

    // Fetch executions from dashboard endpoint
    const url = `${BACKEND_URL}/api/v1/dashboard/executions?limit=${limit}`;

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();
    const executions: ExecutionItem[] = data.executions || [];

    // Transform to Trade format
    let trades: Trade[] = executions.map(executionToTrade);

    // Apply client-side filters
    const dateFrom = searchParams.get('date_from');
    const dateTo = searchParams.get('date_to');
    const broker = searchParams.get('broker');
    const status = searchParams.get('status');

    if (dateFrom) {
      trades = trades.filter(t => t.opened_at >= dateFrom);
    }
    if (dateTo) {
      trades = trades.filter(t => t.opened_at <= dateTo + 'T23:59:59');
    }
    if (broker && broker !== 'all') {
      trades = trades.filter(t => t.broker.toLowerCase() === broker.toLowerCase());
    }
    if (status && status !== 'all') {
      trades = trades.filter(t => t.status === status);
    }

    return NextResponse.json(trades);
  } catch (error) {
    console.error('Error fetching trades:', error);
    return NextResponse.json(
      { error: 'Failed to fetch trades' },
      { status: 500 }
    );
  }
}
