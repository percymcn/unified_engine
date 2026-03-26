'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Slider } from '@/components/ui/slider';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  Zap,
  BarChart3,
  Activity,
  Timer,
  RefreshCw,
  Target,
  AlertTriangle,
  Brain,
  Gauge,
  Trophy,
  Percent,
  DollarSign,
  ArrowUpDown,
  Sparkles,
  Settings2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TimeframeData {
  timeframe: string;
  close: number;
  ema9: number;
  ema21: number;
  rsi14: number;
  macd_histogram: number;
  atr14: number;
  volume_ratio: number;
  volume_delta: number;
  bias: string;
  bias_strength: number;
  ema_bullish: boolean;
  rsi_bullish: boolean;
  macd_bullish: boolean;
  volume_bullish: boolean;
}

interface LatencyRecord {
  timestamp: string;
  ticker: string;
  action: string;
  signal_age_ms: number;
  webhook_post_ms: number;
  total_latency_ms: number;
  under_target: boolean;
}

interface LatencyStats {
  count: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
  under_target_pct: number;
  recent: LatencyRecord[];
}

interface FlowCluster {
  sentiment: string;
  sentiment_score: number;
  total_premium: number;
  call_premium: number;
  put_premium: number;
  net_premium: number;
  sweep_count: number;
  block_count: number;
  total_trades: number;
  timestamp: string;
}

interface StrategyStats {
  signals_generated: number;
  trades_won: number;
  trades_lost: number;
  total_pnl: number;
  win_rate: number;
  avg_rr_achieved: number;
  last_signal_time: string | null;
}

interface RecentSignal {
  ticker: string;
  action: string;
  score: number;
  confidence: number;
  reason: string;
  timestamp: string;
}

interface DeterministicStatus {
  enabled: boolean;
  enable_deterministic_mode: boolean;
  enable_quick_mode: boolean;
  deterministic_min_confidence: number;
  deterministic_min_rr: number;
  deterministic_min_aligned_tfs: number;
  deterministic_rr_preset: string;
  quick_scan_interval: number;
  quick_min_confidence: number;
  quick_require_15m_confirmation: boolean;
  quick_min_rr: number;
  use_flow_confirmation: boolean;
  use_polygon_options_flow: boolean;
  latency_target_ms: number;
  latency_stats: LatencyStats;
  flow_clusters?: Record<string, FlowCluster>;
  mtf_analysis?: Record<string, TimeframeData>;
  strategy_stats: {
    deterministic: StrategyStats;
    quick_5m: StrategyStats;
  };
  recent_signals?: RecentSignal[];
}

export function DeterministicDashboard() {
  const [status, setStatus] = useState<DeterministicStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [rrPreset, setRRPreset] = useState('balanced');
  const [flowConfirmation, setFlowConfirmation] = useState(false);
  const [usePolygonFlow, setUsePolygonFlow] = useState(true);
  const [deterministicEnabled, setDeterministicEnabled] = useState(true);
  const [quickModeEnabled, setQuickModeEnabled] = useState(false);
  const [quick15mConfirm, setQuick15mConfirm] = useState(true);
  const [aiContext, setAiContext] = useState<string>('');
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 30000); // Poll every 30 seconds instead of 5
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      // Add cache buster to prevent stale data
      const response = await fetch(`/api/v1/smartflow/status?_t=${Date.now()}`, {
        credentials: 'include',
        cache: 'no-store',
      });
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        if (data.deterministic_rr_preset) {
          setRRPreset(data.deterministic_rr_preset);
        }
        if (data.use_flow_confirmation !== undefined) {
          setFlowConfirmation(data.use_flow_confirmation);
        }
        if (data.use_polygon_options_flow !== undefined) {
          setUsePolygonFlow(data.use_polygon_options_flow);
        }
        if (data.enable_deterministic_mode !== undefined) {
          setDeterministicEnabled(data.enable_deterministic_mode);
        }
        if (data.enable_quick_mode !== undefined) {
          setQuickModeEnabled(data.enable_quick_mode);
        }
        if (data.quick_require_15m_confirmation !== undefined) {
          setQuick15mConfirm(data.quick_require_15m_confirmation);
        }
      } else {
        console.error('loadStatus failed:', response.status);
      }
    } catch (error) {
      console.error('Failed to load status:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async (config: Record<string, any>) => {
    setSaving(true);
    try {
      const response = await fetch('/api/v1/smartflow/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(config),
      });
      if (response.ok) {
        const result = await response.json();
        console.log('PATCH result:', result);
        // Update local state from server response
        if (result.current_state) {
          if (result.current_state.enable_quick_mode !== undefined) {
            setQuickModeEnabled(result.current_state.enable_quick_mode);
          }
          if (result.current_state.enable_deterministic_mode !== undefined) {
            setDeterministicEnabled(result.current_state.enable_deterministic_mode);
          }
        }
        // Also refresh full status
        loadStatus();
      } else {
        console.error('PATCH failed:', response.status, await response.text());
        // Revert on failure by reloading status
        loadStatus();
      }
    } catch (error) {
      console.error('Failed to save config:', error);
      loadStatus(); // Revert on error
    } finally {
      setSaving(false);
    }
  };

  const toggleDeterministic = () => {
    const newValue = !deterministicEnabled;
    setDeterministicEnabled(newValue);
    saveConfig({ enable_deterministic_mode: newValue });
  };

  const toggleQuickMode = () => {
    const newValue = !quickModeEnabled;
    setQuickModeEnabled(newValue);
    saveConfig({ enable_quick_mode: newValue });
  };

  const fetchAiContext = async () => {
    setAiLoading(true);
    try {
      const response = await fetch('/api/v1/smartflow/ai-context', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setAiContext(data.analysis || 'No AI analysis available');
      }
    } catch (error) {
      setAiContext('Failed to fetch AI analysis');
    } finally {
      setAiLoading(false);
    }
  };

  const getBiasBadge = (bias: string, strength: number) => {
    if (bias === 'bullish') {
      return <Badge className="bg-green-500">BULL {strength.toFixed(0)}%</Badge>;
    } else if (bias === 'bearish') {
      return <Badge className="bg-red-500">BEAR {strength.toFixed(0)}%</Badge>;
    }
    return <Badge variant="outline">NEUTRAL</Badge>;
  };

  const getSignalIcon = (isActive: boolean) => {
    return isActive ? (
      <div className="h-3 w-3 rounded-full bg-green-500" />
    ) : (
      <div className="h-3 w-3 rounded-full bg-gray-400" />
    );
  };

  const getWinRateColor = (winRate: number) => {
    if (winRate >= 60) return 'text-green-500';
    if (winRate >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const detStats = status?.strategy_stats?.deterministic || {
    signals_generated: 0, trades_won: 0, trades_lost: 0, total_pnl: 0, win_rate: 0
  };
  const quickStats = status?.strategy_stats?.quick_5m || {
    signals_generated: 0, trades_won: 0, trades_lost: 0, total_pnl: 0, win_rate: 0
  };

  return (
    <div className="space-y-6">
      {/* Mode Controls - Main Toggles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Deterministic Mode Card */}
        <Card className={cn(
          "border-2 transition-colors",
          deterministicEnabled ? "border-blue-500 bg-blue-500/5" : "border-muted"
        )}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                Deterministic Mode
              </CardTitle>
              <Switch
                checked={deterministicEnabled}
                onCheckedChange={toggleDeterministic}
                disabled={saving}
              />
            </div>
            <CardDescription>
              Multi-timeframe alignment (4-5 TFs) | R:R 2:1+ | High confidence
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2 bg-muted/50 rounded">
                <div className="text-xl font-bold">{detStats.signals_generated}</div>
                <div className="text-xs text-muted-foreground">Signals</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className={cn("text-xl font-bold", getWinRateColor(detStats.win_rate))}>
                  {detStats.win_rate.toFixed(0)}%
                </div>
                <div className="text-xs text-muted-foreground">Win Rate</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className={cn("text-xl font-bold", detStats.total_pnl >= 0 ? "text-green-500" : "text-red-500")}>
                  ${detStats.total_pnl.toFixed(0)}
                </div>
                <div className="text-xs text-muted-foreground">P&L</div>
              </div>
            </div>
            <Select value={rrPreset} onValueChange={(v) => {
              setRRPreset(v);
              saveConfig({ deterministic_rr_preset: v });
            }}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="R:R Preset" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="aggressive">Aggressive (1.5:1)</SelectItem>
                <SelectItem value="balanced">Balanced (2:1)</SelectItem>
                <SelectItem value="conservative">Conservative (3:1)</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {/* Quick Mode Card */}
        <Card className={cn(
          "border-2 transition-colors",
          quickModeEnabled ? "border-yellow-500 bg-yellow-500/5" : "border-muted"
        )}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Zap className="h-5 w-5 text-yellow-500" />
                Quick Mode (5m)
              </CardTitle>
              <Switch
                checked={quickModeEnabled}
                onCheckedChange={toggleQuickMode}
                disabled={saving}
              />
            </div>
            <CardDescription>
              5-minute momentum | R:R 1.5:1 | Fast scalping signals
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2 bg-muted/50 rounded">
                <div className="text-xl font-bold">{quickStats.signals_generated}</div>
                <div className="text-xs text-muted-foreground">Signals</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className={cn("text-xl font-bold", getWinRateColor(quickStats.win_rate))}>
                  {quickStats.win_rate.toFixed(0)}%
                </div>
                <div className="text-xs text-muted-foreground">Win Rate</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className={cn("text-xl font-bold", quickStats.total_pnl >= 0 ? "text-green-500" : "text-red-500")}>
                  ${quickStats.total_pnl.toFixed(0)}
                </div>
                <div className="text-xs text-muted-foreground">P&L</div>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-sm">15m Confirmation</Label>
              <Switch
                checked={quick15mConfirm}
                onCheckedChange={(v) => {
                  setQuick15mConfirm(v);
                  saveConfig({ quick_require_15m_confirmation: v });
                }}
                disabled={saving}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Strategy Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-yellow-500" />
            Strategy Comparison (A/B Testing)
          </CardTitle>
          <CardDescription>
            Compare performance between Deterministic and Quick Mode strategies
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Strategy</TableHead>
                <TableHead>Signals</TableHead>
                <TableHead>Won</TableHead>
                <TableHead>Lost</TableHead>
                <TableHead>Win Rate</TableHead>
                <TableHead>Avg R:R</TableHead>
                <TableHead>Total P&L</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="font-bold">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-blue-500" />
                    Deterministic
                  </div>
                </TableCell>
                <TableCell>{detStats.signals_generated}</TableCell>
                <TableCell className="text-green-500">{detStats.trades_won}</TableCell>
                <TableCell className="text-red-500">{detStats.trades_lost}</TableCell>
                <TableCell className={getWinRateColor(detStats.win_rate)}>
                  <div className="flex items-center gap-2">
                    <Progress value={detStats.win_rate} className="w-16 h-2" />
                    {detStats.win_rate.toFixed(1)}%
                  </div>
                </TableCell>
                <TableCell>{detStats.avg_rr_achieved?.toFixed(2) || '-'}:1</TableCell>
                <TableCell className={detStats.total_pnl >= 0 ? "text-green-500" : "text-red-500"}>
                  ${detStats.total_pnl.toFixed(2)}
                </TableCell>
                <TableCell>
                  <Badge className={deterministicEnabled ? "bg-green-500" : "bg-gray-500"}>
                    {deterministicEnabled ? 'ACTIVE' : 'OFF'}
                  </Badge>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-bold">
                  <div className="flex items-center gap-2">
                    <Zap className="h-4 w-4 text-yellow-500" />
                    Quick 5m
                  </div>
                </TableCell>
                <TableCell>{quickStats.signals_generated}</TableCell>
                <TableCell className="text-green-500">{quickStats.trades_won}</TableCell>
                <TableCell className="text-red-500">{quickStats.trades_lost}</TableCell>
                <TableCell className={getWinRateColor(quickStats.win_rate)}>
                  <div className="flex items-center gap-2">
                    <Progress value={quickStats.win_rate} className="w-16 h-2" />
                    {quickStats.win_rate.toFixed(1)}%
                  </div>
                </TableCell>
                <TableCell>{quickStats.avg_rr_achieved?.toFixed(2) || '-'}:1</TableCell>
                <TableCell className={quickStats.total_pnl >= 0 ? "text-green-500" : "text-red-500"}>
                  ${quickStats.total_pnl.toFixed(2)}
                </TableCell>
                <TableCell>
                  <Badge className={quickModeEnabled ? "bg-yellow-500" : "bg-gray-500"}>
                    {quickModeEnabled ? 'ACTIVE' : 'OFF'}
                  </Badge>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* AI Context Panel */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-purple-500" />
              AI Market Context
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchAiContext}
              disabled={aiLoading}
            >
              {aiLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Sparkles className="h-4 w-4 mr-2" />
              )}
              Refresh Analysis
            </Button>
          </div>
          <CardDescription>
            AI-powered market analysis and context (does not affect trading decisions)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {aiContext ? (
            <div className="p-4 bg-muted/30 rounded-lg">
              <pre className="whitespace-pre-wrap text-sm font-mono">{aiContext}</pre>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Click "Refresh Analysis" to get AI market context</p>
              <p className="text-xs mt-2">AI provides context only - trading uses deterministic indicators</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs defaultValue="signals" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="signals" className="flex items-center gap-1">
            <Activity className="h-4 w-4" />
            Live Signals
          </TabsTrigger>
          <TabsTrigger value="mtf" className="flex items-center gap-1">
            <BarChart3 className="h-4 w-4" />
            Multi-TF
          </TabsTrigger>
          <TabsTrigger value="volume" className="flex items-center gap-1">
            <Gauge className="h-4 w-4" />
            Volume
          </TabsTrigger>
          <TabsTrigger value="latency" className="flex items-center gap-1">
            <Timer className="h-4 w-4" />
            Latency
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-1">
            <Settings2 className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Live Signals Tab */}
        <TabsContent value="signals" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Recent Trading Signals
              </CardTitle>
              <CardDescription>
                Live feed of all signals from both strategies
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Strategy</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(status?.recent_signals || []).slice(0, 15).map((signal, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="text-xs font-mono">{signal.timestamp}</TableCell>
                      <TableCell className="font-bold">{signal.ticker}</TableCell>
                      <TableCell>
                        <Badge className={signal.action === 'buy' ? 'bg-green-500' : 'bg-red-500'}>
                          {signal.action.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {signal.reason?.includes('QUICK') ? (
                          <Badge variant="outline" className="border-yellow-500 text-yellow-500">
                            <Zap className="h-3 w-3 mr-1" />
                            Quick
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="border-blue-500 text-blue-500">
                            <BarChart3 className="h-3 w-3 mr-1" />
                            MTF
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={signal.confidence} className="w-16 h-2" />
                          <span className="text-xs">{signal.confidence?.toFixed(0)}%</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs max-w-xs truncate">{signal.reason}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {(!status?.recent_signals || status.recent_signals.length === 0) && (
                <div className="text-center py-8 text-muted-foreground">
                  No recent signals. Waiting for market conditions...
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Multi-Timeframe Analysis Tab */}
        <TabsContent value="mtf" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Multi-Timeframe Indicator Analysis
              </CardTitle>
              <CardDescription>
                Real-time EMA, RSI, MACD, ATR across 5 timeframes (deterministic mode)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>TF</TableHead>
                    <TableHead>Close</TableHead>
                    <TableHead>EMA9 &gt; EMA21</TableHead>
                    <TableHead>RSI</TableHead>
                    <TableHead>MACD</TableHead>
                    <TableHead>Vol Ratio</TableHead>
                    <TableHead>ATR</TableHead>
                    <TableHead>Bias</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {['5m', '15m', '30m', '1h', '4h'].map((tf) => {
                    const data = status?.mtf_analysis?.[tf];

                    if (!data) {
                      return (
                        <TableRow key={tf}>
                          <TableCell className="font-bold">{tf}</TableCell>
                          <TableCell colSpan={7} className="text-muted-foreground">
                            Waiting for data...
                          </TableCell>
                        </TableRow>
                      );
                    }

                    return (
                      <TableRow key={tf}>
                        <TableCell className="font-bold">{tf}</TableCell>
                        <TableCell>${data.close.toFixed(2)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getSignalIcon(data.ema_bullish)}
                            <span className="text-xs">
                              {data.ema9.toFixed(1)} / {data.ema21.toFixed(1)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getSignalIcon(data.rsi_bullish)}
                            <span className={cn(
                              "font-mono",
                              data.rsi14 > 70 ? "text-red-500" :
                              data.rsi14 < 30 ? "text-green-500" :
                              data.rsi14 > 50 ? "text-green-400" : "text-red-400"
                            )}>
                              {data.rsi14.toFixed(1)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getSignalIcon(data.macd_bullish)}
                            <span className={cn(
                              "font-mono text-xs",
                              data.macd_histogram > 0 ? "text-green-500" : "text-red-500"
                            )}>
                              {data.macd_histogram > 0 ? '+' : ''}{data.macd_histogram.toFixed(3)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={cn(
                            data.volume_ratio > 1.5 ? "bg-green-500" :
                            data.volume_ratio > 1.2 ? "bg-green-400" :
                            data.volume_ratio < 0.8 ? "bg-yellow-500" :
                            "bg-gray-500"
                          )}>
                            {data.volume_ratio.toFixed(1)}x
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          ${data.atr14.toFixed(2)}
                        </TableCell>
                        <TableCell>{getBiasBadge(data.bias, data.bias_strength)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Legend */}
              <div className="flex gap-4 mt-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <div className="h-2 w-2 rounded-full bg-green-500" />
                  <span>Bullish signal</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="h-2 w-2 rounded-full bg-gray-400" />
                  <span>Bearish signal</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>Min {status?.deterministic_min_aligned_tfs || 4}/5 TFs aligned required</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Volume Analysis Tab */}
        <TabsContent value="volume" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Gauge className="h-5 w-5" />
                Volume Analysis
              </CardTitle>
              <CardDescription>
                Relative volume and buy/sell pressure across timeframes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                {['5m', '15m', '30m', '1h', '4h'].map((tf) => {
                  const data = status?.mtf_analysis?.[tf];
                  const volRatio = data?.volume_ratio || 1.0;
                  const volDelta = data?.volume_delta || 0;

                  return (
                    <Card key={tf} className="bg-muted/50">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg">{tf}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div>
                          <div className="flex justify-between text-sm">
                            <span>Relative Vol</span>
                            <Badge className={cn(
                              volRatio > 1.5 ? "bg-green-500" :
                              volRatio > 1.2 ? "bg-green-400" :
                              volRatio < 0.8 ? "bg-yellow-500" :
                              "bg-gray-500"
                            )}>
                              {volRatio.toFixed(2)}x
                            </Badge>
                          </div>
                          <Progress
                            value={Math.min(volRatio * 50, 100)}
                            className="h-2 mt-1"
                          />
                        </div>
                        <div>
                          <div className="flex justify-between text-sm">
                            <span>Buy/Sell Pressure</span>
                            <span className={cn(
                              volDelta > 0 ? "text-green-500" : "text-red-500"
                            )}>
                              {volDelta > 0 ? '+' : ''}{(volDelta / 1000000).toFixed(2)}M
                            </span>
                          </div>
                          <div className="flex gap-1 mt-1">
                            <div
                              className="h-2 bg-green-500 rounded-l"
                              style={{ width: volDelta > 0 ? '60%' : '40%' }}
                            />
                            <div
                              className="h-2 bg-red-500 rounded-r"
                              style={{ width: volDelta > 0 ? '40%' : '60%' }}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Latency Tab */}
        <TabsContent value="latency" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Timer className="h-5 w-5" />
                Signal Latency Tracking
              </CardTitle>
              <CardDescription>
                End-to-end latency from signal generation to webhook post (target: &lt;2s)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Stats Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold">
                    {status?.latency_stats?.avg_ms?.toFixed(0) || 0}ms
                  </div>
                  <div className="text-xs text-muted-foreground">Average</div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold text-green-500">
                    {status?.latency_stats?.min_ms?.toFixed(0) || 0}ms
                  </div>
                  <div className="text-xs text-muted-foreground">Minimum</div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold text-red-500">
                    {status?.latency_stats?.max_ms?.toFixed(0) || 0}ms
                  </div>
                  <div className="text-xs text-muted-foreground">Maximum</div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold">
                    {status?.latency_stats?.under_target_pct?.toFixed(0) || 0}%
                  </div>
                  <div className="text-xs text-muted-foreground">Under 2s</div>
                </div>
              </div>

              {/* Recent Latency Table */}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Signal Age</TableHead>
                    <TableHead>Webhook Post</TableHead>
                    <TableHead>Total</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(status?.latency_stats?.recent || []).slice(-10).reverse().map((record, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="text-xs">{record.timestamp}</TableCell>
                      <TableCell className="font-bold">{record.ticker}</TableCell>
                      <TableCell>
                        <Badge className={record.action === 'buy' ? 'bg-green-500' : 'bg-red-500'}>
                          {record.action.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {record.signal_age_ms.toFixed(0)}ms
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {record.webhook_post_ms.toFixed(0)}ms
                      </TableCell>
                      <TableCell className={cn(
                        "font-mono font-bold",
                        record.under_target ? "text-green-500" : "text-red-500"
                      )}>
                        {record.total_latency_ms.toFixed(0)}ms
                      </TableCell>
                      <TableCell>
                        {record.under_target ? (
                          <Badge className="bg-green-500">OK</Badge>
                        ) : (
                          <Badge className="bg-yellow-500">SLOW</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {(!status?.latency_stats?.recent || status.latency_stats.recent.length === 0) && (
                <div className="text-center py-8 text-muted-foreground">
                  No latency data yet. Signals will appear here after generation.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Deterministic Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-blue-500" />
                  Deterministic Mode Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Minimum Confidence: {status?.deterministic_min_confidence || 75}%</Label>
                  <Slider
                    value={[status?.deterministic_min_confidence || 75]}
                    min={50}
                    max={95}
                    step={5}
                    onValueCommit={(v) => saveConfig({ deterministic_min_confidence: v[0] })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Min Aligned Timeframes: {status?.deterministic_min_aligned_tfs || 4}/5</Label>
                  <Slider
                    value={[status?.deterministic_min_aligned_tfs || 4]}
                    min={3}
                    max={5}
                    step={1}
                    onValueCommit={(v) => saveConfig({ deterministic_min_aligned_tfs: v[0] })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Flow Confirmation</Label>
                  <Switch
                    checked={flowConfirmation}
                    onCheckedChange={(v) => {
                      setFlowConfirmation(v);
                      saveConfig({ use_flow_confirmation: v });
                    }}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Use Polygon Flow</Label>
                  <Switch
                    checked={usePolygonFlow}
                    onCheckedChange={(v) => {
                      setUsePolygonFlow(v);
                      saveConfig({ use_polygon_options_flow: v });
                    }}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Quick Mode Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-yellow-500" />
                  Quick Mode Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Minimum Confidence: {status?.quick_min_confidence || 60}%</Label>
                  <Slider
                    value={[status?.quick_min_confidence || 60]}
                    min={40}
                    max={80}
                    step={5}
                    onValueCommit={(v) => saveConfig({ quick_min_confidence: v[0] })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Scan Interval: {status?.quick_scan_interval || 60}s</Label>
                  <Slider
                    value={[status?.quick_scan_interval || 60]}
                    min={30}
                    max={300}
                    step={30}
                    onValueCommit={(v) => saveConfig({ quick_scan_interval: v[0] })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Minimum R:R: {status?.quick_min_rr || 1.5}:1</Label>
                  <Slider
                    value={[(status?.quick_min_rr || 1.5) * 10]}
                    min={10}
                    max={30}
                    step={5}
                    onValueCommit={(v) => saveConfig({ quick_min_rr: v[0] / 10 })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label>15m Trend Confirmation</Label>
                  <Switch
                    checked={quick15mConfirm}
                    onCheckedChange={(v) => {
                      setQuick15mConfirm(v);
                      saveConfig({ quick_require_15m_confirmation: v });
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Instruments */}
          <Card>
            <CardHeader>
              <CardTitle>Tracked Instruments</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {(status?.deterministic_instruments || ['MES', 'NQ', 'RTY', 'GC', 'MYM', 'BTCUSD', 'ETHUSD']).map((inst) => (
                  <Badge key={inst} variant="outline" className="text-sm py-1 px-3">
                    {inst}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
