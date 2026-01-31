import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const TIMEOUT_MS = 5000; // 5 second timeout to avoid Cloudflare 524

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

    // Helper to fetch with timeout
    const fetchWithTimeout = async (url: string, options: RequestInit) => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
      try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        return response;
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          console.warn(`Timeout fetching ${url}`);
        }
        throw error;
      } finally {
        clearTimeout(timeoutId);
      }
    };

    // Fetch stats from multiple backend endpoints in parallel (max limit=50 per backend validation)
    const [signalsRes, accountsRes, liveAccountsRes, executionsRes] = await Promise.allSettled([
      fetchWithTimeout(`${BACKEND_URL}/api/v1/signals/?limit=50&status=pending`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      fetchWithTimeout(`${BACKEND_URL}/api/v1/accounts/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      // Fetch live account data for real-time balances
      fetchWithTimeout(`${BACKEND_URL}/api/v1/dashboard/accounts/live`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      // Fetch executions for today's trades count (max 50)
      fetchWithTimeout(`${BACKEND_URL}/api/v1/dashboard/executions?limit=50`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
    ]);

    // Parse responses (handle failures gracefully with Promise.allSettled)
    const getResult = async (result: PromiseSettledResult<Response>, fallback: unknown) => {
      if (result.status === 'fulfilled' && result.value.ok) {
        return result.value.json();
      }
      return fallback;
    };

    const signals = await getResult(signalsRes, []);
    const accountsData = await getResult(accountsRes, []);
    const liveAccountsData = await getResult(liveAccountsRes, null);
    const executionsData = await getResult(executionsRes, { executions: [] });

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
