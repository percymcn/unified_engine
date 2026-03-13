'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  Zap,
  RefreshCw,
  Loader2,
  Sparkles,
  BarChart3,
  Calendar,
  AlertCircle,
  CheckCircle,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModelState {
  ticker: string;
  optimal_buy_threshold: number;
  optimal_sell_threshold: number;
  recent_win_rate: number;
  signals_learned: number;
  training_samples: number;
  model_version: number;
  last_trained: string | null;
  best_hours: number[];
  avoid_hours: number[];
}

interface DailyMetric {
  date: string;
  win_rate: number;
  pnl: number;
  signals: number;
  improvement: number;
}

interface Pattern {
  name: string;
  win_rate: number;
  expectancy: number;
  occurrences: number;
}

interface CorrelationSignal {
  type: string;
  direction: string;
  confidence: number;
  conviction: string;
  tickers: string[];
  profitable: boolean | null;
  time: string;
}

interface MLDashboardData {
  model_state: ModelState | null;
  daily_metrics: DailyMetric[];
  top_patterns: Pattern[];
  recent_correlations: CorrelationSignal[];
  is_learning: boolean;
}

export function MLDashboard() {
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [data, setData] = useState<MLDashboardData | null>(null);
  const [selectedTicker, setSelectedTicker] = useState('SPY');

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [selectedTicker]);

  const loadDashboard = async () => {
    try {
      const response = await fetch(`/api/v1/smartflow/ml/dashboard?ticker=${selectedTicker}`, {
        credentials: 'include',
      });
      if (response.ok) {
        const result = await response.json();
        setData(result);
      }
    } catch (error) {
      console.error('Failed to load ML dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const runOptimization = async () => {
    setOptimizing(true);
    try {
      await fetch('/api/v1/smartflow/ml/run-optimization', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: ['SPY', 'QQQ', 'IWM', 'DIA', 'GLD'] }),
      });
      await loadDashboard();
    } catch (error) {
      console.error('Optimization failed:', error);
    } finally {
      setOptimizing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const modelState = data?.model_state;
  const winRate = modelState?.recent_win_rate || 0.5;
  const isLearning = data?.is_learning || false;
  const improvement = winRate - 0.5; // vs 50% baseline

  return (
    <div className="space-y-6">
      {/* ML Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-12 h-12 rounded-xl flex items-center justify-center",
            isLearning ? "bg-gradient-to-br from-violet-500/20 to-purple-500/20" : "bg-muted"
          )}>
            <Brain className={cn("h-6 w-6", isLearning ? "text-violet-400" : "text-muted-foreground")} />
          </div>
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              ML Learning Engine
              {isLearning && (
                <Badge className="bg-gradient-to-r from-violet-500 to-purple-600">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Active
                </Badge>
              )}
            </h2>
            <p className="text-sm text-muted-foreground">
              {isLearning
                ? `Learning from ${modelState?.training_samples || 0} outcomes`
                : 'Waiting for signal outcomes to learn from'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Ticker selector */}
          <div className="flex gap-1">
            {['SPY', 'QQQ', 'IWM', 'DIA'].map((ticker) => (
              <Button
                key={ticker}
                variant={selectedTicker === ticker ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedTicker(ticker)}
              >
                {ticker}
              </Button>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={runOptimization}
            disabled={optimizing}
          >
            {optimizing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Run Optimization
          </Button>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Win Rate */}
        <Card className={cn(
          "border-2",
          winRate >= 0.6 ? "border-green-500/30" : winRate >= 0.5 ? "border-blue-500/30" : "border-yellow-500/30"
        )}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Target className="h-4 w-4" />
              Current Win Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className={cn(
                "text-3xl font-bold",
                winRate >= 0.6 ? "text-green-500" : winRate >= 0.5 ? "text-blue-500" : "text-yellow-500"
              )}>
                {(winRate * 100).toFixed(1)}%
              </span>
              {improvement !== 0 && (
                <span className={cn(
                  "text-sm flex items-center",
                  improvement > 0 ? "text-green-500" : "text-red-500"
                )}>
                  {improvement > 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
                  {Math.abs(improvement * 100).toFixed(1)}%
                </span>
              )}
            </div>
            <Progress value={winRate * 100} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-1">
              vs 50% baseline
            </p>
          </CardContent>
        </Card>

        {/* Learned Thresholds */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Adaptive Thresholds
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm">Buy:</span>
                <span className="font-mono font-bold text-green-500">
                  {modelState?.optimal_buy_threshold?.toFixed(1) || '4.0'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Sell:</span>
                <span className="font-mono font-bold text-red-500">
                  {modelState?.optimal_sell_threshold?.toFixed(1) || '-4.0'}
                </span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {isLearning ? 'Optimized from outcomes' : 'Using defaults'}
            </p>
          </CardContent>
        </Card>

        {/* Training Progress */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Training Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {modelState?.training_samples || 0}
            </div>
            <Progress
              value={Math.min(100, ((modelState?.training_samples || 0) / 100) * 100)}
              className="mt-2"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {(modelState?.training_samples || 0) < 20
                ? `Need ${20 - (modelState?.training_samples || 0)} more for learning`
                : `Model v${modelState?.model_version || 1} active`}
            </p>
          </CardContent>
        </Card>

        {/* Model Status */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Brain className="h-4 w-4" />
              Model Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {isLearning ? (
                <>
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span className="font-semibold text-green-500">Learning Active</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                  <span className="font-semibold text-yellow-500">Collecting Data</span>
                </>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {modelState?.last_trained
                ? `Last trained: ${new Date(modelState.last_trained).toLocaleDateString()}`
                : 'Not yet trained'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Time Optimization Heatmap */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Time-of-Day Optimization
          </CardTitle>
          <CardDescription>
            Win rates by trading hour (learned from your outcomes)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-1 justify-between">
            {Array.from({ length: 14 }, (_, i) => i + 8).map((hour) => {
              const isBest = modelState?.best_hours?.includes(hour);
              const isAvoid = modelState?.avoid_hours?.includes(hour);

              return (
                <div
                  key={hour}
                  className={cn(
                    "flex-1 h-16 rounded-lg flex flex-col items-center justify-center text-xs transition-all",
                    isBest && "bg-green-500/20 border border-green-500/40",
                    isAvoid && "bg-red-500/20 border border-red-500/40",
                    !isBest && !isAvoid && "bg-muted/50"
                  )}
                >
                  <span className="font-mono font-bold">
                    {hour > 12 ? hour - 12 : hour}
                    {hour >= 12 ? 'p' : 'a'}
                  </span>
                  {isBest && <TrendingUp className="h-3 w-3 text-green-500 mt-1" />}
                  {isAvoid && <TrendingDown className="h-3 w-3 text-red-500 mt-1" />}
                </div>
              );
            })}
          </div>
          <div className="flex justify-center gap-6 mt-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-green-500/30 border border-green-500/50" />
              Best Hours
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-red-500/30 border border-red-500/50" />
              Avoid
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-muted/50" />
              Neutral
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance History & Patterns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Daily Performance
            </CardTitle>
            <CardDescription>
              Win rate and P&L over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data?.daily_metrics && data.daily_metrics.length > 0 ? (
              <div className="space-y-2">
                {data.daily_metrics.slice(0, 7).map((metric, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                  >
                    <span className="text-sm font-mono">
                      {new Date(metric.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                    </span>
                    <div className="flex items-center gap-4">
                      <Badge variant={metric.win_rate >= 0.5 ? 'default' : 'destructive'}>
                        {(metric.win_rate * 100).toFixed(0)}%
                      </Badge>
                      <span className={cn(
                        "font-mono text-sm",
                        metric.pnl >= 0 ? "text-green-500" : "text-red-500"
                      )}>
                        {metric.pnl >= 0 ? '+' : ''}{metric.pnl?.toFixed(2) || '0.00'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {metric.signals} signals
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No performance data yet. Record signal outcomes to start tracking.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Patterns */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              Recognized Patterns
            </CardTitle>
            <CardDescription>
              Flow patterns with highest win rates
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data?.top_patterns && data.top_patterns.length > 0 ? (
              <div className="space-y-2">
                {data.top_patterns.slice(0, 5).map((pattern, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                  >
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        pattern.win_rate >= 0.7 ? "bg-green-500" :
                        pattern.win_rate >= 0.5 ? "bg-blue-500" : "bg-yellow-500"
                      )} />
                      <span className="text-sm font-medium">{pattern.name}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge variant={pattern.win_rate >= 0.6 ? 'default' : 'outline'}>
                        {(pattern.win_rate * 100).toFixed(0)}% WR
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {pattern.occurrences} trades
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No patterns recognized yet. ML will learn patterns as you record outcomes.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Correlation Signals */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            Cross-Ticker Correlation Signals
          </CardTitle>
          <CardDescription>
            High-conviction signals when multiple tickers align
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data?.recent_correlations && data.recent_correlations.length > 0 ? (
            <div className="space-y-2">
              {data.recent_correlations.slice(0, 5).map((signal, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg bg-gradient-to-r from-muted/30 to-transparent"
                >
                  <div className="flex items-center gap-3">
                    <Badge className={cn(
                      signal.direction === 'buy' ? 'bg-green-500' : 'bg-red-500'
                    )}>
                      {signal.direction.toUpperCase()}
                    </Badge>
                    <div className="flex gap-1">
                      {signal.tickers?.map((ticker: string) => (
                        <Badge key={ticker} variant="outline" className="text-xs">
                          {ticker}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge className={cn(
                      signal.conviction === 'extreme' ? 'bg-violet-500' :
                      signal.conviction === 'high' ? 'bg-blue-500' :
                      signal.conviction === 'medium' ? 'bg-yellow-500' : 'bg-gray-500'
                    )}>
                      {signal.conviction}
                    </Badge>
                    <span className="text-sm font-mono">
                      {signal.confidence?.toFixed(0)}% conf
                    </span>
                    {signal.profitable !== null && (
                      signal.profitable ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      )
                    )}
                    <span className="text-xs text-muted-foreground">
                      {signal.time ? new Date(signal.time).toLocaleTimeString() : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No correlation signals yet. These appear when multiple tickers align.
            </div>
          )}
        </CardContent>
      </Card>

      {/* How ML Learning Works */}
      <Card className="bg-gradient-to-br from-violet-500/5 to-purple-500/5 border-violet-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-violet-400" />
            How ML Learning Works
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 rounded-full bg-violet-500/20 flex items-center justify-center text-xs font-bold text-violet-400">1</div>
            <div><strong className="text-foreground">Signal Generated:</strong> SmartFlow creates buy/sell signal from flow data</div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 rounded-full bg-violet-500/20 flex items-center justify-center text-xs font-bold text-violet-400">2</div>
            <div><strong className="text-foreground">Trade Executed:</strong> Your system executes the trade through Tradeflow</div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 rounded-full bg-violet-500/20 flex items-center justify-center text-xs font-bold text-violet-400">3</div>
            <div><strong className="text-foreground">Outcome Recorded:</strong> When trade closes, P&L is recorded via webhook</div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 rounded-full bg-violet-500/20 flex items-center justify-center text-xs font-bold text-violet-400">4</div>
            <div><strong className="text-foreground">ML Learns:</strong> System updates win rates, patterns, optimal thresholds</div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center text-xs font-bold text-green-400">5</div>
            <div><strong className="text-foreground">Better Signals:</strong> Next signal uses learned knowledge for higher win rate</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
