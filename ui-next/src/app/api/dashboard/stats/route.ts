import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const TIMEOUT_MS = 8000; // 8 second timeout

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

    // Fetch stats from multiple backend endpoints in parallel
    const [signalsRes, accountsRes, liveAccountsRes, executionsRes] = await Promise.allSettled([
      fetchWithTimeout(`${BACKEND_URL}/api/v1/signals/?limit=1`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      fetchWithTimeout(`${BACKEND_URL}/api/v1/accounts/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      // Fetch live account data for real-time balances
      fetchWithTimeout(`${BACKEND_URL}/api/v1/dashboard/accounts/live`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      // Fetch executions with higher limit for accurate today count
      fetchWithTimeout(`${BACKEND_URL}/api/v1/dashboard/executions?limit=500`, {
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

    const signalsData = await getResult(signalsRes, { signals: [], total: 0, pending_count: 0 });
    const accountsData = await getResult(accountsRes, []);
    const liveAccountsData = await getResult(liveAccountsRes, null);
    const executionsData = await getResult(executionsRes, { executions: [], total: 0 });

    // Normalize accounts response - backend returns {accounts: [], total} or just []
    const accounts = Array.isArray(accountsData)
      ? accountsData
      : (accountsData?.accounts || []);

    // Use today_count from backend (accurate database count, not client-side filtering)
    const todaysTrades = executionsData?.today_count || 0;

    // Use the total from backend response (accurate count from database)
    const totalExecutions = executionsData?.total || 0;

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

    // Count pending signals (use pending_count from backend for accurate count)
    const activeSignals = signalsData?.pending_count || 0;

    return NextResponse.json({
      activeSignals,
      connectedBrokers,
      todaysTrades,
      totalExecutions,
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
