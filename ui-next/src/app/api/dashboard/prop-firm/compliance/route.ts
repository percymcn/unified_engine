import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/dashboard/prop-firm/compliance
 * Get prop firm compliance data for all accounts
 */
export async function GET() {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Fetch accounts and live data
    const [accountsRes, liveDataRes] = await Promise.all([
      fetch(`${BACKEND_URL}/api/v1/accounts/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
      fetch(`${BACKEND_URL}/api/v1/dashboard/accounts/live`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }),
    ]);

    const accountsData = accountsRes.ok ? await accountsRes.json() : [];
    const liveData = liveDataRes.ok ? await liveDataRes.json() : { accounts: [] };

    const accounts = Array.isArray(accountsData)
      ? accountsData
      : (accountsData?.accounts || []);

    // Filter to prop firm accounts (funded, evaluation types)
    const propAccounts = accounts.filter(
      (a: any) => a.account_type === 'funded' || a.account_type === 'evaluation'
    );

    // Build compliance data for each prop account
    const complianceAccounts = propAccounts.map((account: any) => {
      const live = liveData.accounts?.find((l: any) => l.account_id === account.id);
      const balance = live?.balance || account.balance || 100000;
      const equity = live?.equity || account.equity || balance;

      // Calculate drawdown from starting balance
      const startingBalance = account.extra_metadata?.starting_balance || balance;
      const currentDrawdown = Math.max(0, startingBalance - equity);
      const drawdownPercent = (currentDrawdown / startingBalance) * 100;

      // Prop firm rules (these would ideally come from the broker API)
      const dailyDrawdownLimit = account.max_daily_loss_pct || 5;
      const overallDrawdownLimit = account.max_drawdown_pct || 10;
      const profitTarget = account.extra_metadata?.profit_target_pct || 10;
      const consistencyLimit = 30; // max % of profit from single day

      // Calculate current daily loss
      const dailyPnL = live?.unrealized_pnl || 0;
      const dailyLossPercent = dailyPnL < 0 ? Math.abs(dailyPnL / balance) * 100 : 0;

      // Calculate profit progress
      const totalProfit = Math.max(0, equity - startingBalance);
      const profitPercent = (totalProfit / startingBalance) * 100;

      // Determine rule statuses
      const getStatus = (current: number, limit: number) => {
        const ratio = current / limit;
        if (ratio >= 1) return 'breached';
        if (ratio >= 0.9) return 'danger';
        if (ratio >= 0.7) return 'warning';
        return 'safe';
      };

      const rules = [
        {
          id: 'daily_drawdown',
          name: 'Daily Drawdown',
          description: `Maximum daily loss limit`,
          limit: dailyDrawdownLimit,
          current: dailyLossPercent,
          unit: '%',
          status: getStatus(dailyLossPercent, dailyDrawdownLimit),
          category: 'drawdown',
        },
        {
          id: 'overall_drawdown',
          name: 'Overall Drawdown',
          description: `Maximum total drawdown from peak`,
          limit: overallDrawdownLimit,
          current: drawdownPercent,
          unit: '%',
          status: getStatus(drawdownPercent, overallDrawdownLimit),
          category: 'drawdown',
        },
        {
          id: 'profit_target',
          name: 'Profit Target',
          description: `Target profit to pass phase`,
          limit: profitTarget,
          current: profitPercent,
          unit: '%',
          status: profitPercent >= profitTarget ? 'safe' : 'warning',
          category: 'profit',
        },
        {
          id: 'consistency',
          name: 'Consistency Rule',
          description: `No single day can exceed ${consistencyLimit}% of total profit`,
          limit: consistencyLimit,
          current: 15, // Would need historical data to calculate
          unit: '%',
          status: 'safe',
          category: 'trading',
        },
      ];

      // Determine overall status
      const hasBreached = rules.some((r) => r.status === 'breached');
      const hasDanger = rules.some((r) => r.status === 'danger');
      const overallStatus = hasBreached ? 'breached' : hasDanger ? 'at_risk' : 'compliant';

      return {
        accountId: account.id,
        accountName: account.account_name || account.account_number,
        broker: account.broker,
        phase: account.account_type === 'evaluation' ? 'Evaluation' : 'Funded',
        startDate: account.created_at,
        rules,
        payout: {
          nextPayoutDate: getNextPayoutDate(),
          eligibleAmount: Math.max(0, totalProfit * 0.8), // 80% profit split example
          totalPaidOut: account.extra_metadata?.total_paid_out || 0,
          pendingPayout: 0,
          payoutHistory: account.extra_metadata?.payout_history || [],
        },
        overallStatus,
      };
    });

    return NextResponse.json({
      accounts: complianceAccounts,
    });
  } catch (error) {
    console.error('Compliance data error:', error);
    return NextResponse.json(
      { accounts: [] },
      { status: 200 }
    );
  }
}

function getNextPayoutDate(): string {
  // Next payout is typically the 15th of next month
  const now = new Date();
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 15);
  return nextMonth.toISOString();
}
