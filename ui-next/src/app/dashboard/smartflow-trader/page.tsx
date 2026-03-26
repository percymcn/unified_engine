'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { PauseCircle, PlayCircle, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';

const REFRESH_INTERVAL_MS = 30000;

type TraderStatus = {
  state?: string;
  mode?: string;
  running?: boolean;
  paused?: boolean;
  paper_mode?: boolean;
  positions?: unknown[];
};

type PerformanceSnapshot = {
  win_rate?: number;
  total_pnl?: number;
  avg_win?: number;
  avg_loss?: number;
  profit_factor?: number;
  max_drawdown?: number;
};

type SignalRow = {
  id?: string | number;
  timestamp?: string;
  created_at?: string;
  symbol?: string;
  ticker?: string;
  action?: string;
  side?: string;
  confidence?: number;
  score?: number;
  strategy?: string;
  engine_type?: string;
  result?: string;
  post_successful?: boolean;
};

type TradeRow = {
  id?: string | number;
  entry_time?: string;
  entry_at?: string;
  symbol?: string;
  ticker?: string;
  direction?: string;
  side?: string;
  entry_price?: number;
  exit_price?: number;
  pnl?: number;
  status?: string;
};

type TradesResponse = {
  trades?: TradeRow[];
} | TradeRow[];

const formatNumber = (value?: number, decimals = 2) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '--';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

const formatPercent = (value?: number) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '--';
  const normalized = value > 1 ? value : value * 100;
  return `${formatNumber(normalized, 2)}%`;
};

const formatCurrency = (value?: number) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '--';
  const formatted = formatNumber(Math.abs(value), 2);
  return value >= 0 ? `+$${formatted}` : `-$${formatted}`;
};

const formatDateTime = (value?: string) => {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || 'Request failed');
  }

  return response.json();
}

export default function SmartFlowTraderPage() {
  const [status, setStatus] = useState<TraderStatus | null>(null);
  const [performance, setPerformance] = useState<PerformanceSnapshot | null>(null);
  const [signals, setSignals] = useState<SignalRow[]>([]);
  const [trades, setTrades] = useState<TradeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadAll = useCallback(async () => {
    try {
      setError(null);
      const [statusData, performanceData, tradesData, signalsData] = await Promise.all([
        fetchJson<TraderStatus>('/api/v1/smartflow/trader/status'),
        fetchJson<PerformanceSnapshot>('/api/v1/smartflow/trader/performance'),
        fetchJson<TradesResponse>('/api/v1/smartflow/trader/trades'),
        fetchJson<SignalRow[]>('/api/v1/smartflow/trader/signals'),
      ]);

      setStatus(statusData);
      setPerformance(performanceData);
      const tradeRows = Array.isArray(tradesData) ? tradesData : tradesData.trades || [];
      setTrades(tradeRows);
      setSignals(signalsData || []);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load SmartFlow Trader data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadAll]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadAll();
  };

  const statusSummary = useMemo(() => {
    if (!status) {
      return {
        stateLabel: 'Unknown',
        modeLabel: 'Unknown',
        isRunning: false,
        isPaper: true,
      };
    }

    const isPaper = status.paper_mode ?? (status.mode ? status.mode.toLowerCase() === 'paper' : true);
    const isPaused = status.paused ?? (status.state ? status.state.toLowerCase() === 'paused' : false);
    const isRunning = status.running ?? (status.state ? status.state.toLowerCase() === 'running' : false);

    return {
      stateLabel: status.state || (isPaused ? 'Paused' : isRunning ? 'Running' : 'Unknown'),
      modeLabel: status.mode || (isPaper ? 'Paper' : 'Live'),
      isRunning,
      isPaper,
    };
  }, [status]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading SmartFlow Trader...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-destructive">Error: {error}</p>
          <Button onClick={handleRefresh} className="mt-4" variant="outline">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-muted-foreground">
          {lastUpdated ? `Last refresh: ${lastUpdated.toLocaleTimeString()}` : 'Awaiting refresh'}
        </div>
        <Button
          onClick={handleRefresh}
          variant="outline"
          size="sm"
          disabled={refreshing}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Trader Status</CardTitle>
            <CardDescription>Mode and runtime state</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2">
              {statusSummary.isRunning ? (
                <PlayCircle className="h-5 w-5 text-emerald-500" />
              ) : (
                <PauseCircle className="h-5 w-5 text-amber-500" />
              )}
              <span className="text-lg font-semibold">{statusSummary.stateLabel}</span>
            </div>
            <Badge
              variant="outline"
              className={statusSummary.isPaper ? 'border-amber-500/40 text-amber-400' : 'border-emerald-500/40 text-emerald-400'}
            >
              {statusSummary.modeLabel} Mode
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
            <CardDescription>Currently open trades</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{status?.positions?.length ?? 0}</div>
            <p className="text-xs text-muted-foreground mt-2">Auto-refreshing every 30s</p>
          </CardContent>
        </Card>

      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{formatPercent(performance?.win_rate)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total P&amp;L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-semibold ${performance?.total_pnl && performance.total_pnl < 0 ? 'text-red-500' : 'text-emerald-500'}`}>
              {formatCurrency(performance?.total_pnl)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Profit Factor</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{formatNumber(performance?.profit_factor)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">${formatNumber(performance?.max_drawdown)}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Signals</CardTitle>
          <CardDescription>Most recent SmartFlow signal decisions</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {signals.length ? (
                signals.map((signal, index) => {
                  const action = (signal.action || signal.side || '').toUpperCase();
                  const confidence = signal.confidence ?? signal.score;
                  const resultLabel = signal.result || (signal.post_successful ? 'Success' : signal.post_successful === false ? 'Failed' : 'Pending');
                  return (
                    <TableRow key={signal.id ?? `${signal.symbol}-${index}`}>
                      <TableCell>{formatDateTime(signal.timestamp || signal.created_at)}</TableCell>
                      <TableCell className="font-medium">{signal.symbol || signal.ticker || '--'}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={action === 'BUY' ? 'border-emerald-500/40 text-emerald-400' : action === 'SELL' ? 'border-rose-500/40 text-rose-400' : ''}>
                          {action || '--'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {confidence !== undefined && confidence !== null ? (
                            confidence >= 0 ? (
                              <TrendingUp className="h-4 w-4 text-emerald-500" />
                            ) : (
                              <TrendingDown className="h-4 w-4 text-rose-500" />
                            )
                          ) : null}
                          <span>{formatPercent(confidence)}</span>
                        </div>
                      </TableCell>
                      <TableCell>{signal.strategy || signal.engine_type || '--'}</TableCell>
                      <TableCell>{resultLabel}</TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    No recent signals.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>Latest SmartFlow executed trades</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Entry Time</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead>Entry Price</TableHead>
                <TableHead>Exit Price</TableHead>
                <TableHead>P&amp;L</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.length ? (
                trades.map((trade, index) => {
                  const direction = (trade.direction || trade.side || '').toUpperCase();
                  const pnlClass = trade.pnl && trade.pnl < 0 ? 'text-red-500' : 'text-emerald-500';
                  return (
                    <TableRow key={trade.id ?? `${trade.symbol}-${index}`}>
                      <TableCell>{formatDateTime(trade.entry_time || trade.entry_at)}</TableCell>
                      <TableCell className="font-medium">{trade.symbol || trade.ticker || '--'}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={direction === 'BUY' || direction === 'LONG' ? 'border-emerald-500/40 text-emerald-400' : direction === 'SELL' || direction === 'SHORT' ? 'border-rose-500/40 text-rose-400' : ''}>
                          {direction || '--'}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatNumber(trade.entry_price)}</TableCell>
                      <TableCell>{formatNumber(trade.exit_price)}</TableCell>
                      <TableCell className={pnlClass}>{formatCurrency(trade.pnl)}</TableCell>
                      <TableCell>{trade.status || '--'}</TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
                    No trades available.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
