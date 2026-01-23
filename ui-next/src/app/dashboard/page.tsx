'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, Users, Signal, TrendingUp, CalendarClock } from 'lucide-react';
import { BrokerHealthGrid } from '@/components/brokers/broker-health-grid';
import {
  ExpirationAlerts,
  FuturesInfo,
} from '@/components/positions/expiration-badge';
import { RiskUsageWidget } from '@/components/dashboard/risk-usage-widget';
import { RejectedSignalsWidget } from '@/components/dashboard/rejected-signals-widget';
import { TestWebhookButton } from '@/components/dashboard/test-webhook-button';
import {
  StatCardSkeleton,
  BrokerGridSkeleton,
  WidgetSkeleton,
} from '@/components/dashboard/dashboard-skeleton';
import { RecentExecutionsWidget } from '@/components/dashboard/recent-executions-widget';
import { EquityChartWidget } from '@/components/dashboard/equity-chart-widget';
import { TrialStatusWidget } from '@/components/dashboard/trial-status-widget';
import { OpenPositionsWidget } from '@/components/dashboard/open-positions-widget';
import { FlowGuardBot } from '@/components/signal-intelligence/flowguard-bot';
import { SignalHeatMap } from '@/components/signal-intelligence/signal-heat-map';
import { useWebSocketContext } from '@/providers/websocket-provider';
import { cn } from '@/lib/utils';

interface DashboardStats {
  activeSignals: number;
  connectedBrokers: number;
  todaysTrades: number;
  totalBalance: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    activeSignals: 0,
    connectedBrokers: 0,
    todaysTrades: 0,
    totalBalance: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expiringContracts, setExpiringContracts] = useState<FuturesInfo[]>([]);
  const [contractsLoading, setContractsLoading] = useState(true);
  const [recentlyUpdated, setRecentlyUpdated] = useState<string | null>(null);

  // WebSocket for real-time updates
  const { subscribeToSignals, subscribeToOrders, status: wsStatus } = useWebSocketContext();

  // Handle signal updates (increment active signals)
  const handleSignalUpdate = useCallback(() => {
    setStats((prev) => ({
      ...prev,
      activeSignals: prev.activeSignals + 1,
    }));
    // Visual feedback
    setRecentlyUpdated('signals');
    setTimeout(() => setRecentlyUpdated(null), 2000);
  }, []);

  // Handle order updates (trade executed - increment today's trades)
  const handleOrderUpdate = useCallback((data: { status: string }) => {
    if (data.status === 'filled' || data.status === 'executed') {
      setStats((prev) => ({
        ...prev,
        todaysTrades: prev.todaysTrades + 1,
      }));
      // Visual feedback
      setRecentlyUpdated('trades');
      setTimeout(() => setRecentlyUpdated(null), 2000);
    }
  }, []);

  // Subscribe to WebSocket updates
  useEffect(() => {
    const unsubSignals = subscribeToSignals(handleSignalUpdate);
    const unsubOrders = subscribeToOrders(handleOrderUpdate);

    return () => {
      unsubSignals();
      unsubOrders();
    };
  }, [subscribeToSignals, subscribeToOrders, handleSignalUpdate, handleOrderUpdate]);

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await fetch('/api/dashboard/stats');
        if (!response.ok) {
          throw new Error('Failed to fetch stats');
        }
        const data = await response.json();
        setStats(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard stats:', err);
        setError('Failed to load stats');
      } finally {
        setLoading(false);
      }
    }

    async function fetchExpiringContracts() {
      try {
        const response = await fetch('/api/dashboard/contracts?days=7');
        if (response.ok) {
          const data = await response.json();
          setExpiringContracts(data);
        }
      } catch (err) {
        console.error('Error fetching expiring contracts:', err);
      } finally {
        setContractsLoading(false);
      }
    }

    fetchStats();
    fetchExpiringContracts();
  }, []);

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const handleRollover = (contract: FuturesInfo) => {
    // For now, just log the rollover action
    // In the future, this could open a modal or navigate to account settings
    console.log('Rollover requested for:', contract.contractCode, '->', contract.nextContract);
    // Could navigate to accounts page with pre-filled symbol
    window.location.href = `/dashboard/settings/accounts?rollover=${contract.contractCode}`;
  };

  const statCards = [
    {
      key: 'signals',
      title: 'Active Signals',
      value: stats.activeSignals.toString(),
      description: 'Pending signals today',
      icon: Signal,
      iconColor: 'text-primary',
    },
    {
      key: 'brokers',
      title: 'Connected Brokers',
      value: stats.connectedBrokers.toString(),
      description: 'Active broker connections',
      icon: Users,
      iconColor: 'text-chart-2',
    },
    {
      key: 'trades',
      title: "Today's Trades",
      value: stats.todaysTrades.toString(),
      description: 'Executed today',
      icon: Activity,
      iconColor: 'text-chart-3',
    },
    {
      key: 'balance',
      title: 'Total Balance',
      value: formatCurrency(stats.totalBalance),
      description: 'Across all accounts',
      icon: TrendingUp,
      iconColor: 'text-chart-1',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome heading */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome to Tradeflow. Monitor your trading signals and accounts.
          </p>
        </div>
        {/* WebSocket connection indicator */}
        <div className="flex items-center gap-2 text-sm">
          <div
            className={cn(
              'h-2 w-2 rounded-full',
              wsStatus === 'connected' && 'bg-green-500',
              wsStatus === 'connecting' && 'bg-amber-500 animate-pulse',
              wsStatus === 'disconnected' && 'bg-red-500',
              wsStatus === 'error' && 'bg-red-500'
            )}
          />
          <span className="text-muted-foreground hidden sm:inline">
            {wsStatus === 'connected' ? 'Live' : wsStatus === 'connecting' ? 'Connecting...' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Row 1: Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          statCards.map((stat) => (
            <Card
              key={stat.key}
              className={cn(
                'transition-all duration-300',
                recentlyUpdated === stat.key && 'ring-2 ring-primary animate-pulse'
              )}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                <stat.icon className={`h-4 w-4 ${stat.iconColor}`} />
              </CardHeader>
              <CardContent>
                {error ? (
                  <div className="text-2xl font-bold text-muted-foreground">-</div>
                ) : (
                  <div className="text-2xl font-bold">{stat.value}</div>
                )}
                <p className="text-xs text-muted-foreground">{stat.description}</p>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Row 2: Equity chart (2/3) + Trial status (1/3) */}
      <div className="grid gap-4 lg:grid-cols-3">
        {loading ? (
          <>
            <WidgetSkeleton className="lg:col-span-2" />
            <WidgetSkeleton />
          </>
        ) : (
          <>
            <EquityChartWidget />
            <TrialStatusWidget />
          </>
        )}
      </div>

      {/* Quick Actions Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <TestWebhookButton />
        </CardContent>
      </Card>

      {/* Contract Expiration Alerts */}
      {!contractsLoading && expiringContracts.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <CalendarClock className="h-5 w-5 text-amber-500" />
            <CardTitle>Contract Expirations</CardTitle>
          </CardHeader>
          <CardContent>
            <ExpirationAlerts
              alerts={expiringContracts}
              onRollover={handleRollover}
            />
          </CardContent>
        </Card>
      )}

      {/* Row 3: Broker Connections */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold tracking-tight">Broker Connections</h2>
          <span className="text-sm text-muted-foreground">
            {loading ? '...' : `${stats.connectedBrokers} connected`}
          </span>
        </div>
        {loading ? <BrokerGridSkeleton /> : <BrokerHealthGrid />}
      </div>

      {/* Row 4: Open Positions + Recent Executions (side by side) */}
      <div className="grid gap-4 lg:grid-cols-2">
        {loading ? (
          <>
            <WidgetSkeleton />
            <WidgetSkeleton />
          </>
        ) : (
          <>
            <OpenPositionsWidget />
            <RecentExecutionsWidget />
          </>
        )}
      </div>

      {/* Row 5: Risk Usage + Rejected Signals */}
      <div className="grid gap-4 lg:grid-cols-2">
        {loading ? (
          <>
            <WidgetSkeleton />
            <WidgetSkeleton />
          </>
        ) : (
          <>
            <RiskUsageWidget />
            <RejectedSignalsWidget />
          </>
        )}
      </div>

      {/* Row 6: Signal Intelligence - Heat Map */}
      <div className="grid gap-4">
        <SignalHeatMap />
      </div>

      {/* FlowGuard Bot - Floating */}
      <FlowGuardBot />
    </div>
  );
}
