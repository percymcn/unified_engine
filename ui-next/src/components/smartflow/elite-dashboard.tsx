'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Legend
} from 'recharts';
import {
  Activity, TrendingUp, TrendingDown, AlertTriangle,
  Gauge, Target, Shield, Brain, Zap, BarChart3,
  Clock, DollarSign, Percent, RefreshCw, PlayCircle,
  PauseCircle, Settings, Download, ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
interface RegimeData {
  regime: string;
  probability: number;
  color: string;
}

interface RiskMetrics {
  currentDrawdown: number;
  maxDrawdown: number;
  cvar95: number;
  kellyFraction: number;
  activePositions: number;
  totalExposure: number;
  sectorExposure: Record<string, number>;
}

interface FeatureImportance {
  feature: string;
  importance: number;
  change: number;
  isCritical: boolean;
}

interface BacktestResult {
  sharpeRatio: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
  totalReturn: number;
  totalTrades: number;
  expectancy: number;
}

interface Trade {
  id: string;
  timestamp: string;
  ticker: string;
  direction: 'long' | 'short';
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  regime: string;
  isWinner: boolean;
}

interface EnsembleSignal {
  ticker: string;
  direction: 'long' | 'short' | 'neutral';
  probability: number;
  strength: number;
  sources: {
    name: string;
    agrees: boolean;
  }[];
}

// Color constants
const REGIME_COLORS: Record<string, string> = {
  'trending_up': '#22c55e',
  'trending_down': '#ef4444',
  'mean_reverting': '#3b82f6',
  'vol_expansion': '#f59e0b',
  'vol_contraction': '#8b5cf6',
  'chaotic': '#6b7280',
};

const CHART_COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

// Main Dashboard Component
export function EliteDashboard() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // State
  const [regimeData, setRegimeData] = useState<RegimeData[]>([]);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [featureImportance, setFeatureImportance] = useState<FeatureImportance[]>([]);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [recentTrades, setRecentTrades] = useState<Trade[]>([]);
  const [ensembleSignals, setEnsembleSignals] = useState<EnsembleSignal[]>([]);
  const [equityCurve, setEquityCurve] = useState<{ date: string; equity: number }[]>([]);
  const [drawdownHistory, setDrawdownHistory] = useState<{ date: string; drawdown: number }[]>([]);

  // Load data from API
  const loadData = useCallback(async () => {
    try {
      // Fetch overview data
      const overviewRes = await fetch('/api/v1/smartflow/elite/overview?days=90', {
        credentials: 'include',
      });

      if (overviewRes.ok) {
        const overview = await overviewRes.json();

        // Set regime data from API
        if (overview.regime?.probabilities) {
          const regimeLabels: Record<string, string> = {
            'trending_up': 'Trending Up',
            'trending_down': 'Trending Down',
            'mean_reverting': 'Mean Reverting',
            'vol_expansion': 'Vol Expansion',
            'vol_contraction': 'Vol Contraction',
            'chaotic': 'Chaotic',
          };

          setRegimeData(
            Object.entries(overview.regime.probabilities).map(([key, prob]) => ({
              regime: regimeLabels[key] || key,
              probability: prob as number,
              color: REGIME_COLORS[key] || '#6b7280',
            }))
          );
        }

        // Set risk metrics from API
        if (overview.risk) {
          setRiskMetrics({
            currentDrawdown: overview.risk.current_drawdown || 0,
            maxDrawdown: overview.risk.max_drawdown || 0,
            cvar95: overview.risk.cvar_95 || 0,
            kellyFraction: overview.risk.kelly_fraction || 0,
            activePositions: overview.risk.active_positions || 0,
            totalExposure: overview.risk.total_exposure_pct || 0,
            sectorExposure: overview.risk.sector_exposure || {},
          });
        }

        // Set feature importance from API
        if (overview.features?.length > 0) {
          setFeatureImportance(
            overview.features.map((f: { feature: string; importance: number; change: number; is_critical: boolean }) => ({
              feature: f.feature,
              importance: f.importance,
              change: f.change || 0,
              isCritical: f.is_critical || false,
            }))
          );
        }

        // Set backtest result from API performance
        if (overview.performance) {
          setBacktestResult({
            sharpeRatio: overview.performance.sharpe_ratio || 0,
            winRate: overview.performance.win_rate || 0,
            profitFactor: overview.performance.profit_factor || 0,
            maxDrawdown: overview.performance.max_drawdown || 0,
            totalReturn: (overview.performance.total_pnl / 25000) * 100 || 0,
            totalTrades: overview.performance.total_trades || 0,
            expectancy: overview.performance.expectancy || 0,
          });
        }
      }

      // Fetch equity curve
      const equityRes = await fetch('/api/v1/smartflow/elite/equity-curve?days=90', {
        credentials: 'include',
      });

      if (equityRes.ok) {
        const equityData = await equityRes.json();
        if (equityData.equity_curve) {
          setEquityCurve(equityData.equity_curve);
        }
        if (equityData.drawdown_history) {
          setDrawdownHistory(equityData.drawdown_history);
        }
      }

      // Fetch recent trades
      const tradesRes = await fetch('/api/v1/smartflow/elite/recent-trades?limit=10', {
        credentials: 'include',
      });

      if (tradesRes.ok) {
        const tradesData = await tradesRes.json();
        if (tradesData.trades) {
          setRecentTrades(tradesData.trades.map((t: {
            id: string;
            timestamp: string;
            ticker: string;
            direction: 'long' | 'short';
            entry_price: number;
            exit_price: number;
            pnl: number;
            regime: string;
            is_winner: boolean;
          }) => ({
            id: t.id,
            timestamp: t.timestamp,
            ticker: t.ticker,
            direction: t.direction,
            entryPrice: t.entry_price,
            exitPrice: t.exit_price,
            pnl: t.pnl,
            regime: t.regime,
            isWinner: t.is_winner,
          })));
        }
      }

      // Default ensemble signals (would come from ensemble scoring service)
      setEnsembleSignals([
        {
          ticker: 'MES',
          direction: 'long',
          probability: 0.72,
          strength: 68,
          sources: [
            { name: 'Flow', agrees: true },
            { name: 'Regime', agrees: true },
            { name: 'TA', agrees: true },
            { name: 'ML', agrees: false },
          ]
        },
      ]);

    } catch (error) {
      console.error('Error loading dashboard data:', error);

      // Fallback to mock data if API fails
      setRegimeData([
        { regime: 'Trending Up', probability: 0.35, color: REGIME_COLORS['trending_up'] },
        { regime: 'Mean Reverting', probability: 0.25, color: REGIME_COLORS['mean_reverting'] },
        { regime: 'Vol Contraction', probability: 0.20, color: REGIME_COLORS['vol_contraction'] },
        { regime: 'Trending Down', probability: 0.10, color: REGIME_COLORS['trending_down'] },
        { regime: 'Vol Expansion', probability: 0.07, color: REGIME_COLORS['vol_expansion'] },
        { regime: 'Chaotic', probability: 0.03, color: REGIME_COLORS['chaotic'] },
      ]);

      setRiskMetrics({
        currentDrawdown: 3.2,
        maxDrawdown: 8.5,
        cvar95: 4.1,
        kellyFraction: 0.12,
        activePositions: 2,
        totalExposure: 15.0,
        sectorExposure: { 'equity_index': 10.0, 'metals': 5.0 },
      });

      setFeatureImportance([
        { feature: 'bb_position', importance: 0.18, change: -0.02, isCritical: true },
        { feature: 'flow_conviction', importance: 0.15, change: 0.01, isCritical: true },
        { feature: 'adx', importance: 0.12, change: 0.00, isCritical: true },
        { feature: 'rsi', importance: 0.10, change: -0.01, isCritical: false },
      ]);

      setBacktestResult({
        sharpeRatio: 1.45,
        winRate: 58.3,
        profitFactor: 1.72,
        maxDrawdown: 8.5,
        totalReturn: 24.6,
        totalTrades: 127,
        expectancy: 42.50,
      });

      // Generate mock equity curve
      const dates = Array.from({ length: 90 }, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (89 - i));
        return d.toISOString().split('T')[0];
      });
      let equity = 25000;
      setEquityCurve(dates.map(date => {
        equity += (Math.random() - 0.45) * 500;
        return { date, equity: Math.round(equity) };
      }));

    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setTimeout(() => setRefreshing(false), 500);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6 text-yellow-500" />
            SmartFlow Elite Dashboard
          </h2>
          <p className="text-muted-foreground">
            Real-time regime detection, risk analytics, and performance metrics
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard
          title="Sharpe Ratio"
          value={backtestResult?.sharpeRatio.toFixed(2) || '0'}
          icon={<TrendingUp className="h-4 w-4" />}
          trend={backtestResult && backtestResult.sharpeRatio > 1.0 ? 'up' : 'down'}
          subtitle="Target: >1.3"
        />
        <StatCard
          title="Win Rate"
          value={`${backtestResult?.winRate.toFixed(1)}%`}
          icon={<Target className="h-4 w-4" />}
          trend={backtestResult && backtestResult.winRate > 55 ? 'up' : 'neutral'}
          subtitle="Target: >55%"
        />
        <StatCard
          title="Profit Factor"
          value={backtestResult?.profitFactor.toFixed(2) || '0'}
          icon={<DollarSign className="h-4 w-4" />}
          trend={backtestResult && backtestResult.profitFactor > 1.5 ? 'up' : 'down'}
          subtitle="Target: >1.65"
        />
        <StatCard
          title="Max Drawdown"
          value={`${riskMetrics?.maxDrawdown.toFixed(1)}%`}
          icon={<TrendingDown className="h-4 w-4" />}
          trend={riskMetrics && riskMetrics.maxDrawdown < 10 ? 'up' : 'down'}
          subtitle="Limit: <12%"
        />
        <StatCard
          title="CVaR (95%)"
          value={`${riskMetrics?.cvar95.toFixed(1)}%`}
          icon={<Shield className="h-4 w-4" />}
          trend={riskMetrics && riskMetrics.cvar95 < 5 ? 'up' : 'neutral'}
          subtitle="Daily tail risk"
        />
        <StatCard
          title="Expectancy"
          value={`$${backtestResult?.expectancy.toFixed(0)}`}
          icon={<Gauge className="h-4 w-4" />}
          trend={backtestResult && backtestResult.expectancy > 0 ? 'up' : 'down'}
          subtitle="Per trade"
        />
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5 lg:w-auto lg:inline-grid">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="regime">Regime</TabsTrigger>
          <TabsTrigger value="risk">Risk</TabsTrigger>
          <TabsTrigger value="features">Features</TabsTrigger>
          <TabsTrigger value="trades">Trades</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Equity Curve */}
            <Card>
              <CardHeader>
                <CardTitle>Equity Curve</CardTitle>
                <CardDescription>Portfolio value over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityCurve}>
                      <defs>
                        <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                      <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                      <Tooltip formatter={(v: number) => [`$${v.toLocaleString()}`, 'Equity']} />
                      <Area type="monotone" dataKey="equity" stroke="#22c55e" fill="url(#equityGradient)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Drawdown Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Drawdown</CardTitle>
                <CardDescription>Peak to trough decline</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={drawdownHistory}>
                      <defs>
                        <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                      <YAxis tick={{ fontSize: 10 }} domain={[0, 'auto']} reversed />
                      <Tooltip formatter={(v: number) => [`${v.toFixed(2)}%`, 'Drawdown']} />
                      <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fill="url(#ddGradient)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Ensemble Signals */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  Ensemble Signals
                </CardTitle>
                <CardDescription>Multi-source signal agreement</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {ensembleSignals.map((signal, idx) => (
                    <div key={idx} className="p-4 rounded-lg border bg-muted/30">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-lg">{signal.ticker}</span>
                          <Badge className={cn(
                            signal.direction === 'long' ? 'bg-green-500' :
                            signal.direction === 'short' ? 'bg-red-500' : 'bg-gray-500'
                          )}>
                            {signal.direction.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold">{(signal.probability * 100).toFixed(0)}%</div>
                          <div className="text-xs text-muted-foreground">Confidence</div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {signal.sources.map((src, i) => (
                          <Badge key={i} variant={src.agrees ? 'default' : 'outline'} className={cn(
                            src.agrees ? 'bg-green-500/20 text-green-400' : 'text-muted-foreground'
                          )}>
                            {src.name}
                          </Badge>
                        ))}
                      </div>
                      <Progress value={signal.strength} className="mt-3 h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Regime Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Current Regime</CardTitle>
                <CardDescription>Market state probability distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={regimeData}
                        dataKey="probability"
                        nameKey="regime"
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        label={({ regime, probability }) => `${regime}: ${(probability * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {regimeData.map((entry, index) => (
                          <Cell key={index} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Regime Tab */}
        <TabsContent value="regime" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {regimeData.map((regime, idx) => (
              <Card key={idx}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full" style={{ backgroundColor: regime.color }} />
                      <span className="font-medium">{regime.regime}</span>
                    </div>
                    <span className="text-2xl font-bold">{(regime.probability * 100).toFixed(0)}%</span>
                  </div>
                  <Progress value={regime.probability * 100} className="h-3" style={{
                    '--progress-foreground': regime.color
                  } as React.CSSProperties} />
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Regime Performance</CardTitle>
              <CardDescription>Win rate and P&L by market regime</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    { regime: 'Trending Up', winRate: 65, pnl: 1250 },
                    { regime: 'Trending Down', winRate: 58, pnl: 420 },
                    { regime: 'Mean Reverting', winRate: 62, pnl: 890 },
                    { regime: 'Vol Expansion', winRate: 45, pnl: -180 },
                    { regime: 'Vol Contraction', winRate: 55, pnl: 320 },
                    { regime: 'Chaotic', winRate: 48, pnl: -95 },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                    <XAxis dataKey="regime" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="winRate" name="Win Rate %" fill="#22c55e" />
                    <Bar yAxisId="right" dataKey="pnl" name="P&L $" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Risk Tab */}
        <TabsContent value="risk" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-blue-500" />
                  Position Limits
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span>Active Positions</span>
                  <span className="font-bold">{riskMetrics?.activePositions} / 5</span>
                </div>
                <Progress value={(riskMetrics?.activePositions || 0) / 5 * 100} />

                <div className="flex justify-between items-center">
                  <span>Total Exposure</span>
                  <span className="font-bold">{riskMetrics?.totalExposure}%</span>
                </div>
                <Progress value={riskMetrics?.totalExposure || 0} className="h-2" />

                <div className="flex justify-between items-center">
                  <span>Kelly Fraction</span>
                  <span className="font-bold">{((riskMetrics?.kellyFraction || 0) * 100).toFixed(1)}%</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  Drawdown Monitor
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span>Current DD</span>
                    <span className={cn(
                      "font-bold",
                      (riskMetrics?.currentDrawdown || 0) > 5 ? 'text-red-500' : 'text-green-500'
                    )}>
                      {riskMetrics?.currentDrawdown.toFixed(1)}%
                    </span>
                  </div>
                  <Progress
                    value={(riskMetrics?.currentDrawdown || 0) / 15 * 100}
                    className="h-3"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-2">
                    <span>Max DD</span>
                    <span className="font-bold">{riskMetrics?.maxDrawdown.toFixed(1)}%</span>
                  </div>
                  <Progress value={(riskMetrics?.maxDrawdown || 0) / 15 * 100} className="h-3" />
                </div>

                <div className="pt-2 border-t">
                  <div className="text-sm text-muted-foreground">
                    Breakers: 5% warn, 10% reduce, 15% pause
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Gauge className="h-5 w-5 text-purple-500" />
                  CVaR / Expected Shortfall
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center">
                  <div className="text-4xl font-bold text-purple-500">
                    {riskMetrics?.cvar95.toFixed(1)}%
                  </div>
                  <div className="text-sm text-muted-foreground">CVaR 95%</div>
                </div>

                <div className="text-sm">
                  <p>Expected loss on worst 5% of days</p>
                  <p className="text-muted-foreground mt-2">
                    With $25k capital: -${((riskMetrics?.cvar95 || 0) / 100 * 25000).toFixed(0)} worst case
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sector Exposure */}
          <Card>
            <CardHeader>
              <CardTitle>Sector Exposure</CardTitle>
              <CardDescription>Position allocation by sector (max 50% per sector)</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(riskMetrics?.sectorExposure || {}).map(([sector, exposure]) => (
                  <div key={sector} className="p-4 rounded-lg bg-muted/30">
                    <div className="text-sm text-muted-foreground capitalize">{sector.replace('_', ' ')}</div>
                    <div className="text-2xl font-bold">{exposure}%</div>
                    <Progress value={exposure / 50 * 100} className="h-2 mt-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Feature Importance</CardTitle>
              <CardDescription>Model feature weights with trend indicators</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={featureImportance} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                    <XAxis type="number" domain={[0, 0.25]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                    <YAxis dataKey="feature" type="category" width={100} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
                    <Bar dataKey="importance" fill="#3b82f6">
                      {featureImportance.map((entry, index) => (
                        <Cell key={index} fill={entry.isCritical ? '#f59e0b' : '#3b82f6'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
                {featureImportance.map((f, idx) => (
                  <div key={idx} className={cn(
                    "p-2 rounded text-sm",
                    f.isCritical ? 'bg-yellow-500/10' : 'bg-muted/30'
                  )}>
                    <div className="flex justify-between">
                      <span className="font-medium">{f.feature}</span>
                      <span className={cn(
                        f.change > 0 ? 'text-green-500' :
                        f.change < 0 ? 'text-red-500' : 'text-muted-foreground'
                      )}>
                        {f.change > 0 ? '+' : ''}{(f.change * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Feature Radar</CardTitle>
              <CardDescription>Current feature strength visualization</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={featureImportance}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="feature" tick={{ fontSize: 10 }} />
                    <PolarRadiusAxis domain={[0, 0.2]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                    <Radar name="Importance" dataKey="importance" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.5} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trades Tab */}
        <TabsContent value="trades" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent Trades</CardTitle>
              <CardDescription>Latest executed trades with outcomes</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Time</th>
                      <th className="text-left p-2">Ticker</th>
                      <th className="text-left p-2">Direction</th>
                      <th className="text-right p-2">Entry</th>
                      <th className="text-right p-2">Exit</th>
                      <th className="text-right p-2">P&L</th>
                      <th className="text-left p-2">Regime</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentTrades.map((trade) => (
                      <tr key={trade.id} className="border-b hover:bg-muted/30">
                        <td className="p-2 text-muted-foreground">{trade.timestamp}</td>
                        <td className="p-2 font-medium">{trade.ticker}</td>
                        <td className="p-2">
                          <Badge className={trade.direction === 'long' ? 'bg-green-500' : 'bg-red-500'}>
                            {trade.direction.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="p-2 text-right">{trade.entryPrice.toFixed(2)}</td>
                        <td className="p-2 text-right">{trade.exitPrice.toFixed(2)}</td>
                        <td className={cn(
                          "p-2 text-right font-bold",
                          trade.isWinner ? 'text-green-500' : 'text-red-500'
                        )}>
                          {trade.pnl > 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                        </td>
                        <td className="p-2">
                          <Badge variant="outline" className="text-xs">
                            {trade.regime.replace('_', ' ')}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Trade Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-green-500">
                  ${backtestResult?.expectancy.toFixed(2) || 0}
                </div>
                <div className="text-sm text-muted-foreground">Avg Expectancy</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">
                  {backtestResult?.totalTrades || 0}
                </div>
                <div className="text-sm text-muted-foreground">Total Trades</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-green-500">
                  {backtestResult?.profitFactor.toFixed(2) || 0}
                </div>
                <div className="text-sm text-muted-foreground">Profit Factor</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">
                  {backtestResult?.winRate.toFixed(1) || 0}%
                </div>
                <div className="text-sm text-muted-foreground">Win Rate</div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Stat Card Component
function StatCard({
  title,
  value,
  icon,
  trend,
  subtitle
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  trend: 'up' | 'down' | 'neutral';
  subtitle?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-muted-foreground text-sm">{title}</span>
          <div className={cn(
            'p-1 rounded',
            trend === 'up' ? 'text-green-500 bg-green-500/10' :
            trend === 'down' ? 'text-red-500 bg-red-500/10' :
            'text-gray-500 bg-gray-500/10'
          )}>
            {icon}
          </div>
        </div>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
      </CardContent>
    </Card>
  );
}

export default EliteDashboard;
