'use client';

import { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, RefreshCw, Zap, Activity, TrendingUp, TrendingDown, Minus, Save, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DeterministicDashboard } from '@/components/smartflow/deterministic-dashboard';
import { EliteDashboard } from '@/components/smartflow/elite-dashboard';
import { ForwardTestDashboard } from '@/components/smartflow/forward-test-dashboard';
import { MLDashboard } from '@/components/smartflow/ml-dashboard';
import { AIAnalysisDashboard } from '@/components/smartflow/ai-analysis-dashboard';
import { QuickModeDashboard } from '@/components/smartflow/quick-mode-dashboard';
import { CompareEnginesDashboard } from '@/components/smartflow/compare-engines-dashboard';
import { AdaptiveRouterDashboard } from '@/components/smartflow/adaptive-router-dashboard';
import { StrategiesOverview } from '@/components/smartflow/strategies-overview';
import { WebhooksDashboard } from '@/components/smartflow/webhooks-dashboard';
import { LiveSignalsDashboard } from '@/components/smartflow/live-signals-dashboard';
import { TabContainer } from '@/components/smartflow/TabContainer';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';

interface SmartFlowConfig {
  enabled: boolean;
  enable_ai_only_mode?: boolean;
  enable_deterministic_mode?: boolean;
  enable_quick_mode?: boolean;
  enable_ai_enhancement?: boolean;
  [key: string]: any;
}

interface SmartFlowStatus {
  enabled: boolean;
  latest_scores: any;
  recent_signals: any[];
}

interface Strategy {
  strategy_id: string;
  strategy_type: string;
  version: string;
  status: string;
  sharpe_ratio?: number;
  win_rate?: number;
  total_trades?: number;
}

export default function SmartFlowPage() {
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<SmartFlowConfig>({
    enabled: false,
    enable_ai_only_mode: false,
    enable_deterministic_mode: true,
    enable_quick_mode: true,
  });
  const [status, setStatus] = useState<SmartFlowStatus | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  // Backtest config - lifted to parent to persist across re-renders
  const [backtestConfig, setBacktestConfig] = useState({
    ticker: 'MES',
    days: 90,
    engine_type: 'unified',
    initial_capital: 25000,
    position_size_pct: 2.0,
    use_atr_stops: true,
    atr_stop_mult: 2.0,
    atr_target_mult: 3.0,
    use_pct_stops: false,
    pct_stop: 2.5,
    pct_target: 2.5,
  });
  const { toast } = useToast();

  useEffect(() => {
    loadConfig();
    loadStatus();
    loadStrategies();
    const interval = setInterval(loadStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/config', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
      }
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/status', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  const loadStrategies = async () => {
    try {
      const response = await fetch('/api/strategies', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setStrategies(data.strategies || []);
      }
    } catch (error) {
      console.error('Failed to load strategies:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadStatus();
    await loadStrategies();
    setTimeout(() => setRefreshing(false), 500);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const getScoreBadge = (score: number) => {
    if (score > 4) {
      return <Badge className="bg-green-500"><TrendingUp className="h-3 w-3 mr-1" /> Strong Buy</Badge>;
    } else if (score > 2) {
      return <Badge className="bg-green-600/70"><TrendingUp className="h-3 w-3 mr-1" /> Bullish</Badge>;
    } else if (score < -4) {
      return <Badge className="bg-red-500"><TrendingDown className="h-3 w-3 mr-1" /> Strong Sell</Badge>;
    } else if (score < -2) {
      return <Badge className="bg-red-600/70"><TrendingDown className="h-3 w-3 mr-1" /> Bearish</Badge>;
    } else {
      return <Badge variant="outline"><Minus className="h-3 w-3 mr-1" /> Neutral</Badge>;
    }
  };

  const formatWinRate = (value?: number) => {
    if (value === null || value === undefined) {
      return '-';
    }
    const normalized = value <= 1 ? value * 100 : value;
    return `${normalized.toFixed(1)}%`;
  };

  // Overview Tab Content
  const OverviewContent = () => (
    <div className="space-y-4">
      {/* Live Signals Dashboard - Prominent placement for real-time visibility */}
      <LiveSignalsDashboard className="border-2 border-green-500/20" />

      {/* Engine Status Summary */}
      <Card className="border-2 border-primary/20">
        <CardHeader>
          <CardTitle>All Strategy Engines</CardTitle>
          <CardDescription>
            {strategies.length} strategies registered. Router selects best engine per regime.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {strategies.map((strategy) => {
              const isActive = ['built_in', 'active', 'approved_for_router'].includes(strategy.status);
              const isForwardTesting = strategy.status === 'forward_testing';
              const color = isForwardTesting ? 'purple' : isActive ? 'green' : 'gray';

              return (
                <Card key={strategy.strategy_id} className={cn("border-2",
                  isForwardTesting ? "border-purple-500/50 bg-purple-500/5" :
                  isActive ? "border-green-500/50 bg-green-500/5" : "border-gray-300")}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm capitalize">{strategy.strategy_type}</CardTitle>
                      {isActive && <Activity className="h-4 w-4 text-green-500 animate-pulse" />}
                      {isForwardTesting && <Activity className="h-4 w-4 text-purple-500 animate-pulse" />}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Badge className={
                      isForwardTesting ? "bg-purple-500" :
                      isActive ? "bg-green-500" : "bg-gray-500"
                    }>
                      {isForwardTesting ? "FORWARD TEST" : isActive ? "ACTIVE" : strategy.status.toUpperCase()}
                    </Badge>
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div className="flex justify-between">
                        <span>Sharpe:</span>
                        <span className="font-medium">{strategy.sharpe_ratio?.toFixed(2) || '-'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Win Rate:</span>
                        <span className="font-medium">{formatWinRate(strategy.win_rate)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Trades:</span>
                        <span className="font-medium">{strategy.total_trades || 0}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Flow Engine Live Scores (if enabled) */}
      {config.enabled && status?.latest_scores && (
        <Card>
          <CardHeader>
            <CardTitle>Flow Engine - Live Sentiment Scores</CardTitle>
            <CardDescription>Real-time institutional options flow analysis</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {['SPY', 'QQQ', 'IWM', 'DIA', 'GLD'].map((ticker) => {
                const scoreData = status.latest_scores[ticker];
                const score = scoreData?.score || 0;
                const bullish = scoreData?.bullish_flows || 0;
                const bearish = scoreData?.bearish_flows || 0;
                const premium = scoreData?.total_premium || 0;

                return (
                  <Card key={ticker} className="border">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg">{ticker}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="text-2xl font-bold">
                          <span className={score > 0 ? "text-green-500" : score < 0 ? "text-red-500" : "text-gray-500"}>
                            {score > 0 ? '+' : ''}{score.toFixed(1)}
                          </span>
                        </div>
                        <div>{getScoreBadge(score)}</div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <div className="text-muted-foreground">Bullish</div>
                            <div className="font-semibold text-green-500">{bullish}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Bearish</div>
                            <div className="font-semibold text-red-500">{bearish}</div>
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          ${(premium / 1000000).toFixed(2)}M premium
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );

  // Engines Tab Content
  const EnginesContent = () => (
    <div className="space-y-6">
      {/* Flow Engine Panel */}
      <Card className="border-2 border-blue-500/20">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-blue-500" />
                Flow Engine
                <Badge className={config.enabled ? "bg-green-500" : "bg-gray-500"}>
                  {config.enabled ? "ACTIVE" : "OFF"}
                </Badge>
              </CardTitle>
              <CardDescription>
                Institutional options flow sentiment analysis from FlowAlgo
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {config.enabled && status?.latest_scores ? (
            <div className="text-sm text-muted-foreground">
              Currently monitoring: SPY, QQQ, IWM, DIA, GLD
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              Enable SmartFlow to activate flow engine
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI Engine Panel */}
      <Card className="border-2 border-purple-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            AI Engine
            <Badge className={config.enable_ai_only_mode ? "bg-purple-500" : "bg-gray-500"}>
              {config.enable_ai_only_mode ? "ACTIVE" : "STANDBY"}
            </Badge>
          </CardTitle>
          <CardDescription>
            24/7 AI-driven analysis for futures, forex, and crypto
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AIAnalysisDashboard />
        </CardContent>
      </Card>

      {/* Deterministic Engine Panel */}
      <Card className="border-2 border-emerald-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Deterministic Engine
            <Badge className={config.enable_deterministic_mode ? "bg-emerald-500" : "bg-gray-500"}>
              {config.enable_deterministic_mode ? "RUNNING" : "OFF"}
            </Badge>
            <Badge variant="outline">NO AI</Badge>
          </CardTitle>
          <CardDescription>
            Multi-timeframe technical indicators with volume analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DeterministicDashboard />
        </CardContent>
      </Card>

      {/* Quick Mode Panel */}
      <Card className="border-2 border-amber-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Quick Mode Engine
            <Badge className={config.enable_quick_mode ? "bg-amber-500" : "bg-gray-500"}>
              {config.enable_quick_mode ? "RUNNING" : "OFF"}
            </Badge>
          </CardTitle>
          <CardDescription>
            5-minute momentum scalping with optional 15m confirmation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <QuickModeDashboard />
        </CardContent>
      </Card>
    </div>
  );

  // Analytics Tab Content
  const AnalyticsContent = () => (
    <div className="space-y-4">
      <Card className="border-2 border-yellow-500/20">
        <CardHeader>
          <CardTitle>SmartFlow Elite Analytics</CardTitle>
          <CardDescription>
            Regime detection, CVaR risk metrics, and performance analytics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EliteDashboard />
        </CardContent>
      </Card>

      <Card className="border-2 border-violet-500/20">
        <CardHeader>
          <CardTitle>ML Learning Engine</CardTitle>
          <CardDescription>Machine learning insights and pattern recognition</CardDescription>
        </CardHeader>
        <CardContent>
          <MLDashboard />
        </CardContent>
      </Card>
    </div>
  );

  // Forward Test Tab Content
  const ForwardTestContent = () => (
    <Card className="border-2 border-cyan-500/20">
      <CardHeader>
        <CardTitle>Forward Test - Live Paper Trading</CardTitle>
        <CardDescription>
          Real-time paper trading with full decision trace. Click any trade to see WHY it fired.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ForwardTestDashboard />
      </CardContent>
    </Card>
  );

  // Backtest Tab Content - Single Run
  // Note: backtestConfig is now managed at parent level to persist across re-renders
  const SingleRunContent = () => {
    const [running, setRunning] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [loadingResults, setLoadingResults] = useState(true);

    useEffect(() => {
      loadPreviousResults();
    }, []);

    const loadPreviousResults = async () => {
      try {
        const response = await fetch('/api/v1/smartflow/backtest/results', {
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          setResults(data);
        }
      } catch (error) {
        console.error('Failed to load previous backtest results:', error);
      } finally {
        setLoadingResults(false);
      }
    };

    const runBacktest = async () => {
      setRunning(true);
      try {
        const response = await fetch('/api/v1/smartflow/backtest/run', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(backtestConfig),
        });

        if (response.ok) {
          const data = await response.json();
          setResults(data);
          toast({
            title: 'Backtest complete',
            description: `Completed ${data.total_trades} trades over ${data.trading_days} days.`,
          });
        } else {
          const error = await response.json();
          toast({
            title: 'Backtest failed',
            description: error.detail || 'An error occurred',
            variant: 'destructive',
          });
        }
      } catch (error) {
        console.error('Backtest error:', error);
        toast({
          title: 'Backtest failed',
          description: 'Failed to run backtest',
          variant: 'destructive',
        });
      } finally {
        setRunning(false);
      }
    };

    const updateConfig = (field: string, value: any) => {
      setBacktestConfig((prev) => ({ ...prev, [field]: value }));
    };

    return (
      <div className="space-y-6">
        {/* Controls */}
        <Card className="border-2 border-indigo-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Backtest Configuration
            </CardTitle>
            <CardDescription>
              Run historical backtests with SmartFlow's full suite (Regime Detection, Ensemble Scoring, Risk Management)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="bt_ticker">Ticker</Label>
                <Input
                  id="bt_ticker"
                  value={backtestConfig.ticker}
                  onChange={(e) => updateConfig('ticker', e.target.value)}
                  placeholder="MES, SPY, QQQ"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bt_days">Days of History</Label>
                <Input
                  id="bt_days"
                  type="number"
                  value={backtestConfig.days}
                  onChange={(e) => updateConfig('days', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bt_engine">Engine</Label>
                <Select
                  value={backtestConfig.engine_type}
                  onValueChange={(value) => updateConfig('engine_type', value)}
                >
                  <SelectTrigger id="bt_engine">
                    <SelectValue placeholder="Select engine" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unified">Unified (Default)</SelectItem>
                    <SelectItem value="flow">Flow Engine</SelectItem>
                    <SelectItem value="ai">AI Engine</SelectItem>
                    <SelectItem value="deterministic">Deterministic Engine</SelectItem>
                    <SelectItem value="quick">Quick Mode</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Note: Currently all engines use unified strategy
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="bt_capital">Initial Capital ($)</Label>
                <Input
                  id="bt_capital"
                  type="number"
                  value={backtestConfig.initial_capital}
                  onChange={(e) => updateConfig('initial_capital', parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bt_position_size">Position Size (%)</Label>
                <Input
                  id="bt_position_size"
                  type="number"
                  step="0.1"
                  value={backtestConfig.position_size_pct}
                  onChange={(e) => updateConfig('position_size_pct', parseFloat(e.target.value))}
                />
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="bt_use_atr">Use ATR-Based Stops</Label>
                <Switch
                  id="bt_use_atr"
                  checked={backtestConfig.use_atr_stops}
                  onCheckedChange={(checked) => updateConfig('use_atr_stops', checked)}
                />
              </div>

              {backtestConfig.use_atr_stops && (
                <div className="grid grid-cols-2 gap-4 ml-4">
                  <div className="space-y-2">
                    <Label htmlFor="bt_atr_stop">ATR Stop Multiplier</Label>
                    <Input
                      id="bt_atr_stop"
                      type="number"
                      step="0.1"
                      value={backtestConfig.atr_stop_mult}
                      onChange={(e) => updateConfig('atr_stop_mult', parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="bt_atr_target">ATR Target Multiplier</Label>
                    <Input
                      id="bt_atr_target"
                      type="number"
                      step="0.1"
                      value={backtestConfig.atr_target_mult}
                      onChange={(e) => updateConfig('atr_target_mult', parseFloat(e.target.value))}
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between">
                <Label htmlFor="bt_use_pct">Use Percentage Stops</Label>
                <Switch
                  id="bt_use_pct"
                  checked={backtestConfig.use_pct_stops}
                  onCheckedChange={(checked) => updateConfig('use_pct_stops', checked)}
                />
              </div>

              {backtestConfig.use_pct_stops && (
                <div className="grid grid-cols-2 gap-4 ml-4">
                  <div className="space-y-2">
                    <Label htmlFor="bt_pct_stop">Stop Loss (%)</Label>
                    <Input
                      id="bt_pct_stop"
                      type="number"
                      step="0.1"
                      value={backtestConfig.pct_stop}
                      onChange={(e) => updateConfig('pct_stop', parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="bt_pct_target">Take Profit (%)</Label>
                    <Input
                      id="bt_pct_target"
                      type="number"
                      step="0.1"
                      value={backtestConfig.pct_target}
                      onChange={(e) => updateConfig('pct_target', parseFloat(e.target.value))}
                    />
                  </div>
                </div>
              )}
            </div>

            <Button onClick={runBacktest} disabled={running} className="w-full" size="lg">
              {running ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running Backtest...
                </>
              ) : (
                <>Run Backtest</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        {loadingResults ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
              Loading previous results...
            </CardContent>
          </Card>
        ) : results ? (
          <div className="space-y-4">
            {/* Performance Summary */}
            <Card className="border-2 border-green-500/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Performance Summary
                  <Badge variant="outline" className="text-xs">
                    {results.engine_type || 'unified'}
                  </Badge>
                </CardTitle>
                <CardDescription>
                  {results.start_date} to {results.end_date} ({results.trading_days} days)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Total Return</div>
                    <div className={cn("text-2xl font-bold", results.total_return_pct > 0 ? "text-green-500" : "text-red-500")}>
                      {results.total_return_pct > 0 ? '+' : ''}{results.total_return_pct.toFixed(2)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Sharpe Ratio</div>
                    <div className="text-2xl font-bold">{results.sharpe_ratio.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Win Rate</div>
                    <div className="text-2xl font-bold">{formatWinRate(results.win_rate)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Max Drawdown</div>
                    <div className="text-2xl font-bold text-red-500">-{results.max_drawdown_pct.toFixed(2)}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Total Trades</div>
                    <div className="text-xl font-bold">{results.total_trades}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Profit Factor</div>
                    <div className="text-xl font-bold">{results.profit_factor.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Net Profit</div>
                    <div className={cn("text-xl font-bold", results.net_profit > 0 ? "text-green-500" : "text-red-500")}>
                      ${results.net_profit.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Avg Holding</div>
                    <div className="text-xl font-bold">{results.avg_holding_time_hours.toFixed(1)}h</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Trade Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Trade Breakdown</CardTitle>
                <CardDescription>Last {results.trades?.length || 0} trades</CardDescription>
              </CardHeader>
              <CardContent>
                {results.trades && results.trades.length > 0 ? (
                  <div className="space-y-2">
                    {results.trades.map((trade: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between border-b pb-2 last:border-0">
                        <div className="flex items-center gap-3">
                          <Badge className={trade.direction === 'long' ? 'bg-green-500' : 'bg-red-500'}>
                            {trade.direction.toUpperCase()}
                          </Badge>
                          <div>
                            <div className="text-sm font-medium">{trade.ticker}</div>
                            <div className="text-xs text-muted-foreground">
                              {new Date(trade.entry_time).toLocaleString()}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-xs">{trade.regime}</Badge>
                          <Badge variant="outline" className="text-xs">{trade.exit_reason}</Badge>
                          <div className={cn("text-sm font-bold", trade.net_pnl > 0 ? "text-green-500" : "text-red-500")}>
                            {trade.net_pnl > 0 ? '+' : ''}${trade.net_pnl.toFixed(2)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-4">
                    No trade details available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No backtest results yet. Run a backtest to see performance metrics.
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  // Backtest Tab Content (with sub-tabs)
  const BacktestContent = () => (
    <Tabs defaultValue="single" className="w-full">
      <TabsList className="grid w-full grid-cols-3 mb-6">
        <TabsTrigger value="single">Single Run</TabsTrigger>
        <TabsTrigger value="compare">Compare Engines</TabsTrigger>
        <TabsTrigger value="saved">Saved Runs</TabsTrigger>
      </TabsList>

      <TabsContent value="single">
        <SingleRunContent />
      </TabsContent>

      <TabsContent value="compare">
        <CompareEnginesDashboard />
      </TabsContent>

      <TabsContent value="saved">
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p className="mb-2">Saved Runs</p>
            <p className="text-sm">Coming soon - save and replay comparison results</p>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );

  // Config Tab Content
  const ConfigContent = () => {
    const [formData, setFormData] = useState<SmartFlowConfig>(config);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
      setFormData(config);
    }, [config]);

    const handleSave = async () => {
      setSaving(true);
      try {
        const response = await fetch('/api/v1/smartflow/config', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(formData),
        });

        if (response.ok) {
          const updated = await response.json();
          setConfig(updated);
          toast({
            title: 'Configuration saved',
            description: 'SmartFlow configuration has been updated successfully.',
          });
        } else {
          toast({
            title: 'Save failed',
            description: 'Failed to save configuration. Please try again.',
            variant: 'destructive',
          });
        }
      } catch (error) {
        console.error('Failed to save config:', error);
        toast({
          title: 'Save failed',
          description: 'An error occurred while saving.',
          variant: 'destructive',
        });
      } finally {
        setSaving(false);
      }
    };

    const updateField = (field: string, value: any) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    };

    return (
      <div className="space-y-6">
        {/* Save Button Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Engine Configuration
            </h3>
            <p className="text-sm text-muted-foreground">
              Configure each trading engine's parameters and thresholds
            </p>
          </div>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>

        {/* Flow Engine Config */}
        <Card className="border-2 border-blue-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-blue-500" />
              Flow Engine
            </CardTitle>
            <CardDescription>Institutional options flow analysis settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enabled">Enable Flow Engine</Label>
              <Switch
                id="enabled"
                checked={formData.enabled}
                onCheckedChange={(checked) => updateField('enabled', checked)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="buy_threshold">Buy Threshold</Label>
                <Input
                  id="buy_threshold"
                  type="number"
                  value={formData.buy_threshold || 0}
                  onChange={(e) => updateField('buy_threshold', parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sell_threshold">Sell Threshold</Label>
                <Input
                  id="sell_threshold"
                  type="number"
                  value={formData.sell_threshold || 0}
                  onChange={(e) => updateField('sell_threshold', parseFloat(e.target.value))}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* AI Engine Config */}
        <Card className="border-2 border-purple-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              AI Engine
            </CardTitle>
            <CardDescription>AI-driven analysis settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enable_ai_only_mode">Enable AI Engine</Label>
              <Switch
                id="enable_ai_only_mode"
                checked={formData.enable_ai_only_mode || false}
                onCheckedChange={(checked) => updateField('enable_ai_only_mode', checked)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ai_only_scan_interval">Scan Interval (seconds)</Label>
                <Input
                  id="ai_only_scan_interval"
                  type="number"
                  value={formData.ai_only_scan_interval || 300}
                  onChange={(e) => updateField('ai_only_scan_interval', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ai_only_confidence_threshold">Confidence Threshold (%)</Label>
                <Input
                  id="ai_only_confidence_threshold"
                  type="number"
                  value={formData.ai_only_confidence_threshold || 70}
                  onChange={(e) => updateField('ai_only_confidence_threshold', parseFloat(e.target.value))}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Deterministic Engine Config */}
        <Card className="border-2 border-emerald-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Deterministic Engine
              <Badge variant="outline">NO AI</Badge>
            </CardTitle>
            <CardDescription>Multi-timeframe technical indicators settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enable_deterministic_mode">Enable Deterministic Engine</Label>
              <Switch
                id="enable_deterministic_mode"
                checked={formData.enable_deterministic_mode !== false}
                onCheckedChange={(checked) => updateField('enable_deterministic_mode', checked)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="deterministic_min_confidence">Min Confidence (%)</Label>
                <Input
                  id="deterministic_min_confidence"
                  type="number"
                  value={formData.deterministic_min_confidence || 75}
                  onChange={(e) => updateField('deterministic_min_confidence', parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="deterministic_min_aligned_tfs">Min Aligned Timeframes</Label>
                <Input
                  id="deterministic_min_aligned_tfs"
                  type="number"
                  value={formData.deterministic_min_aligned_tfs || 4}
                  onChange={(e) => updateField('deterministic_min_aligned_tfs', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="deterministic_min_rr">Min Risk:Reward Ratio</Label>
                <Input
                  id="deterministic_min_rr"
                  type="number"
                  step="0.1"
                  value={formData.deterministic_min_rr || 2.0}
                  onChange={(e) => updateField('deterministic_min_rr', parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="deterministic_rr_preset">R:R Preset</Label>
                <Input
                  id="deterministic_rr_preset"
                  type="text"
                  value={formData.deterministic_rr_preset || 'balanced'}
                  onChange={(e) => updateField('deterministic_rr_preset', e.target.value)}
                  placeholder="balanced, aggressive, conservative"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Mode Engine Config */}
        <Card className="border-2 border-amber-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Quick Mode Engine
            </CardTitle>
            <CardDescription>5-minute momentum scalping settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enable_quick_mode">Enable Quick Mode</Label>
              <Switch
                id="enable_quick_mode"
                checked={formData.enable_quick_mode !== false}
                onCheckedChange={(checked) => updateField('enable_quick_mode', checked)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="quick_scan_interval">Scan Interval (seconds)</Label>
                <Input
                  id="quick_scan_interval"
                  type="number"
                  value={formData.quick_scan_interval || 60}
                  onChange={(e) => updateField('quick_scan_interval', parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="quick_min_confidence">Min Confidence (%)</Label>
                <Input
                  id="quick_min_confidence"
                  type="number"
                  value={formData.quick_min_confidence || 60}
                  onChange={(e) => updateField('quick_min_confidence', parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="quick_min_rr">Min Risk:Reward Ratio</Label>
                <Input
                  id="quick_min_rr"
                  type="number"
                  step="0.1"
                  value={formData.quick_min_rr || 1.5}
                  onChange={(e) => updateField('quick_min_rr', parseFloat(e.target.value))}
                />
              </div>
              <div className="flex items-center justify-between pt-6">
                <Label htmlFor="quick_require_15m_confirmation">Require 15m Confirmation</Label>
                <Switch
                  id="quick_require_15m_confirmation"
                  checked={formData.quick_require_15m_confirmation !== false}
                  onCheckedChange={(checked) => updateField('quick_require_15m_confirmation', checked)}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Save Button Footer */}
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving} size="lg">
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : 'Save All Changes'}
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Zap className="h-8 w-8 text-yellow-500" />
            SmartFlow Platform
          </h1>
          <p className="text-muted-foreground mt-1">
            Multi-engine trading system with AI, flow analysis, and technical indicators
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-9 mb-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="engines">Engines</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="backtest">Backtest</TabsTrigger>
          <TabsTrigger value="forward-test">Forward Test</TabsTrigger>
          <TabsTrigger value="router">Router</TabsTrigger>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="webhooks">Webhooks</TabsTrigger>
          <TabsTrigger value="config">Config</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewContent />
        </TabsContent>

        <TabsContent value="engines">
          <EnginesContent />
        </TabsContent>

        <TabsContent value="analytics">
          <AnalyticsContent />
        </TabsContent>

        <TabsContent value="backtest">
          <BacktestContent />
        </TabsContent>

        <TabsContent value="forward-test">
          <ForwardTestContent />
        </TabsContent>

        <TabsContent value="router">
          <AdaptiveRouterDashboard />
        </TabsContent>

        <TabsContent value="strategies">
          <StrategiesOverview />
        </TabsContent>

        <TabsContent value="webhooks">
          <WebhooksDashboard />
        </TabsContent>

        <TabsContent value="config">
          <ConfigContent />
        </TabsContent>
      </Tabs>
    </div>
  );
}
