'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
  RefreshCw,
  Loader2,
  Eye,
  Clock,
  Target,
  AlertTriangle,
  BarChart3,
  Brain,
  Zap,
  ChevronRight,
  DollarSign,
  Percent,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface TradeIndicators {
  adx: number | null;
  hurst: number | null;
  atr: number | null;
  atr_pct: number | null;
  rsi: number | null;
  price_change_24h: number | null;
  volume_ratio: number | null;
  compression_flag: boolean;
  breakout_flag: boolean;
}

interface TradeScoring {
  probability: number | null;
  signal_strength: number | null;
  confidence_score: number | null;
}

interface TradeStrategy {
  mode: string | null;
  stop_pct_used: number | null;
  target_pct_used: number | null;
  size_multiplier: number | null;
}

interface TradeThresholds {
  min_prob: number | null;
  min_strength: number | null;
  passed: boolean;
}

interface ForwardTestTrade {
  id: number;
  trade_id: string;
  session_id: string;
  signal_id: string | null;
  correlation_id: string | null;
  symbol: string;
  side: string;
  direction: string;
  entry_time: string;
  entry_price: number;
  exit_time: string | null;
  exit_price: number | null;
  exit_reason: string | null;
  stop_loss: number | null;
  take_profit: number | null;
  trailing_stop: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  status: string;
  size: number;
  is_pyramid: boolean;
  pyramid_level: number | null;
  parent_trade_id: string | null;
  regime: string | null;
  regime_confidence: number | null;
  indicators: TradeIndicators;
  scoring: TradeScoring;
  strategy: TradeStrategy;
  thresholds: TradeThresholds;
  engine_type?: string | null;  // Phase 0.5: Engine source tracking
  raw_snapshot: any;
  created_at: string;
  updated_at: string | null;
  is_forward_test: boolean;
  is_legacy?: boolean;
}

interface TradeSummary {
  total_trades: number;
  closed_trades: number;
  open_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

interface RegimeStats {
  [regime: string]: {
    trades: number;
    wins: number;
    pnl: number;
  };
}

interface ForwardTestData {
  trades: ForwardTestTrade[];
  summary: TradeSummary;
  by_regime: RegimeStats;
  sessions: string[];
  is_legacy?: boolean;
}

export function ForwardTestDashboard() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<ForwardTestData | null>(null);
  const [selectedTrade, setSelectedTrade] = useState<ForwardTestTrade | null>(null);
  const [filterSymbol, setFilterSymbol] = useState<string>('all');
  const [filterSession, setFilterSession] = useState<string>('all');
  const [showOpenOnly, setShowOpenOnly] = useState(false);

  const loadTrades = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '100' });
      if (filterSymbol !== 'all') params.append('ticker', filterSymbol);
      if (filterSession !== 'all') params.append('session_id', filterSession);
      if (!showOpenOnly) params.append('include_open', 'true');

      const response = await fetch(`/api/v1/smartflow/forward-test/trades?${params}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const result = await response.json();
        setData(result);
      }
    } catch (error) {
      console.error('Failed to load forward test trades:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filterSymbol, filterSession, showOpenOnly]);

  useEffect(() => {
    loadTrades();
    const interval = setInterval(loadTrades, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [loadTrades]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadTrades();
  };

  const formatPrice = (price: number | null) => {
    if (price === null) return '-';
    return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatPnL = (pnl: number | null) => {
    if (pnl === null) return '-';
    const formatted = pnl.toFixed(2);
    return pnl >= 0 ? `+$${formatted}` : `-$${Math.abs(pnl).toFixed(2)}`;
  };

  const formatPercent = (pct: number | null) => {
    if (pct === null) return '-';
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
  };

  const getRegimeBadge = (regime: string | null) => {
    if (!regime) return <Badge variant="outline">Unknown</Badge>;

    const regimeColors: Record<string, string> = {
      trending_up: 'bg-green-500',
      trending_down: 'bg-red-500',
      trending: 'bg-blue-500',
      ranging: 'bg-yellow-500',
      volatile: 'bg-orange-500',
      breakout: 'bg-purple-500',
    };

    return (
      <Badge className={cn(regimeColors[regime] || 'bg-gray-500')}>
        {regime.replace('_', ' ').toUpperCase()}
      </Badge>
    );
  };

  const getStrategyBadge = (mode: string | null) => {
    if (!mode) return null;

    const strategyColors: Record<string, string> = {
      TRENDING: 'bg-blue-600',
      RANGING: 'bg-yellow-600',
      VOLATILE: 'bg-orange-600',
      BREAKOUT: 'bg-purple-600',
      DEFAULT: 'bg-gray-600',
    };

    return (
      <Badge className={cn(strategyColors[mode] || 'bg-gray-500', 'text-xs')}>
        {mode}
      </Badge>
    );
  };

  const getEngineBadge = (engineType: string | null | undefined) => {
    if (!engineType) return <Badge variant="outline" className="text-xs">Unknown</Badge>;

    const engineColors: Record<string, string> = {
      'flow': 'bg-blue-500',
      'ai_enhancement': 'bg-indigo-500',
      'ai_only': 'bg-purple-500',
      'deterministic': 'bg-emerald-500',
      'quick': 'bg-amber-500',
    };

    const engineLabels: Record<string, string> = {
      'flow': 'Flow',
      'ai_enhancement': 'AI+',
      'ai_only': 'AI-Only',
      'deterministic': 'Determ',
      'quick': 'Quick',
    };

    return (
      <Badge className={cn(engineColors[engineType] || 'bg-gray-500', 'text-xs')}>
        {engineLabels[engineType] || engineType}
      </Badge>
    );
  };

  const getDirectionIcon = (direction: string) => {
    return direction === 'long' ? (
      <TrendingUp className="h-4 w-4 text-green-500" />
    ) : (
      <TrendingDown className="h-4 w-4 text-red-500" />
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const uniqueSymbols = [...new Set(data?.trades.map(t => t.symbol) || [])];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{data?.summary.total_trades || 0}</div>
            <p className="text-xs text-muted-foreground">Total Trades</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-500">{data?.summary.open_trades || 0}</div>
            <p className="text-xs text-muted-foreground">Open Positions</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{data?.summary.win_rate?.toFixed(1) || 0}%</div>
            <p className="text-xs text-muted-foreground">Win Rate</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className={cn(
              "text-2xl font-bold",
              (data?.summary.total_pnl || 0) >= 0 ? "text-green-500" : "text-red-500"
            )}>
              {formatPnL(data?.summary.total_pnl || 0)}
            </div>
            <p className="text-xs text-muted-foreground">Total P&L</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-500">{data?.summary.wins || 0}</div>
            <p className="text-xs text-muted-foreground">Wins</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-red-500">{data?.summary.losses || 0}</div>
            <p className="text-xs text-muted-foreground">Losses</p>
          </CardContent>
        </Card>
      </div>

      {/* Regime Performance */}
      {data?.by_regime && Object.keys(data.by_regime).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Performance by Regime
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(data.by_regime).map(([regime, stats]) => {
                const winRate = stats.trades > 0 ? (stats.wins / stats.trades * 100) : 0;
                return (
                  <div key={regime} className="space-y-1">
                    {getRegimeBadge(regime)}
                    <div className="text-sm">
                      <span className="font-medium">{stats.trades}</span> trades,{' '}
                      <span className={cn(winRate >= 50 ? "text-green-500" : "text-red-500")}>
                        {winRate.toFixed(0)}% WR
                      </span>
                    </div>
                    <div className={cn(
                      "text-xs",
                      stats.pnl >= 0 ? "text-green-500" : "text-red-500"
                    )}>
                      {formatPnL(stats.pnl)}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Label htmlFor="symbol-filter">Symbol:</Label>
          <Select value={filterSymbol} onValueChange={setFilterSymbol}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              {uniqueSymbols.map(s => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Label htmlFor="session-filter">Session:</Label>
          <Select value={filterSession} onValueChange={setFilterSession}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sessions</SelectItem>
              {(data?.sessions || []).map(s => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
          Refresh
        </Button>

        {data?.is_legacy && (
          <Badge variant="outline" className="text-yellow-500 border-yellow-500">
            Legacy Data
          </Badge>
        )}
      </div>

      {/* Trades Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Forward Test Trades
          </CardTitle>
          <CardDescription>
            Click on any trade to see the full decision trace
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data?.trades && data.trades.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Direction</TableHead>
                  <TableHead>Entry</TableHead>
                  <TableHead>Exit</TableHead>
                  <TableHead>Engine</TableHead>
                  <TableHead>Regime</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>P&L</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.trades.map((trade) => (
                  <TableRow
                    key={trade.trade_id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => setSelectedTrade(trade)}
                  >
                    <TableCell className="text-xs text-muted-foreground">
                      {trade.entry_time ? new Date(trade.entry_time).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell className="font-semibold">{trade.symbol}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {getDirectionIcon(trade.direction)}
                        <span className={cn(
                          "uppercase text-xs font-medium",
                          trade.direction === 'long' ? "text-green-500" : "text-red-500"
                        )}>
                          {trade.direction}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>{formatPrice(trade.entry_price)}</TableCell>
                    <TableCell>{formatPrice(trade.exit_price)}</TableCell>
                    <TableCell>{getEngineBadge(trade.engine_type)}</TableCell>
                    <TableCell>{getRegimeBadge(trade.regime)}</TableCell>
                    <TableCell>{getStrategyBadge(trade.strategy?.mode)}</TableCell>
                    <TableCell className={cn(
                      "font-medium",
                      trade.pnl === null ? "" : trade.pnl >= 0 ? "text-green-500" : "text-red-500"
                    )}>
                      {formatPnL(trade.pnl)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={trade.status === 'open' ? 'default' : 'outline'}>
                        {trade.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No forward test trades found. Start the forward test daemon to generate trades.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Trade Detail Modal */}
      <Dialog open={!!selectedTrade} onOpenChange={() => setSelectedTrade(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Trade Decision Trace
            </DialogTitle>
            <DialogDescription>
              Full audit trail explaining why this signal fired
            </DialogDescription>
          </DialogHeader>

          {selectedTrade && (
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="indicators">Indicators</TabsTrigger>
                <TabsTrigger value="strategy">Strategy</TabsTrigger>
                <TabsTrigger value="raw">Raw Data</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                {/* Trade Header */}
                <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                  <div>
                    <div className="text-2xl font-bold flex items-center gap-2">
                      {selectedTrade.symbol}
                      {getDirectionIcon(selectedTrade.direction)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {selectedTrade.trade_id}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={cn(
                      "text-2xl font-bold",
                      selectedTrade.pnl === null ? "" :
                        selectedTrade.pnl >= 0 ? "text-green-500" : "text-red-500"
                    )}>
                      {formatPnL(selectedTrade.pnl)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatPercent(selectedTrade.pnl_pct)}
                    </div>
                  </div>
                </div>

                {/* Key Info Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" /> Entry Time
                    </div>
                    <div className="font-medium text-sm">
                      {selectedTrade.entry_time ? new Date(selectedTrade.entry_time).toLocaleString() : '-'}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <DollarSign className="h-3 w-3" /> Entry Price
                    </div>
                    <div className="font-medium text-sm">{formatPrice(selectedTrade.entry_price)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Target className="h-3 w-3" /> Stop Loss
                    </div>
                    <div className="font-medium text-sm text-red-500">
                      {formatPrice(selectedTrade.stop_loss)}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Target className="h-3 w-3" /> Take Profit
                    </div>
                    <div className="font-medium text-sm text-green-500">
                      {formatPrice(selectedTrade.take_profit)}
                    </div>
                  </div>
                </div>

                {/* Regime & Strategy */}
                <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Regime Detected</div>
                    {getRegimeBadge(selectedTrade.regime)}
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Strategy Applied</div>
                    {getStrategyBadge(selectedTrade.strategy?.mode)}
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Position Size</div>
                    <Badge variant="outline">
                      {((selectedTrade.strategy?.size_multiplier || 1) * 100).toFixed(0)}%
                    </Badge>
                  </div>
                </div>

                {/* Scoring */}
                <div className="grid grid-cols-3 gap-4">
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                        <Percent className="h-3 w-3" /> Probability
                      </div>
                      <div className="text-xl font-bold">
                        {selectedTrade.scoring?.probability
                          ? `${(selectedTrade.scoring.probability * 100).toFixed(1)}%`
                          : '-'}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                        <Zap className="h-3 w-3" /> Signal Strength
                      </div>
                      <div className="text-xl font-bold">
                        {selectedTrade.scoring?.signal_strength?.toFixed(1) || '-'}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                        <Brain className="h-3 w-3" /> Confidence
                      </div>
                      <div className="text-xl font-bold">
                        {selectedTrade.scoring?.confidence_score?.toFixed(1) || '-'}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Exit Info (if closed) */}
                {selectedTrade.status === 'closed' && (
                  <div className="p-4 bg-muted/50 rounded-lg space-y-2">
                    <div className="font-medium flex items-center gap-2">
                      <Info className="h-4 w-4" />
                      Exit Details
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Exit Time:</span>{' '}
                        {selectedTrade.exit_time ? new Date(selectedTrade.exit_time).toLocaleString() : '-'}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Exit Price:</span>{' '}
                        {formatPrice(selectedTrade.exit_price)}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Reason:</span>{' '}
                        <Badge variant="outline">{selectedTrade.exit_reason || 'N/A'}</Badge>
                      </div>
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="indicators" className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground">ADX (Trend Strength)</div>
                      <div className="text-xl font-bold">
                        {selectedTrade.indicators?.adx?.toFixed(1) || '-'}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {selectedTrade.indicators?.adx
                          ? selectedTrade.indicators.adx > 25 ? 'Strong trend' : 'Weak/no trend'
                          : ''}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground">Hurst Exponent</div>
                      <div className="text-xl font-bold">
                        {selectedTrade.indicators?.hurst?.toFixed(2) || '-'}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {selectedTrade.indicators?.hurst
                          ? selectedTrade.indicators.hurst > 0.5 ? 'Trending' : 'Mean-reverting'
                          : ''}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground">ATR %</div>
                      <div className="text-xl font-bold">
                        {selectedTrade.indicators?.atr_pct?.toFixed(2) || '-'}%
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Volatility measure
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground">RSI (14)</div>
                      <div className="text-xl font-bold">
                        {selectedTrade.indicators?.rsi?.toFixed(1) || '-'}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {selectedTrade.indicators?.rsi
                          ? selectedTrade.indicators.rsi > 70 ? 'Overbought'
                            : selectedTrade.indicators.rsi < 30 ? 'Oversold'
                              : 'Neutral'
                          : ''}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground">Volume Ratio</div>
                      <div className="text-xl font-bold">
                        {selectedTrade.indicators?.volume_ratio?.toFixed(2) || '-'}x
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        vs 20-day average
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="text-xs text-muted-foreground">24h Price Change</div>
                      <div className={cn(
                        "text-xl font-bold",
                        (selectedTrade.indicators?.price_change_24h || 0) >= 0 ? "text-green-500" : "text-red-500"
                      )}>
                        {formatPercent(selectedTrade.indicators?.price_change_24h)}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Flags */}
                <div className="flex gap-4">
                  <Badge variant={selectedTrade.indicators?.compression_flag ? 'default' : 'outline'}>
                    {selectedTrade.indicators?.compression_flag ? 'Compression Detected' : 'No Compression'}
                  </Badge>
                  <Badge variant={selectedTrade.indicators?.breakout_flag ? 'default' : 'outline'}>
                    {selectedTrade.indicators?.breakout_flag ? 'Breakout Detected' : 'No Breakout'}
                  </Badge>
                </div>
              </TabsContent>

              <TabsContent value="strategy" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Strategy Selection Logic</CardTitle>
                    <CardDescription>
                      Why this strategy mode was selected based on market conditions
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="p-4 bg-muted rounded-lg">
                      <div className="font-medium mb-2">Decision Flow:</div>
                      <div className="text-sm space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">1</Badge>
                          <span>Regime detected: <strong>{selectedTrade.regime || 'Unknown'}</strong></span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">2</Badge>
                          <span>Strategy selected: <strong>{selectedTrade.strategy?.mode || 'DEFAULT'}</strong></span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">3</Badge>
                          <span>Stop %: <strong>{selectedTrade.strategy?.stop_pct_used?.toFixed(1) || '-'}%</strong></span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">4</Badge>
                          <span>Target %: <strong>{selectedTrade.strategy?.target_pct_used?.toFixed(1) || '-'}%</strong></span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">5</Badge>
                          <span>Size multiplier: <strong>{selectedTrade.strategy?.size_multiplier?.toFixed(2) || '1.00'}x</strong></span>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <div className="text-xs text-muted-foreground">Min Probability Threshold</div>
                        <div className="font-medium">
                          {selectedTrade.thresholds?.min_prob
                            ? `${(selectedTrade.thresholds.min_prob * 100).toFixed(0)}%`
                            : '-'}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <div className="text-xs text-muted-foreground">Min Signal Strength</div>
                        <div className="font-medium">
                          {selectedTrade.thresholds?.min_strength?.toFixed(0) || '-'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-sm">Threshold Check:</span>
                      <Badge className={selectedTrade.thresholds?.passed ? 'bg-green-500' : 'bg-red-500'}>
                        {selectedTrade.thresholds?.passed ? 'PASSED' : 'FAILED'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="raw" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Raw Decision Snapshot</CardTitle>
                    <CardDescription>
                      Complete JSON snapshot captured at entry time
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto max-h-96">
                      {JSON.stringify(selectedTrade.raw_snapshot, null, 2) || 'No raw snapshot available'}
                    </pre>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Full Trade Record</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto max-h-96">
                      {JSON.stringify(selectedTrade, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
