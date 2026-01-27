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

    // Fetch stats from multiple backend endpoints in parallel (max limit=50 per backend validation)
    const [signalsRes, accountsRes, liveAccountsRes, executionsRes] = await Promise.all([
      fetch(`${BACKEND_URL}/api/v1/signals/?limit=50&status=pending`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      fetch(`${BACKEND_URL}/api/v1/accounts/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      // Fetch live account data for real-time balances
      fetch(`${BACKEND_URL}/api/v1/dashboard/accounts/live`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      // Fetch executions for today's trades count (max 50)
      fetch(`${BACKEND_URL}/api/v1/dashboard/executions?limit=50`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
    ]);

    // Parse responses (handle failures gracefully)
    const signals = signalsRes.ok ? await signalsRes.json() : [];
    const accountsData = accountsRes.ok ? await accountsRes.json() : [];
    const liveAccountsData = liveAccountsRes.ok ? await liveAccountsRes.json() : null;
    const executionsData = executionsRes.ok ? await executionsRes.json() : { executions: [] };

    // Normalize accounts response - backend returns {accounts: [], total} or just []
    const accounts = Array.isArray(accountsData)
      ? accountsData
      : (accountsData?.accounts || []);

    // Calculate today's trades from executions
    const today = new Date().toISOString().split('T')[0];
    const executions = executionsData?.executions || [];
    const todaysTrades = executions.filter(
      (e: { created_at?: string }) => e.created_at?.startsWith(today)
    ).length;

    // Use live account data for balance if available, otherwise fallback to DB cached
    let totalBalance = 0;
    if (liveAccountsData?.total_balance !== undefined) {
      totalBalance = liveAccountsData.total_balance;
    } else {
      totalBalance = accounts.reduce(
        (sum: number, acc: { balance?: number }) => sum + (acc.balance || 0),
        0
      );
    }

    // Count connected brokers (accounts with active status)
    const connectedBrokers = accounts.filter(
      (acc: { is_active?: boolean }) => acc.is_active
    ).length;

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
