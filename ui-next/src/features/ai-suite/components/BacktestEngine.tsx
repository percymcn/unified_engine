'use client';

import { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  LineChart as LineChartIcon,
  Play,
  Pause,
  RotateCcw,
  TrendingUp,
  TrendingDown,
  Calendar,
  DollarSign,
  Percent,
  Activity,
  BarChart3,
  Target,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BacktestConfig, BacktestResults, BacktestTrade, EquityPoint } from '../types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  ReferenceLine,
} from 'recharts';

interface BacktestEngineProps {
  code?: string;
  onResultsChange?: (results: BacktestResults | null) => void;
  className?: string;
}

const SYMBOLS = [
  { value: 'EURUSD', label: 'EUR/USD' },
  { value: 'GBPUSD', label: 'GBP/USD' },
  { value: 'USDJPY', label: 'USD/JPY' },
  { value: 'XAUUSD', label: 'XAU/USD (Gold)' },
  { value: 'MES1!', label: 'Micro E-mini S&P 500' },
  { value: 'MNQ1!', label: 'Micro E-mini Nasdaq' },
  { value: 'ES1!', label: 'E-mini S&P 500' },
  { value: 'NQ1!', label: 'E-mini Nasdaq' },
  { value: 'BTCUSD', label: 'BTC/USD' },
  { value: 'ETHUSD', label: 'ETH/USD' },
];

const TIMEFRAMES = [
  { value: '1', label: '1 Minute' },
  { value: '5', label: '5 Minutes' },
  { value: '15', label: '15 Minutes' },
  { value: '30', label: '30 Minutes' },
  { value: '60', label: '1 Hour' },
  { value: '240', label: '4 Hours' },
  { value: 'D', label: 'Daily' },
];

const CANDLE_TYPES = [
  { value: 'regular', label: 'Regular Candles' },
  { value: 'heikinashi', label: 'Heikin-Ashi' },
];

// Mock backtest simulation
function simulateBacktest(config: BacktestConfig & { candleType?: string }, code: string): BacktestResults {
  const trades: BacktestTrade[] = [];
  const equityCurve: EquityPoint[] = [];
  let equity = config.initialCapital;
  let maxEquity = equity;
  let maxDrawdown = 0;
  let maxDrawdownPercent = 0;

  // Parse start/end dates
  const startDate = new Date(config.startDate);
  const endDate = new Date(config.endDate);
  const days = Math.floor((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));

  // Simulate based on code characteristics
  const isLongOnly = code.includes('long_only') || !code.includes('strategy.short');
  const hasATRStop = code.toLowerCase().includes('atr');
  const hasRSIFilter = code.toLowerCase().includes('rsi');
  const isHeikinAshi = config.candleType === 'heikinashi';

  // Adjust win rate based on strategy characteristics
  let baseWinRate = 0.45;
  if (hasATRStop) baseWinRate += 0.05;
  if (hasRSIFilter) baseWinRate += 0.03;

  // Heikin-Ashi candles typically smooth price action, reducing false signals
  // This can improve win rate and trend following but may delay entries/exits
  if (isHeikinAshi) {
    baseWinRate += 0.08; // Heikin-Ashi tends to filter out noise
  }

  // Generate trades (roughly 2-4 trades per week based on timeframe)
  const tradesPerWeek = config.timeframe === 'D' ? 1 : config.timeframe === '60' ? 3 : 5;
  const numTrades = Math.floor((days / 7) * tradesPerWeek);

  for (let i = 0; i < numTrades; i++) {
    const tradeDate = new Date(startDate.getTime() + (i / numTrades) * (endDate.getTime() - startDate.getTime()));
    const isWin = Math.random() < baseWinRate;
    const isLong = isLongOnly || Math.random() > 0.5;

    // Calculate position size (risk 1% per trade)
    const riskAmount = equity * 0.01;
    const entryPrice = 100 + Math.random() * 10; // Normalized price
    const stopDistance = entryPrice * 0.005; // 0.5% stop
    const size = riskAmount / stopDistance;

    // Calculate P&L
    let pnl: number;
    let exitReason: 'sl' | 'tp' | 'signal';

    if (isWin) {
      // Win: 1.5-3x R
      const rMultiple = 1.5 + Math.random() * 1.5;
      pnl = riskAmount * rMultiple;
      exitReason = Math.random() > 0.3 ? 'tp' : 'signal';
    } else {
      // Loss: 0.5-1x R
      const rMultiple = 0.5 + Math.random() * 0.5;
      pnl = -riskAmount * rMultiple;
      exitReason = Math.random() > 0.2 ? 'sl' : 'signal';
    }

    // Apply commission
    const commission = config.commission * size * 2;
    pnl -= commission;

    // Update equity
    equity += pnl;
    maxEquity = Math.max(maxEquity, equity);
    const drawdown = maxEquity - equity;
    const drawdownPct = (drawdown / maxEquity) * 100;
    maxDrawdown = Math.max(maxDrawdown, drawdown);
    maxDrawdownPercent = Math.max(maxDrawdownPercent, drawdownPct);

    trades.push({
      id: `trade-${i + 1}`,
      entryTime: tradeDate.toISOString(),
      exitTime: new Date(tradeDate.getTime() + Math.random() * 24 * 60 * 60 * 1000).toISOString(),
      side: isLong ? 'long' : 'short',
      entryPrice: entryPrice,
      exitPrice: entryPrice * (1 + (pnl / (size * entryPrice))),
      size: Math.round(size * 100) / 100,
      pnl: Math.round(pnl * 100) / 100,
      pnlPercent: Math.round((pnl / config.initialCapital) * 10000) / 100,
      commission: Math.round(commission * 100) / 100,
      exitReason,
    });

    equityCurve.push({
      date: tradeDate.toISOString().split('T')[0],
      equity: Math.round(equity * 100) / 100,
      drawdown: Math.round(drawdown * 100) / 100,
    });
  }

  // Calculate statistics
  const winningTrades = trades.filter((t) => t.pnl > 0);
  const losingTrades = trades.filter((t) => t.pnl < 0);
  const totalPnl = trades.reduce((sum, t) => sum + t.pnl, 0);
  const grossProfit = winningTrades.reduce((sum, t) => sum + t.pnl, 0);
  const grossLoss = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0));

  // Monthly returns (simplified)
  const monthlyReturns: { month: string; return: number; trades: number }[] = [];
  const monthMap = new Map<string, { pnl: number; trades: number }>();

  trades.forEach((trade) => {
    const month = trade.entryTime.slice(0, 7);
    const existing = monthMap.get(month) || { pnl: 0, trades: 0 };
    monthMap.set(month, {
      pnl: existing.pnl + trade.pnl,
      trades: existing.trades + 1,
    });
  });

  monthMap.forEach((value, month) => {
    monthlyReturns.push({
      month,
      return: Math.round((value.pnl / config.initialCapital) * 10000) / 100,
      trades: value.trades,
    });
  });

  // Calculate Sharpe Ratio (simplified)
  const avgReturn = totalPnl / numTrades;
  const stdDev = Math.sqrt(
    trades.reduce((sum, t) => sum + Math.pow(t.pnl - avgReturn, 2), 0) / numTrades
  );
  const sharpeRatio = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252 / (days / numTrades)) : 0;

  // Calculate Sortino Ratio
  const downside = trades.filter((t) => t.pnl < 0);
  const downsideStdDev = Math.sqrt(
    downside.reduce((sum, t) => sum + Math.pow(t.pnl, 2), 0) / (downside.length || 1)
  );
  const sortinoRatio = downsideStdDev > 0 ? (avgReturn / downsideStdDev) * Math.sqrt(252 / (days / numTrades)) : 0;

  return {
    totalTrades: trades.length,
    winningTrades: winningTrades.length,
    losingTrades: losingTrades.length,
    winRate: Math.round((winningTrades.length / trades.length) * 10000) / 100,
    totalPnl: Math.round(totalPnl * 100) / 100,
    totalPnlPercent: Math.round((totalPnl / config.initialCapital) * 10000) / 100,
    maxDrawdown: Math.round(maxDrawdown * 100) / 100,
    maxDrawdownPercent: Math.round(maxDrawdownPercent * 100) / 100,
    sharpeRatio: Math.round(sharpeRatio * 100) / 100,
    sortinoRatio: Math.round(sortinoRatio * 100) / 100,
    profitFactor: grossLoss > 0 ? Math.round((grossProfit / grossLoss) * 100) / 100 : 0,
    averageWin: winningTrades.length > 0 ? Math.round((grossProfit / winningTrades.length) * 100) / 100 : 0,
    averageLoss: losingTrades.length > 0 ? Math.round((grossLoss / losingTrades.length) * 100) / 100 : 0,
    largestWin: winningTrades.length > 0 ? Math.round(Math.max(...winningTrades.map((t) => t.pnl)) * 100) / 100 : 0,
    largestLoss: losingTrades.length > 0 ? Math.round(Math.min(...losingTrades.map((t) => t.pnl)) * 100) / 100 : 0,
    averageHoldingPeriod: 24, // Hours (simplified)
    equityCurve,
    trades,
    monthlyReturns,
  };
}

export function BacktestEngine({
  code = '',
  onResultsChange,
  className,
}: BacktestEngineProps) {
  const [config, setConfig] = useState<BacktestConfig & { candleType: string }>({
    symbol: 'EURUSD',
    timeframe: '60',
    startDate: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    initialCapital: 10000,
    commission: 0.5,
    slippage: 0.1,
    candleType: 'regular',
  });

  const [results, setResults] = useState<BacktestResults | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [activeTab, setActiveTab] = useState<'overview' | 'equity' | 'trades' | 'monthly'>('overview');

  const runBacktest = useCallback(async () => {
    if (!code) {
      return;
    }

    setIsRunning(true);
    setProgress(0);
    setResults(null);

    // Simulate progress
    for (let i = 0; i <= 100; i += 10) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      setProgress(i);
    }

    // Run simulation
    const backtestResults = simulateBacktest(config, code);
    setResults(backtestResults);
    onResultsChange?.(backtestResults);
    setIsRunning(false);
  }, [code, config, onResultsChange]);

  const resetBacktest = () => {
    setResults(null);
    setProgress(0);
  };

  return (
    <Card className={cn('cyber-card', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              Backtest Engine
            </CardTitle>
            <CardDescription>
              Simulate your strategy on historical data
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-xs">
            Mock Engine v1.0
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Configuration */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="space-y-2">
            <Label>Symbol</Label>
            <Select
              value={config.symbol}
              onValueChange={(v) => setConfig({ ...config, symbol: v })}
              disabled={isRunning}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SYMBOLS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Timeframe</Label>
            <Select
              value={config.timeframe}
              onValueChange={(v) => setConfig({ ...config, timeframe: v })}
              disabled={isRunning}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEFRAMES.map((tf) => (
                  <SelectItem key={tf.value} value={tf.value}>
                    {tf.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Candle Type</Label>
            <Select
              value={config.candleType}
              onValueChange={(v) => setConfig({ ...config, candleType: v })}
              disabled={isRunning}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CANDLE_TYPES.map((ct) => (
                  <SelectItem key={ct.value} value={ct.value}>
                    {ct.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Start Date</Label>
            <Input
              type="date"
              value={config.startDate}
              onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
              disabled={isRunning}
            />
          </div>

          <div className="space-y-2">
            <Label>End Date</Label>
            <Input
              type="date"
              value={config.endDate}
              onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
              disabled={isRunning}
            />
          </div>

          <div className="space-y-2">
            <Label>Initial Capital</Label>
            <Input
              type="number"
              value={config.initialCapital}
              onChange={(e) => setConfig({ ...config, initialCapital: parseFloat(e.target.value) })}
              disabled={isRunning}
            />
          </div>

          <div className="space-y-2">
            <Label>Commission ($)</Label>
            <Input
              type="number"
              step={0.01}
              value={config.commission}
              onChange={(e) => setConfig({ ...config, commission: parseFloat(e.target.value) })}
              disabled={isRunning}
            />
          </div>

          <div className="space-y-2">
            <Label>Slippage ($)</Label>
            <Input
              type="number"
              step={0.01}
              value={config.slippage}
              onChange={(e) => setConfig({ ...config, slippage: parseFloat(e.target.value) })}
              disabled={isRunning}
            />
          </div>

          <div className="flex items-end">
            <Button
              onClick={runBacktest}
              disabled={isRunning || !code}
              className="w-full"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Backtest
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Progress */}
        {isRunning && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Processing...</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} />
          </div>
        )}

        {/* Results */}
        {results && (
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="equity">Equity</TabsTrigger>
              <TabsTrigger value="trades">Trades</TabsTrigger>
              <TabsTrigger value="monthly">Monthly</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  title="Total P&L"
                  value={`$${results.totalPnl.toLocaleString()}`}
                  subtitle={`${results.totalPnlPercent > 0 ? '+' : ''}${results.totalPnlPercent}%`}
                  icon={DollarSign}
                  positive={results.totalPnl > 0}
                />
                <StatCard
                  title="Win Rate"
                  value={`${results.winRate}%`}
                  subtitle={`${results.winningTrades}W / ${results.losingTrades}L`}
                  icon={Target}
                  positive={results.winRate > 50}
                />
                <StatCard
                  title="Profit Factor"
                  value={results.profitFactor.toFixed(2)}
                  subtitle={results.profitFactor > 1 ? 'Profitable' : 'Unprofitable'}
                  icon={TrendingUp}
                  positive={results.profitFactor > 1}
                />
                <StatCard
                  title="Max Drawdown"
                  value={`$${results.maxDrawdown.toLocaleString()}`}
                  subtitle={`${results.maxDrawdownPercent}%`}
                  icon={AlertTriangle}
                  positive={results.maxDrawdownPercent < 20}
                />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  title="Sharpe Ratio"
                  value={results.sharpeRatio.toFixed(2)}
                  subtitle={results.sharpeRatio > 1 ? 'Good' : results.sharpeRatio > 0 ? 'Acceptable' : 'Poor'}
                  icon={Activity}
                  positive={results.sharpeRatio > 1}
                />
                <StatCard
                  title="Sortino Ratio"
                  value={results.sortinoRatio.toFixed(2)}
                  subtitle="Risk-adjusted"
                  icon={Activity}
                  positive={results.sortinoRatio > 1}
                />
                <StatCard
                  title="Avg Win"
                  value={`$${results.averageWin.toLocaleString()}`}
                  subtitle={`Largest: $${results.largestWin}`}
                  icon={TrendingUp}
                  positive
                />
                <StatCard
                  title="Avg Loss"
                  value={`$${results.averageLoss.toLocaleString()}`}
                  subtitle={`Largest: $${Math.abs(results.largestLoss)}`}
                  icon={TrendingDown}
                  positive={false}
                />
              </div>
            </TabsContent>

            {/* Equity Curve Tab */}
            <TabsContent value="equity" className="space-y-4">
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={100}>
                  <AreaChart data={results.equityCurve}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#9CA3AF', fontSize: 10 }}
                      tickFormatter={(v) => v.slice(5)}
                    />
                    <YAxis
                      tick={{ fill: '#9CA3AF', fontSize: 10 }}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                      formatter={(value: number) => [`$${value.toLocaleString()}`, 'Equity']}
                    />
                    <ReferenceLine y={config.initialCapital} stroke="#6B7280" strokeDasharray="3 3" />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#10B981"
                      fill="url(#equityGradient)"
                    />
                    <defs>
                      <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Drawdown Chart */}
              <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={50}>
                  <AreaChart data={results.equityCurve}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#9CA3AF', fontSize: 10 }}
                      tickFormatter={(v) => v.slice(5)}
                    />
                    <YAxis
                      tick={{ fill: '#9CA3AF', fontSize: 10 }}
                      tickFormatter={(v) => `-$${v}`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                      formatter={(value: number) => [`$${value.toLocaleString()}`, 'Drawdown']}
                    />
                    <Area
                      type="monotone"
                      dataKey="drawdown"
                      stroke="#EF4444"
                      fill="url(#drawdownGradient)"
                    />
                    <defs>
                      <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </TabsContent>

            {/* Trades Tab */}
            <TabsContent value="trades">
              <div className="max-h-[400px] overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead>Entry</TableHead>
                      <TableHead>Exit</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>P&L</TableHead>
                      <TableHead>Exit</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.trades.slice(0, 50).map((trade) => (
                      <TableRow key={trade.id}>
                        <TableCell className="text-xs">
                          {new Date(trade.entryTime).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-xs',
                              trade.side === 'long'
                                ? 'border-emerald-500 text-emerald-400'
                                : 'border-red-500 text-red-400'
                            )}
                          >
                            {trade.side === 'long' ? (
                              <TrendingUp className="h-3 w-3 mr-1" />
                            ) : (
                              <TrendingDown className="h-3 w-3 mr-1" />
                            )}
                            {trade.side}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {trade.entryPrice.toFixed(5)}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {trade.exitPrice.toFixed(5)}
                        </TableCell>
                        <TableCell className="text-xs">{trade.size}</TableCell>
                        <TableCell
                          className={cn(
                            'font-medium text-xs',
                            trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                          )}
                        >
                          {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="text-xs">
                            {trade.exitReason.toUpperCase()}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            {/* Monthly Returns Tab */}
            <TabsContent value="monthly">
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={100}>
                  <LineChart data={results.monthlyReturns}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="month"
                      tick={{ fill: '#9CA3AF', fontSize: 10 }}
                      tickFormatter={(v) => v.slice(5)}
                    />
                    <YAxis
                      tick={{ fill: '#9CA3AF', fontSize: 10 }}
                      tickFormatter={(v) => `${v}%`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                      formatter={(value: number, name: string) => [
                        name === 'return' ? `${value}%` : value,
                        name === 'return' ? 'Return' : 'Trades',
                      ]}
                    />
                    <ReferenceLine y={0} stroke="#6B7280" />
                    <Line
                      type="monotone"
                      dataKey="return"
                      stroke="#8B5CF6"
                      strokeWidth={2}
                      dot={{ fill: '#8B5CF6', strokeWidth: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-4 grid grid-cols-3 md:grid-cols-6 gap-2">
                {results.monthlyReturns.map((month) => (
                  <div
                    key={month.month}
                    className={cn(
                      'p-2 rounded-lg text-center text-xs',
                      month.return >= 0
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    )}
                  >
                    <div className="font-medium">{month.month.slice(5)}</div>
                    <div className="font-bold">
                      {month.return >= 0 ? '+' : ''}
                      {month.return}%
                    </div>
                    <div className="text-muted-foreground">{month.trades} trades</div>
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        )}

        {/* No code warning */}
        {!code && (
          <div className="text-center py-8 text-muted-foreground">
            <AlertTriangle className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>Enter Pine Script code in the editor to run a backtest</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Stat Card Component
interface StatCardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  positive: boolean;
}

function StatCard({ title, value, subtitle, icon: Icon, positive }: StatCardProps) {
  return (
    <div className="p-4 rounded-lg bg-muted/50 border border-border/50">
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Icon className="h-4 w-4" />
        {title}
      </div>
      <div
        className={cn(
          'text-xl font-bold mt-1',
          positive ? 'text-emerald-400' : 'text-red-400'
        )}
      >
        {value}
      </div>
      <div className="text-xs text-muted-foreground">{subtitle}</div>
    </div>
  );
}
