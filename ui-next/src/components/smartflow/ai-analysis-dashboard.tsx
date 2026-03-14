'use client';

import { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Search,
  BarChart3,
  Clock,
  Target,
  Loader2,
  ChevronDown,
  ChevronUp,
  Eye,
  Zap,
  Bot,
  Activity,
  DollarSign,
  CheckCircle,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TradeDecision {
  execution_id: number;
  symbol: string;
  trade_action: string;
  entry_price: number;
  exit_price: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  status: string;
  close_reason: string | null;
  trade_time: string;
  closed_at: string | null;
  broker: string;
  signal: {
    id: number;
    ticker: string;
    action: string;
    fss_score: number;
    confidence: number;
    reason: string;
    bullish_flows: number;
    bearish_flows: number;
    total_premium: number;
    time: string;
  } | null;
  outcome: {
    is_winner: boolean;
    market_regime: string;
    hour_of_day: number;
    day_of_week: number;
  } | null;
  ai_context: {
    mode: string;
    recommendation: string | null;
    confidence_boost: number;
  };
  ai_analysis: {
    recommendation: string;
    confidence: number;
    summary: string;
    data: {
      trend?: { daily: string; weekly: string; monthly: string };
      indicators?: { rsi: number; macd: string; bollinger: string };
      moving_averages?: Record<string, number>;
      support_levels?: number[];
      resistance_levels?: number[];
      entry_price?: number;
      stop_loss?: number;
      profit_target?: number;
      risk_reward_ratio?: number;
      chart_pattern?: string;
      volume_trend?: string;
    };
    analyzed_at: string;
  } | null;
}

interface TradeDecisionStats {
  by_mode: Record<string, { count: number; winners: number; losers: number; win_rate: number }>;
  by_ticker: Record<string, { trades: number; winners: number; win_rate: number }>;
  last_7_days: {
    total_trades: number;
    winners: number;
    win_rate: number;
    total_pnl: number;
  };
}

interface AIAnalysis {
  id: number;
  ticker: string;
  analysis_type: string;
  recommendation: string;
  confidence: number;
  summary: string;
  data: Record<string, unknown>;
  created_at: string;
  hit_count: number;
}

export function AIAnalysisDashboard() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [decisions, setDecisions] = useState<TradeDecision[]>([]);
  const [decisionStats, setDecisionStats] = useState<TradeDecisionStats | null>(null);
  const [analyses, setAnalyses] = useState<AIAnalysis[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<TradeDecision | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  // Filters
  const [tickerFilter, setTickerFilter] = useState('');
  const [modeFilter, setModeFilter] = useState('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [decisionsRes, statsRes, analysesRes] = await Promise.all([
        fetch('/api/v1/smartflow/trade-decisions?limit=100', { credentials: 'include' }),
        fetch('/api/v1/smartflow/trade-decisions/stats', { credentials: 'include' }),
        fetch('/api/v1/smartflow/ai/analysis?limit=50', { credentials: 'include' }),
      ]);

      if (decisionsRes.ok) {
        const data = await decisionsRes.json();
        setDecisions(data.decisions || []);
      }

      if (statsRes.ok) {
        const data = await statsRes.json();
        setDecisionStats(data);
      }

      if (analysesRes.ok) {
        const data = await analysesRes.json();
        setAnalyses(data.analyses || []);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load trade decision data',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = async () => {
    setLoading(true);
    try {
      let url = '/api/v1/smartflow/trade-decisions?limit=100';
      if (tickerFilter) url += `&ticker=${encodeURIComponent(tickerFilter)}`;

      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        let filtered = data.decisions || [];

        // Client-side mode filtering
        if (modeFilter !== 'all') {
          filtered = filtered.filter((d: TradeDecision) => d.ai_context.mode === modeFilter);
        }

        setDecisions(filtered);
      }
    } catch (error) {
      console.error('Failed to filter:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      timeZone: 'America/New_York',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  const formatPrice = (price: number | null) => {
    if (price === null) return '-';
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatPnl = (pnl: number | null) => {
    if (pnl === null) return '-';
    const formatted = Math.abs(pnl).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return pnl >= 0 ? `+$${formatted}` : `-$${formatted}`;
  };

  const getModeBadge = (mode: string) => {
    switch (mode) {
      case 'ai_only':
        return <Badge className="bg-violet-500"><Bot className="h-3 w-3 mr-1" />AI Only</Badge>;
      case 'hybrid':
        return <Badge className="bg-blue-500"><Zap className="h-3 w-3 mr-1" />Hybrid</Badge>;
      default:
        return <Badge variant="outline"><Activity className="h-3 w-3 mr-1" />Flow Only</Badge>;
    }
  };

  const getOutcomeBadge = (decision: TradeDecision) => {
    if (decision.outcome?.is_winner === true) {
      return <Badge className="bg-green-500"><CheckCircle className="h-3 w-3 mr-1" />Winner</Badge>;
    } else if (decision.outcome?.is_winner === false) {
      return <Badge className="bg-red-500"><XCircle className="h-3 w-3 mr-1" />Loser</Badge>;
    } else {
      return <Badge variant="outline"><Clock className="h-3 w-3 mr-1" />Open</Badge>;
    }
  };

  const getActionBadge = (action: string) => {
    if (action.toLowerCase() === 'buy') {
      return <Badge className="bg-green-600"><TrendingUp className="h-3 w-3 mr-1" />BUY</Badge>;
    } else {
      return <Badge className="bg-red-600"><TrendingDown className="h-3 w-3 mr-1" />SELL</Badge>;
    }
  };

  if (loading && decisions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <Tabs defaultValue="decisions" className="w-full">
      <TabsList className="grid w-full grid-cols-2 mb-4">
        <TabsTrigger value="decisions" className="flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Trade Decisions
        </TabsTrigger>
        <TabsTrigger value="analyses" className="flex items-center gap-2">
          <Brain className="h-4 w-4" />
          AI Analysis Cache
        </TabsTrigger>
      </TabsList>

      <TabsContent value="decisions" className="space-y-6">
        {/* Stats Overview */}
        {decisionStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">7-Day Trades</p>
                    <p className="text-2xl font-bold">{decisionStats.last_7_days.total_trades}</p>
                  </div>
                  <Activity className="h-8 w-8 text-blue-500 opacity-50" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">7-Day Win Rate</p>
                    <p className={cn(
                      "text-2xl font-bold",
                      decisionStats.last_7_days.win_rate >= 50 ? "text-green-500" : "text-red-500"
                    )}>
                      {decisionStats.last_7_days.win_rate}%
                    </p>
                  </div>
                  <Target className="h-8 w-8 text-green-500 opacity-50" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">7-Day P&L</p>
                    <p className={cn(
                      "text-2xl font-bold",
                      decisionStats.last_7_days.total_pnl >= 0 ? "text-green-500" : "text-red-500"
                    )}>
                      {formatPnl(decisionStats.last_7_days.total_pnl)}
                    </p>
                  </div>
                  <DollarSign className="h-8 w-8 text-yellow-500 opacity-50" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">AI-Only Trades</p>
                    <p className="text-2xl font-bold text-violet-500">
                      {decisionStats.by_mode['ai_only']?.count || 0}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {decisionStats.by_mode['ai_only']?.win_rate || 0}% win
                    </p>
                  </div>
                  <Bot className="h-8 w-8 text-violet-500 opacity-50" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Mode Breakdown */}
        {decisionStats && Object.keys(decisionStats.by_mode).length > 0 && (
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Performance by Mode
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(decisionStats.by_mode).map(([mode, stats]) => (
                  <div key={mode} className="p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center justify-between mb-2">
                      {getModeBadge(mode)}
                      <span className="text-sm font-medium">{stats.count} trades</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-green-500">{stats.winners} W</span>
                      <span className="text-red-500">{stats.losers} L</span>
                      <span className={cn(
                        "font-semibold",
                        stats.win_rate >= 50 ? "text-green-500" : "text-red-500"
                      )}>
                        {stats.win_rate}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filters */}
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Search className="h-4 w-4" />
              Filter Trade Decisions
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex flex-wrap gap-4 items-end">
              <div className="space-y-1">
                <Label className="text-xs">Ticker</Label>
                <Input
                  placeholder="e.g., MES, NQ"
                  value={tickerFilter}
                  onChange={(e) => setTickerFilter(e.target.value)}
                  className="w-32"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Mode</Label>
                <Select value={modeFilter} onValueChange={setModeFilter}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="ai_only">AI Only</SelectItem>
                    <SelectItem value="hybrid">Hybrid</SelectItem>
                    <SelectItem value="flow_only">Flow Only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button size="sm" onClick={applyFilters} disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                Apply
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setTickerFilter('');
                  setModeFilter('all');
                  loadData();
                }}
              >
                Clear
              </Button>
              <Button size="sm" variant="outline" onClick={loadData}>
                <RefreshCw className={cn("h-4 w-4 mr-1", loading && "animate-spin")} />
                Refresh
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Trade Decisions Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-violet-500" />
              Trade Decision History
            </CardTitle>
            <CardDescription>
              Every trade with full AI analysis context ({decisions.length} results)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {decisions.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Mode</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Entry</TableHead>
                    <TableHead>P&L</TableHead>
                    <TableHead>Outcome</TableHead>
                    <TableHead className="text-right">Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {decisions.map((decision) => (
                    <TableRow key={decision.execution_id}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatTime(decision.trade_time)}
                      </TableCell>
                      <TableCell className="font-semibold">{decision.symbol}</TableCell>
                      <TableCell>{getActionBadge(decision.trade_action)}</TableCell>
                      <TableCell>{getModeBadge(decision.ai_context.mode)}</TableCell>
                      <TableCell>
                        <Badge className={cn(
                          (decision.signal?.confidence || 0) >= 70 ? "bg-green-500" :
                          (decision.signal?.confidence || 0) >= 50 ? "bg-blue-500" :
                          "bg-gray-500"
                        )}>
                          {decision.signal?.confidence || 0}%
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        ${formatPrice(decision.entry_price)}
                      </TableCell>
                      <TableCell className={cn(
                        "font-semibold",
                        (decision.pnl || 0) >= 0 ? "text-green-500" : "text-red-500"
                      )}>
                        {formatPnl(decision.pnl)}
                      </TableCell>
                      <TableCell>{getOutcomeBadge(decision)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setSelectedDecision(decision);
                            setShowDetail(true);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No trade decisions found. Enable SmartFlow to start generating trades.
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="analyses" className="space-y-6">
        {/* AI Analysis Cache */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-violet-500" />
              AI Analysis Cache
            </CardTitle>
            <CardDescription>
              All AI analyses stored in the database ({analyses.length} results)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {analyses.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Recommendation</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Summary</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {analyses.map((analysis) => (
                    <TableRow key={analysis.id}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatTime(analysis.created_at)}
                      </TableCell>
                      <TableCell className="font-semibold">{analysis.ticker}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={cn(
                          analysis.analysis_type === 'technical' ? "text-blue-500 border-blue-500" :
                          analysis.analysis_type === 'patterns' ? "text-purple-500 border-purple-500" :
                          "text-orange-500 border-orange-500"
                        )}>
                          {analysis.analysis_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={cn(
                          analysis.recommendation.includes('buy') ? "bg-green-500" :
                          analysis.recommendation.includes('sell') ? "bg-red-500" :
                          "bg-gray-500"
                        )}>
                          {analysis.recommendation}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={cn(
                          analysis.confidence >= 70 ? "bg-green-500" :
                          analysis.confidence >= 50 ? "bg-blue-500" :
                          "bg-gray-500"
                        )}>
                          {analysis.confidence}%
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-md truncate text-sm text-muted-foreground">
                        {analysis.summary || 'No summary'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No AI analyses found. Enable AI Enhancement to start generating analyses.
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      {/* Detail Dialog */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-violet-500" />
              Trade Decision Detail
            </DialogTitle>
            <DialogDescription>
              Full context for trade #{selectedDecision?.execution_id}
            </DialogDescription>
          </DialogHeader>
          {selectedDecision && (
            <div className="space-y-6">
              {/* Trade Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground">Symbol</Label>
                  <p className="font-semibold">{selectedDecision.symbol}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Action</Label>
                  <div className="mt-1">{getActionBadge(selectedDecision.trade_action)}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Mode</Label>
                  <div className="mt-1">{getModeBadge(selectedDecision.ai_context.mode)}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Outcome</Label>
                  <div className="mt-1">{getOutcomeBadge(selectedDecision)}</div>
                </div>
              </div>

              {/* Price Info */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
                <div>
                  <Label className="text-xs text-muted-foreground">Entry Price</Label>
                  <p className="text-lg font-mono">${formatPrice(selectedDecision.entry_price)}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Exit Price</Label>
                  <p className="text-lg font-mono">${formatPrice(selectedDecision.exit_price)}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">P&L</Label>
                  <p className={cn(
                    "text-lg font-semibold",
                    (selectedDecision.pnl || 0) >= 0 ? "text-green-500" : "text-red-500"
                  )}>
                    {formatPnl(selectedDecision.pnl)}
                  </p>
                </div>
              </div>

              {/* Signal Info */}
              {selectedDecision.signal && (
                <div className="space-y-3">
                  <Label className="text-sm font-semibold">Signal Details</Label>
                  <div className="p-4 bg-muted/50 rounded-lg space-y-3">
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <Label className="text-xs text-muted-foreground">FSS Score</Label>
                        <p className={cn(
                          "text-lg font-semibold",
                          selectedDecision.signal.fss_score > 0 ? "text-green-500" : "text-red-500"
                        )}>
                          {selectedDecision.signal.fss_score > 0 ? '+' : ''}{selectedDecision.signal.fss_score}
                        </p>
                      </div>
                      <div>
                        <Label className="text-xs text-muted-foreground">Confidence</Label>
                        <p className="text-lg font-semibold">{selectedDecision.signal.confidence}%</p>
                      </div>
                      <div>
                        <Label className="text-xs text-muted-foreground">AI Boost</Label>
                        <p className={cn(
                          "text-lg font-semibold",
                          selectedDecision.ai_context.confidence_boost > 0 ? "text-green-500" :
                          selectedDecision.ai_context.confidence_boost < 0 ? "text-red-500" : ""
                        )}>
                          {selectedDecision.ai_context.confidence_boost > 0 ? '+' : ''}{selectedDecision.ai_context.confidence_boost}%
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Bullish Flows:</span>{' '}
                        <span className="text-green-500 font-medium">{selectedDecision.signal.bullish_flows}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Bearish Flows:</span>{' '}
                        <span className="text-red-500 font-medium">{selectedDecision.signal.bearish_flows}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Premium:</span>{' '}
                        <span className="font-medium">${(selectedDecision.signal.total_premium / 1000000).toFixed(2)}M</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Full Reason / Analysis Context */}
              {selectedDecision.signal?.reason && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Decision Reasoning</Label>
                  <div className="p-4 bg-violet-500/10 border border-violet-500/20 rounded-lg">
                    <p className="text-sm font-mono whitespace-pre-wrap">{selectedDecision.signal.reason}</p>
                  </div>
                </div>
              )}

              {/* AI Context */}
              <div className="space-y-2">
                <Label className="text-sm font-semibold">AI Context</Label>
                <div className="p-4 bg-muted/50 rounded-lg">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label className="text-xs text-muted-foreground">Mode</Label>
                      <p className="font-medium capitalize">{selectedDecision.ai_context.mode.replace('_', ' ')}</p>
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground">AI Recommendation</Label>
                      <p className="font-medium capitalize">{selectedDecision.ai_context.recommendation || 'N/A'}</p>
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground">Broker</Label>
                      <p className="font-medium">{selectedDecision.broker}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Full AI Analysis (from cache) */}
              {selectedDecision.ai_analysis && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold flex items-center gap-2">
                    <Brain className="h-4 w-4 text-violet-500" />
                    AI Technical Analysis
                  </Label>
                  <div className="p-4 bg-gradient-to-br from-violet-500/5 to-blue-500/5 border border-violet-500/20 rounded-lg space-y-4">
                    {/* Summary */}
                    <p className="text-sm leading-relaxed">{selectedDecision.ai_analysis.summary}</p>

                    {/* Key Metrics Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      {selectedDecision.ai_analysis.data.trend && (
                        <div className="p-2 bg-muted/30 rounded">
                          <Label className="text-xs text-muted-foreground">Trend</Label>
                          <div className="flex gap-1 mt-1">
                            <Badge variant="outline" className={cn(
                              selectedDecision.ai_analysis.data.trend.daily === 'up' ? 'text-green-500' : 'text-red-500'
                            )}>
                              D: {selectedDecision.ai_analysis.data.trend.daily}
                            </Badge>
                            <Badge variant="outline" className={cn(
                              selectedDecision.ai_analysis.data.trend.weekly === 'up' ? 'text-green-500' : 'text-red-500'
                            )}>
                              W: {selectedDecision.ai_analysis.data.trend.weekly}
                            </Badge>
                          </div>
                        </div>
                      )}
                      {selectedDecision.ai_analysis.data.indicators && (
                        <div className="p-2 bg-muted/30 rounded">
                          <Label className="text-xs text-muted-foreground">Indicators</Label>
                          <div className="mt-1 space-y-0.5">
                            <p className="text-xs">RSI: <span className="font-medium">{selectedDecision.ai_analysis.data.indicators.rsi}</span></p>
                            <p className="text-xs">MACD: <span className={cn(
                              "font-medium",
                              selectedDecision.ai_analysis.data.indicators.macd === 'bullish' ? 'text-green-500' : 'text-red-500'
                            )}>{selectedDecision.ai_analysis.data.indicators.macd}</span></p>
                          </div>
                        </div>
                      )}
                      {selectedDecision.ai_analysis.data.chart_pattern && (
                        <div className="p-2 bg-muted/30 rounded">
                          <Label className="text-xs text-muted-foreground">Pattern</Label>
                          <p className="font-medium capitalize mt-1">{selectedDecision.ai_analysis.data.chart_pattern}</p>
                        </div>
                      )}
                      {selectedDecision.ai_analysis.data.risk_reward_ratio && (
                        <div className="p-2 bg-muted/30 rounded">
                          <Label className="text-xs text-muted-foreground">Risk/Reward</Label>
                          <p className="font-medium text-green-500 mt-1">1:{selectedDecision.ai_analysis.data.risk_reward_ratio}</p>
                        </div>
                      )}
                    </div>

                    {/* Price Levels */}
                    {(selectedDecision.ai_analysis.data.entry_price || selectedDecision.ai_analysis.data.stop_loss || selectedDecision.ai_analysis.data.profit_target) && (
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        {selectedDecision.ai_analysis.data.entry_price && (
                          <div className="p-2 bg-blue-500/10 rounded text-center">
                            <Label className="text-xs text-muted-foreground">AI Entry</Label>
                            <p className="font-mono font-medium">${selectedDecision.ai_analysis.data.entry_price.toLocaleString()}</p>
                          </div>
                        )}
                        {selectedDecision.ai_analysis.data.stop_loss && (
                          <div className="p-2 bg-red-500/10 rounded text-center">
                            <Label className="text-xs text-muted-foreground">Stop Loss</Label>
                            <p className="font-mono font-medium text-red-500">${selectedDecision.ai_analysis.data.stop_loss.toLocaleString()}</p>
                          </div>
                        )}
                        {selectedDecision.ai_analysis.data.profit_target && (
                          <div className="p-2 bg-green-500/10 rounded text-center">
                            <Label className="text-xs text-muted-foreground">Target</Label>
                            <p className="font-mono font-medium text-green-500">${selectedDecision.ai_analysis.data.profit_target.toLocaleString()}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Support/Resistance */}
                    {(selectedDecision.ai_analysis.data.support_levels || selectedDecision.ai_analysis.data.resistance_levels) && (
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        {selectedDecision.ai_analysis.data.support_levels && (
                          <div className="p-2 bg-green-500/10 rounded">
                            <Label className="text-xs text-muted-foreground">Support Levels</Label>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {selectedDecision.ai_analysis.data.support_levels.map((level, i) => (
                                <Badge key={i} variant="outline" className="text-green-500 text-xs">${level.toLocaleString()}</Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        {selectedDecision.ai_analysis.data.resistance_levels && (
                          <div className="p-2 bg-red-500/10 rounded">
                            <Label className="text-xs text-muted-foreground">Resistance Levels</Label>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {selectedDecision.ai_analysis.data.resistance_levels.map((level, i) => (
                                <Badge key={i} variant="outline" className="text-red-500 text-xs">${level.toLocaleString()}</Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Moving Averages */}
                    {selectedDecision.ai_analysis.data.moving_averages && (
                      <div className="text-xs">
                        <Label className="text-xs text-muted-foreground">Moving Averages</Label>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {Object.entries(selectedDecision.ai_analysis.data.moving_averages).map(([key, value]) => (
                            <span key={key} className="px-2 py-0.5 bg-muted/50 rounded">
                              <span className="text-muted-foreground">{key.toUpperCase()}:</span> ${(value as number).toLocaleString()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Timing */}
              <div className="text-xs text-muted-foreground flex items-center gap-4">
                <span>Trade Time: {formatTime(selectedDecision.trade_time)}</span>
                {selectedDecision.closed_at && (
                  <span>Closed: {formatTime(selectedDecision.closed_at)}</span>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Tabs>
  );
}
