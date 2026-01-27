'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Activity, Users, Signal, TrendingUp, CalendarClock, KeyRound, Loader2, BarChart3, LayoutDashboard } from 'lucide-react';
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
import { GuardModal } from '@/components/signal-intelligence/guard-modal';
import { StreakBadge } from '@/components/dashboard/streak-badge';
import { OnboardingTooltip } from '@/components/dashboard/onboarding-tooltip';
import { LiveMarketChart } from '@/components/dashboard/live-market-chart';
import { useWebSocketContext } from '@/providers/websocket-provider';
import { cn } from '@/lib/utils';
import { CopyButton } from '@/components/ui/copy-button';
import { useToast } from '@/hooks/use-toast';
import { useUser } from '@/providers/user-provider';
import confetti from 'canvas-confetti';
import { useQueryClient } from '@tanstack/react-query';

interface PendingSignal {
  signal_id: string;
  symbol: string;
  action: string;
  quantity?: number;
  reason?: string;
  reason_detail?: string;
  warning_type?: string;
  message?: string;
}

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
  const [primaryWebhookKey, setPrimaryWebhookKey] = useState<string | null>(null);
  const [generatingKey, setGeneratingKey] = useState(false);

  // Guard modal state for pending webhook confirmations
  const [guardModalOpen, setGuardModalOpen] = useState(false);
  const [pendingSignal, setPendingSignal] = useState<PendingSignal | null>(null);

  // WebSocket for real-time updates
  const { subscribeToSignals, subscribeToOrders, status: wsStatus } = useWebSocketContext();
  const { user, refetch: refetchUser } = useUser();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const fireTestConfetti = useCallback(() => {
    confetti({
      particleCount: 120,
      spread: 70,
      origin: { y: 0.7 },
      colors: ['#10b981', '#3b82f6', '#22c55e'],
      zIndex: 9999,
    });
  }, []);

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

  // Poll for pending webhook confirmations (signals awaiting user action)
  useEffect(() => {
    async function checkPendingSignals() {
      try {
        const response = await fetch('/api/signals?status=pending_confirmation&limit=1', { credentials: 'include' });
        if (response.ok) {
          const data = await response.json();
          const signals = Array.isArray(data) ? data : (data?.signals || []);
          if (signals.length > 0 && !guardModalOpen) {
            const sig = signals[0];
            setPendingSignal({
              signal_id: sig.signal_id || sig.id?.toString(),
              symbol: sig.symbol,
              action: sig.action,
              quantity: sig.quantity,
              reason: sig.guard_reason || sig.reason,
              reason_detail: sig.reason_detail,
              warning_type: sig.warning_type || sig.guard_rule,
              message: sig.message || `Signal requires confirmation: ${sig.guard_reason || 'Manual review required'}`,
            });
            setGuardModalOpen(true);
          }
        }
      } catch (err) {
        // Silent fail - don't interrupt user experience
        console.debug('Error checking pending signals:', err);
      }
    }

    // Check immediately and then every 10 seconds
    checkPendingSignals();
    const interval = setInterval(checkPendingSignals, 10000);
    return () => clearInterval(interval);
  }, [guardModalOpen]);

  // Handle guard modal action completion
  const handleGuardActionComplete = useCallback(() => {
    setPendingSignal(null);
    // Refresh stats after action
    fetch('/api/dashboard/stats', { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await fetch('/api/dashboard/stats', { credentials: 'include' });
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
        const response = await fetch('/api/dashboard/contracts?days=7', { credentials: 'include' });
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

  useEffect(() => {
    setPrimaryWebhookKey(user?.primary_webhook_key || null);
  }, [user?.primary_webhook_key]);

  const handleGenerateWebhookKey = async () => {
    try {
      setGeneratingKey(true);
      const response = await fetch('/api/webhooks/generate-key', { method: 'POST', credentials: 'include' });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to generate webhook key' }));
        throw new Error(error.detail || 'Failed to generate webhook key');
      }
      const data = await response.json();
      setPrimaryWebhookKey(data.webhook_key || null);
      await refetchUser();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['user-profile'] }),
        queryClient.invalidateQueries({ queryKey: ['webhook-configs'] }),
      ]);
      toast({
        title: 'Webhook key updated',
        description: 'Your new webhook key is ready to copy.',
      });
    } catch (err) {
      console.error('Failed to generate webhook key:', err);
      toast({
        title: 'Webhook key update failed',
        description: err instanceof Error ? err.message : 'Failed to generate webhook key',
        variant: 'destructive',
      });
    } finally {
      setGeneratingKey(false);
    }
  };

  const handleTestWebhookSuccess = useCallback(() => {
    setRecentlyUpdated('trades');
    setTimeout(() => setRecentlyUpdated(null), 2000);
    fireTestConfetti();
  }, [fireTestConfetti]);

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
        {/* Streak badge + WebSocket connection indicator */}
        <div className="flex items-center gap-4">
          <StreakBadge />
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
      </div>

      {/* Dashboard Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <LayoutDashboard className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="live-market" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Live Market
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab Content */}
        <TabsContent value="overview" className="mt-6 space-y-6">
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
                'glass glass-hover transition-all duration-300',
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
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <TestWebhookButton onSuccess={handleTestWebhookSuccess} />
          </div>
          <div className="rounded-lg border bg-muted/40 p-4 space-y-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-primary" />
                  <p className="text-sm font-medium">Webhook Key</p>
                </div>
                <p className="text-xs text-muted-foreground">
                  Use this in your TradingView or webhook settings.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateWebhookKey}
                disabled={generatingKey}
              >
                {generatingKey ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  'Generate new key'
                )}
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 rounded-md bg-background px-3 py-2 font-mono text-xs break-all">
                {primaryWebhookKey || 'No key yet. Click generate to create one.'}
              </div>
              {primaryWebhookKey && (
                <CopyButton text={primaryWebhookKey} tooltip="Copy webhook key" />
              )}
            </div>
          </div>
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
        </TabsContent>

        {/* Live Market Tab Content */}
        <TabsContent value="live-market" className="mt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">Live Market Data</h2>
                <p className="text-sm text-muted-foreground">
                  Real-time charts and technical indicators for ProjectX/TopStep instruments
                </p>
              </div>
            </div>
            <LiveMarketChart />
          </div>
        </TabsContent>
      </Tabs>

      {/* FlowGuard Bot - Floating (available on all tabs) */}
      <FlowGuardBot />

      {/* Onboarding Tooltip for First-Time Users */}
      <OnboardingTooltip />

      {/* Guard Modal for Pending Webhook Confirmations */}
      {pendingSignal && (
        <GuardModal
          open={guardModalOpen}
          onOpenChange={setGuardModalOpen}
          modalData={{
            type: 'webhook_warning',
            message: pendingSignal.message || 'Signal requires confirmation',
            symbol: pendingSignal.symbol,
            action: pendingSignal.action,
            quantity: pendingSignal.quantity,
            reason: pendingSignal.reason,
            reason_detail: pendingSignal.reason_detail,
            warning_type: pendingSignal.warning_type,
          }}
          signalId={pendingSignal.signal_id}
          onActionComplete={handleGuardActionComplete}
        />
      )}
    </div>
  );
}
