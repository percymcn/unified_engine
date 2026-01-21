import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/dashboard/stats
 * BFF pattern: Aggregate dashboard statistics from backend
 * Uses auth_token cookie for authorization
 */
export async function GET() {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Fetch stats from multiple backend endpoints in parallel
    const [signalsRes, accountsRes, tradesRes] = await Promise.all([
      fetch(`${BACKEND_URL}/api/v1/signals/?limit=100&status=pending`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      fetch(`${BACKEND_URL}/api/v1/accounts/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      fetch(`${BACKEND_URL}/api/v1/trades/?limit=100`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
    ]);

    // Parse responses (handle failures gracefully)
    const signals = signalsRes.ok ? await signalsRes.json() : [];
    const accounts = accountsRes.ok ? await accountsRes.json() : [];
    const trades = tradesRes.ok ? await tradesRes.json() : [];

    // Calculate today's trades
    const today = new Date().toISOString().split('T')[0];
    const todaysTrades = Array.isArray(trades)
      ? trades.filter((t: { created_at?: string }) => t.created_at?.startsWith(today)).length
      : 0;

    // Calculate total balance across accounts
    const totalBalance = Array.isArray(accounts)
      ? accounts.reduce((sum: number, acc: { balance?: number }) => sum + (acc.balance || 0), 0)
      : 0;

    // Count connected brokers (accounts with active status)
    const connectedBrokers = Array.isArray(accounts)
      ? accounts.filter((acc: { is_active?: boolean }) => acc.is_active).length
      : 0;

    // Count pending signals
    const activeSignals = Array.isArray(signals) ? signals.length : 0;

    return NextResponse.json({
      activeSignals,
      connectedBrokers,
      todaysTrades,
      totalBalance,
    });
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    // Return empty stats on error, not error response (graceful degradation)
    return NextResponse.json(
      { activeSignals: 0, connectedBrokers: 0, todaysTrades: 0, totalBalance: 0 },
      { status: 200 }
    );
  }
}
