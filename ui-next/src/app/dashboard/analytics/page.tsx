'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  AlertTriangle,
  Shield,
  Clock,
  Calendar,
  BarChart3,
  Percent,
  DollarSign,
  Zap,
  Brain,
  Newspaper,
  GitBranch,
  Scale,
  LineChart,
  RefreshCw,
  CheckCircle,
  XCircle,
  Pause,
  Play,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

// Types
interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  gross_profit: number;
  gross_loss: number;
  net_profit: number;
  profit_factor: number | null;
  expectancy: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  current_streak: number;
  best_hour: number | null;
  best_day: number | null;
  sharpe_ratio: number | null;
}

interface StrategyStats {
  strategy_name: string;
  total_trades: number;
  win_rate: number;
  net_profit: number;
  profit_factor: number | null;
  expectancy: number | null;
  current_streak: number;
  is_active: boolean;
}

interface TimeStats {
  value: number;
  total_trades: number;
  win_rate: number;
  net_pnl: number;
  is_recommended: boolean;
}

interface CircuitBreakerStatus {
  can_trade: boolean;
  block_reason: string | null;
  active_events: Array<{
    trigger_type: string;
    trigger_value: number;
    triggered_at: string;
  }>;
}

interface EquityCurveStatus {
  is_trading_allowed: boolean;
  is_above_ma: boolean;
  cumulative_pnl: number;
  equity_ma: number;
  trade_count: number;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const SESSIONS = ['Asian', 'London', 'Overlap', 'New York'];

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
  const [strategies, setStrategies] = useState<StrategyStats[]>([]);
  const [timeAnalysis, setTimeAnalysis] = useState<{
    hourly: TimeStats[];
    daily: TimeStats[];
    session: TimeStats[];
  }>({ hourly: [], daily: [], session: [] });
  const [circuitBreaker, setCircuitBreaker] = useState<CircuitBreakerStatus | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityCurveStatus | null>(null);

  // Settings states
  const [cbSettings, setCbSettings] = useState({
    daily_loss_limit_enabled: true,
    daily_loss_limit_pct: 3,
    consecutive_loss_enabled: true,
    max_consecutive_losses: 5,
    auto_resume_enabled: true,
  });

  const [newsSettings, setNewsSettings] = useState({
    enabled: false,
    filter_high_impact: true,
    pause_minutes_before: 15,
    pause_minutes_after: 15,
  });

  const [correlationSettings, setCorrelationSettings] = useState({
    enabled: false,
    max_positive_correlation: 0.7,
  });

  const [dynamicSizing, setDynamicSizing] = useState({
    enabled: false,
    equity_curve_enabled: false,
    pause_below_ma: false,
  });

  const { toast } = useToast();

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [perfRes, stratRes, timeRes, cbRes, eqRes, cbSettingsRes, newsRes, corrRes, dsRes] = await Promise.all([
        fetch('/api/analytics/trading/performance'),
        fetch('/api/analytics/trading/strategies'),
        fetch('/api/analytics/trading/time-analysis'),
        fetch('/api/analytics/trading/circuit-breaker/status'),
        fetch('/api/analytics/trading/equity-curve'),
        fetch('/api/analytics/trading/circuit-breaker/settings'),
        fetch('/api/analytics/trading/news-filter/settings'),
        fetch('/api/analytics/trading/correlation-filter/settings'),
        fetch('/api/analytics/trading/dynamic-sizing/settings'),
      ]);

      if (perfRes.ok) setPerformance(await perfRes.json());
      if (stratRes.ok) setStrategies(await stratRes.json());
      if (timeRes.ok) setTimeAnalysis(await timeRes.json());
      if (cbRes.ok) setCircuitBreaker(await cbRes.json());
      if (eqRes.ok) setEquityCurve(await eqRes.json());
      if (cbSettingsRes.ok) setCbSettings(await cbSettingsRes.json());
      if (newsRes.ok) setNewsSettings(await newsRes.json());
      if (corrRes.ok) setCorrelationSettings(await corrRes.json());
      if (dsRes.ok) setDynamicSizing(await dsRes.json());
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateSettings = async (endpoint: string, data: Record<string, unknown>) => {
    try {
      const res = await fetch(`/api/analytics/trading/${endpoint}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        toast({ title: 'Settings Updated', description: 'Your changes have been saved.' });
        fetchAllData();
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update settings.', variant: 'destructive' });
    }
  };

  const resetCircuitBreakers = async () => {
    try {
      const res = await fetch('/api/analytics/trading/circuit-breaker/reset', { method: 'POST' });
      if (res.ok) {
        toast({ title: 'Circuit Breakers Reset', description: 'Trading has been resumed.' });
        fetchAllData();
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to reset circuit breakers.', variant: 'destructive' });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Trading Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Performance metrics, risk controls, and trading intelligence
          </p>
        </div>
        <Button onClick={fetchAllData} variant="outline" size="sm" className="w-fit">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Circuit Breaker Alert */}
      {circuitBreaker && !circuitBreaker.can_trade && (
        <Card className="border-destructive bg-destructive/10">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-6 h-6 text-destructive" />
                <div>
                  <p className="font-semibold text-destructive">Trading Paused</p>
                  <p className="text-sm text-muted-foreground">{circuitBreaker.block_reason}</p>
                </div>
              </div>
              <Button onClick={resetCircuitBreakers} variant="destructive" size="sm">
                <Play className="w-4 h-4 mr-2" />
                Resume Trading
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Performance Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.win_rate?.toFixed(1) || 0}%</div>
            <p className="text-xs text-muted-foreground">
              {performance?.winning_trades || 0}W / {performance?.losing_trades || 0}L
            </p>
            <Progress
              value={performance?.win_rate || 0}
              className="mt-2 h-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Net Profit</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              (performance?.net_profit || 0) >= 0 ? "text-green-500" : "text-red-500"
            )}>
              ${performance?.net_profit?.toFixed(2) || '0.00'}
            </div>
            <p className="text-xs text-muted-foreground">
              {performance?.total_trades || 0} total trades
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Profit Factor</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              (performance?.profit_factor || 0) >= 1.5 ? "text-green-500" :
              (performance?.profit_factor || 0) >= 1 ? "text-yellow-500" : "text-red-500"
            )}>
              {performance?.profit_factor?.toFixed(2) || 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              {(performance?.profit_factor || 0) >= 1.5 ? 'Good edge' :
               (performance?.profit_factor || 0) >= 1 ? 'Break even' : 'Needs work'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">
              {performance?.max_drawdown_pct?.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              ${performance?.max_drawdown?.toFixed(2) || '0.00'} peak to trough
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Additional Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Expectancy</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              (performance?.expectancy || 0) >= 0 ? "text-green-500" : "text-red-500"
            )}>
              ${performance?.expectancy?.toFixed(2) || '0.00'}
            </div>
            <p className="text-xs text-muted-foreground">
              Expected profit per trade
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Streak</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              (performance?.current_streak || 0) > 0 ? "text-green-500" :
              (performance?.current_streak || 0) < 0 ? "text-red-500" : ""
            )}>
              {(performance?.current_streak || 0) > 0 ? '+' : ''}{performance?.current_streak || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {(performance?.current_streak || 0) > 0 ? 'Winning streak' :
               (performance?.current_streak || 0) < 0 ? 'Losing streak' : 'No streak'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sharpe Ratio</CardTitle>
            <LineChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              (performance?.sharpe_ratio || 0) >= 1 ? "text-green-500" : "text-yellow-500"
            )}>
              {performance?.sharpe_ratio?.toFixed(2) || 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              Risk-adjusted returns
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for different sections */}
      <Tabs defaultValue="time" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1 p-1 md:grid md:w-full md:grid-cols-5">
          <TabsTrigger value="time" className="flex-1 min-w-[80px] text-xs md:text-sm">
            <Clock className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Time Analysis</span>
            <span className="md:hidden">Time</span>
          </TabsTrigger>
          <TabsTrigger value="strategies" className="flex-1 min-w-[80px] text-xs md:text-sm">
            <BarChart3 className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Strategies</span>
            <span className="md:hidden">Stats</span>
          </TabsTrigger>
          <TabsTrigger value="circuit" className="flex-1 min-w-[80px] text-xs md:text-sm">
            <Shield className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Circuit Breakers</span>
            <span className="md:hidden">Limits</span>
          </TabsTrigger>
          <TabsTrigger value="filters" className="flex-1 min-w-[80px] text-xs md:text-sm">
            <Newspaper className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Filters</span>
            <span className="md:hidden">Filter</span>
          </TabsTrigger>
          <TabsTrigger value="sizing" className="flex-1 min-w-[80px] text-xs md:text-sm">
            <Scale className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Position Sizing</span>
            <span className="md:hidden">Size</span>
          </TabsTrigger>
        </TabsList>

        {/* Time Analysis Tab */}
        <TabsContent value="time" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Best Trading Hours */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Best Trading Hours (UTC)
                </CardTitle>
                <CardDescription>Performance by hour of day</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-6 gap-1">
                  {Array.from({ length: 24 }, (_, i) => {
                    const hourStat = timeAnalysis.hourly.find(h => h.value === i);
                    const winRate = hourStat?.win_rate || 0;
                    const trades = hourStat?.total_trades || 0;
                    const isRecommended = hourStat?.is_recommended ?? true;

                    return (
                      <div
                        key={i}
                        className={cn(
                          "p-2 rounded text-center text-xs border",
                          trades === 0 ? "bg-muted/50 text-muted-foreground" :
                          isRecommended ? "bg-green-500/20 border-green-500/50" :
                          "bg-red-500/20 border-red-500/50"
                        )}
                        title={`${i}:00 - ${trades} trades, ${winRate.toFixed(0)}% win rate`}
                      >
                        <div className="font-medium">{i}h</div>
                        {trades > 0 && (
                          <div className="text-[10px]">{winRate.toFixed(0)}%</div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-green-500/20 border border-green-500/50" />
                    Recommended
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-red-500/20 border border-red-500/50" />
                    Avoid
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Best Trading Days */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="w-5 h-5" />
                  Best Trading Days
                </CardTitle>
                <CardDescription>Performance by day of week</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {DAYS.map((day, i) => {
                    const dayStat = timeAnalysis.daily.find(d => d.value === i);
                    const winRate = dayStat?.win_rate || 0;
                    const trades = dayStat?.total_trades || 0;
                    const pnl = dayStat?.net_pnl || 0;
                    const isRecommended = dayStat?.is_recommended ?? true;

                    return (
                      <div key={day} className="flex items-center gap-3">
                        <div className="w-24 text-sm font-medium">{day}</div>
                        <div className="flex-1">
                          <Progress
                            value={winRate}
                            className={cn(
                              "h-4",
                              isRecommended ? "[&>div]:bg-green-500" : "[&>div]:bg-red-500"
                            )}
                          />
                        </div>
                        <div className="w-16 text-right text-sm">
                          {winRate.toFixed(0)}%
                        </div>
                        <div className={cn(
                          "w-20 text-right text-sm font-medium",
                          pnl >= 0 ? "text-green-500" : "text-red-500"
                        )}>
                          ${pnl.toFixed(0)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Trading Sessions */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Performance by Session
                </CardTitle>
                <CardDescription>Asian, London, NY Overlap, and New York sessions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4">
                  {SESSIONS.map((session, i) => {
                    const sessionStat = timeAnalysis.session.find(s => s.value === i);
                    const winRate = sessionStat?.win_rate || 0;
                    const trades = sessionStat?.total_trades || 0;
                    const pnl = sessionStat?.net_pnl || 0;
                    const isRecommended = sessionStat?.is_recommended ?? true;

                    return (
                      <Card key={session} className={cn(
                        "border-2",
                        trades === 0 ? "border-muted" :
                        isRecommended ? "border-green-500/50" : "border-red-500/50"
                      )}>
                        <CardContent className="pt-4 text-center">
                          <div className="text-lg font-semibold">{session}</div>
                          <div className="text-3xl font-bold mt-2">
                            {winRate.toFixed(0)}%
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {trades} trades
                          </div>
                          <div className={cn(
                            "text-sm font-medium mt-1",
                            pnl >= 0 ? "text-green-500" : "text-red-500"
                          )}>
                            ${pnl.toFixed(2)}
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Strategies Tab */}
        <TabsContent value="strategies" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Strategy Performance</CardTitle>
              <CardDescription>Compare performance across your trading strategies</CardDescription>
            </CardHeader>
            <CardContent>
              {strategies.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No strategy data yet.</p>
                  <p className="text-sm">Add a "strategy" field to your TradingView alerts to track performance per strategy.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {strategies.map((strategy) => (
                    <div key={strategy.strategy_name} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Badge variant={strategy.is_active ? "default" : "secondary"}>
                          {strategy.is_active ? 'Active' : 'Paused'}
                        </Badge>
                        <div>
                          <div className="font-medium">{strategy.strategy_name}</div>
                          <div className="text-sm text-muted-foreground">
                            {strategy.total_trades} trades
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-6 text-sm">
                        <div className="text-center">
                          <div className="font-medium">{strategy.win_rate.toFixed(1)}%</div>
                          <div className="text-muted-foreground">Win Rate</div>
                        </div>
                        <div className="text-center">
                          <div className={cn(
                            "font-medium",
                            strategy.net_profit >= 0 ? "text-green-500" : "text-red-500"
                          )}>
                            ${strategy.net_profit.toFixed(2)}
                          </div>
                          <div className="text-muted-foreground">Net P&L</div>
                        </div>
                        <div className="text-center">
                          <div className="font-medium">{strategy.profit_factor?.toFixed(2) || 'N/A'}</div>
                          <div className="text-muted-foreground">Profit Factor</div>
                        </div>
                        <div className="text-center">
                          <div className={cn(
                            "font-medium",
                            strategy.current_streak > 0 ? "text-green-500" :
                            strategy.current_streak < 0 ? "text-red-500" : ""
                          )}>
                            {strategy.current_streak > 0 ? '+' : ''}{strategy.current_streak}
                          </div>
                          <div className="text-muted-foreground">Streak</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Circuit Breakers Tab */}
        <TabsContent value="circuit" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  Circuit Breaker Status
                </CardTitle>
                <CardDescription>Current trading protection status</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className={cn(
                  "p-4 rounded-lg border-2 flex items-center justify-between",
                  circuitBreaker?.can_trade
                    ? "border-green-500/50 bg-green-500/10"
                    : "border-red-500/50 bg-red-500/10"
                )}>
                  <div className="flex items-center gap-3">
                    {circuitBreaker?.can_trade ? (
                      <CheckCircle className="w-6 h-6 text-green-500" />
                    ) : (
                      <XCircle className="w-6 h-6 text-red-500" />
                    )}
                    <div>
                      <div className="font-semibold">
                        {circuitBreaker?.can_trade ? 'Trading Active' : 'Trading Paused'}
                      </div>
                      {circuitBreaker?.block_reason && (
                        <div className="text-sm text-muted-foreground">
                          {circuitBreaker.block_reason}
                        </div>
                      )}
                    </div>
                  </div>
                  {!circuitBreaker?.can_trade && (
                    <Button onClick={resetCircuitBreakers} size="sm">
                      Resume
                    </Button>
                  )}
                </div>

                {circuitBreaker?.active_events && circuitBreaker.active_events.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Active Events</div>
                    {circuitBreaker.active_events.map((event, i) => (
                      <div key={i} className="p-2 bg-muted rounded text-sm">
                        <div className="font-medium">{event.trigger_type}</div>
                        <div className="text-muted-foreground">
                          Value: {event.trigger_value} | {new Date(event.triggered_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Circuit Breaker Settings</CardTitle>
                <CardDescription>Configure automatic trading pauses</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Daily Loss Limit</Label>
                      <p className="text-sm text-muted-foreground">Pause if daily loss exceeds %</p>
                    </div>
                    <Switch
                      checked={cbSettings.daily_loss_limit_enabled}
                      onCheckedChange={(v) => {
                        setCbSettings(s => ({ ...s, daily_loss_limit_enabled: v }));
                        updateSettings('circuit-breaker/settings', { daily_loss_limit_enabled: v });
                      }}
                    />
                  </div>
                  {cbSettings.daily_loss_limit_enabled && (
                    <div className="pl-4 border-l-2 space-y-2">
                      <Label>Loss Limit: {cbSettings.daily_loss_limit_pct}%</Label>
                      <Slider
                        value={[cbSettings.daily_loss_limit_pct]}
                        onValueChange={(v) => setCbSettings(s => ({ ...s, daily_loss_limit_pct: v[0] }))}
                        onValueCommit={(v) => updateSettings('circuit-breaker/settings', { daily_loss_limit_pct: v[0] })}
                        min={1}
                        max={20}
                        step={0.5}
                      />
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Consecutive Loss Limit</Label>
                      <p className="text-sm text-muted-foreground">Pause after X consecutive losses</p>
                    </div>
                    <Switch
                      checked={cbSettings.consecutive_loss_enabled}
                      onCheckedChange={(v) => {
                        setCbSettings(s => ({ ...s, consecutive_loss_enabled: v }));
                        updateSettings('circuit-breaker/settings', { consecutive_loss_enabled: v });
                      }}
                    />
                  </div>
                  {cbSettings.consecutive_loss_enabled && (
                    <div className="pl-4 border-l-2 space-y-2">
                      <Label>Max Losses: {cbSettings.max_consecutive_losses}</Label>
                      <Slider
                        value={[cbSettings.max_consecutive_losses]}
                        onValueChange={(v) => setCbSettings(s => ({ ...s, max_consecutive_losses: v[0] }))}
                        onValueCommit={(v) => updateSettings('circuit-breaker/settings', { max_consecutive_losses: v[0] })}
                        min={2}
                        max={10}
                        step={1}
                      />
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto Resume</Label>
                    <p className="text-sm text-muted-foreground">Automatically resume after cooldown</p>
                  </div>
                  <Switch
                    checked={cbSettings.auto_resume_enabled}
                    onCheckedChange={(v) => {
                      setCbSettings(s => ({ ...s, auto_resume_enabled: v }));
                      updateSettings('circuit-breaker/settings', { auto_resume_enabled: v });
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Filters Tab */}
        <TabsContent value="filters" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Newspaper className="w-5 h-5" />
                  News Filter
                </CardTitle>
                <CardDescription>Pause trading around economic events</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable News Filter</Label>
                    <p className="text-sm text-muted-foreground">Pause trades before high-impact news</p>
                  </div>
                  <Switch
                    checked={newsSettings.enabled}
                    onCheckedChange={(v) => {
                      setNewsSettings(s => ({ ...s, enabled: v }));
                      updateSettings('news-filter/settings', { enabled: v });
                    }}
                  />
                </div>

                {newsSettings.enabled && (
                  <div className="space-y-4 pt-4 border-t">
                    <div className="flex items-center justify-between">
                      <Label>Filter High Impact Events</Label>
                      <Switch
                        checked={newsSettings.filter_high_impact}
                        onCheckedChange={(v) => {
                          setNewsSettings(s => ({ ...s, filter_high_impact: v }));
                          updateSettings('news-filter/settings', { filter_high_impact: v });
                        }}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Pause Before (min)</Label>
                        <Input
                          type="number"
                          value={newsSettings.pause_minutes_before}
                          onChange={(e) => setNewsSettings(s => ({ ...s, pause_minutes_before: parseInt(e.target.value) || 15 }))}
                          onBlur={() => updateSettings('news-filter/settings', { pause_minutes_before: newsSettings.pause_minutes_before })}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Resume After (min)</Label>
                        <Input
                          type="number"
                          value={newsSettings.pause_minutes_after}
                          onChange={(e) => setNewsSettings(s => ({ ...s, pause_minutes_after: parseInt(e.target.value) || 15 }))}
                          onBlur={() => updateSettings('news-filter/settings', { pause_minutes_after: newsSettings.pause_minutes_after })}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GitBranch className="w-5 h-5" />
                  Correlation Filter
                </CardTitle>
                <CardDescription>Prevent correlated trades</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable Correlation Filter</Label>
                    <p className="text-sm text-muted-foreground">Block correlated positions</p>
                  </div>
                  <Switch
                    checked={correlationSettings.enabled}
                    onCheckedChange={(v) => {
                      setCorrelationSettings(s => ({ ...s, enabled: v }));
                      updateSettings('correlation-filter/settings', { enabled: v });
                    }}
                  />
                </div>

                {correlationSettings.enabled && (
                  <div className="space-y-4 pt-4 border-t">
                    <div className="space-y-2">
                      <Label>Max Correlation: {(correlationSettings.max_positive_correlation * 100).toFixed(0)}%</Label>
                      <p className="text-xs text-muted-foreground">Block if symbols are more correlated than this</p>
                      <Slider
                        value={[correlationSettings.max_positive_correlation * 100]}
                        onValueChange={(v) => setCorrelationSettings(s => ({ ...s, max_positive_correlation: v[0] / 100 }))}
                        onValueCommit={(v) => updateSettings('correlation-filter/settings', { max_positive_correlation: v[0] / 100 })}
                        min={50}
                        max={100}
                        step={5}
                      />
                    </div>
                    <div className="p-3 bg-muted rounded text-sm">
                      <div className="font-medium mb-1">Built-in Correlations:</div>
                      <div className="text-muted-foreground">ES/NQ: 92% | ES/YM: 95% | EURUSD/GBPUSD: 85%</div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Position Sizing Tab */}
        <TabsContent value="sizing" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Scale className="w-5 h-5" />
                  Dynamic Position Sizing
                </CardTitle>
                <CardDescription>Adjust size based on performance</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable Dynamic Sizing</Label>
                    <p className="text-sm text-muted-foreground">Auto-adjust position size</p>
                  </div>
                  <Switch
                    checked={dynamicSizing.enabled}
                    onCheckedChange={(v) => {
                      setDynamicSizing(s => ({ ...s, enabled: v }));
                      updateSettings('dynamic-sizing/settings', { enabled: v });
                    }}
                  />
                </div>

                {dynamicSizing.enabled && (
                  <div className="space-y-4 pt-4 border-t">
                    <div className="p-3 bg-muted rounded text-sm">
                      <div className="font-medium mb-1">How it works:</div>
                      <ul className="list-disc list-inside text-muted-foreground space-y-1">
                        <li>Increase size after 3+ winning trades</li>
                        <li>Decrease size after 2+ losing trades</li>
                        <li>Never exceed 2x or go below 0.25x base size</li>
                      </ul>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LineChart className="w-5 h-5" />
                  Equity Curve Trading
                </CardTitle>
                <CardDescription>Trade only when equity above MA</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Equity Curve Status */}
                <div className={cn(
                  "p-4 rounded-lg border-2",
                  equityCurve?.is_above_ma
                    ? "border-green-500/50 bg-green-500/10"
                    : "border-yellow-500/50 bg-yellow-500/10"
                )}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">
                        {equityCurve?.is_above_ma ? 'Above MA' : 'Below MA'}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        P&L: ${equityCurve?.cumulative_pnl?.toFixed(2) || 0} | MA: ${equityCurve?.equity_ma?.toFixed(2) || 0}
                      </div>
                    </div>
                    <div className="text-right text-sm text-muted-foreground">
                      {equityCurve?.trade_count || 0} trades
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable Equity Curve Filter</Label>
                    <p className="text-sm text-muted-foreground">Reduce/pause when below MA</p>
                  </div>
                  <Switch
                    checked={dynamicSizing.equity_curve_enabled}
                    onCheckedChange={(v) => {
                      setDynamicSizing(s => ({ ...s, equity_curve_enabled: v }));
                      updateSettings('dynamic-sizing/settings', { equity_curve_enabled: v });
                    }}
                  />
                </div>

                {dynamicSizing.equity_curve_enabled && (
                  <div className="flex items-center justify-between pl-4 border-l-2">
                    <div>
                      <Label>Pause Below MA</Label>
                      <p className="text-sm text-muted-foreground">Stop trading entirely</p>
                    </div>
                    <Switch
                      checked={dynamicSizing.pause_below_ma}
                      onCheckedChange={(v) => {
                        setDynamicSizing(s => ({ ...s, pause_below_ma: v }));
                        updateSettings('dynamic-sizing/settings', { pause_below_ma: v });
                      }}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
