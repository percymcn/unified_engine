"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  BarChart3,
  Activity,
} from "lucide-react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { motion } from "framer-motion";

// Tradeable symbols on ProjectX/TopStep
const SYMBOLS = [
  { value: "MNQ", label: "MNQ - Micro Nasdaq" },
  { value: "MES", label: "MES - Micro S&P" },
  { value: "MYM", label: "MYM - Micro Dow" },
  { value: "M2K", label: "M2K - Micro Russell" },
  { value: "NQ", label: "NQ - E-mini Nasdaq" },
  { value: "ES", label: "ES - E-mini S&P" },
  { value: "MCL", label: "MCL - Micro Crude" },
  { value: "MGC", label: "MGC - Micro Gold" },
];

const INTERVALS = [
  { value: "1", label: "1m" },
  { value: "5", label: "5m" },
  { value: "15", label: "15m" },
  { value: "30", label: "30m" },
  { value: "60", label: "1h" },
];

interface BarData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Indicators {
  rsi?: number;
  macd?: number | { macd?: number; signal?: number; histogram?: number };
  macd_signal?: number;
  macd_histogram?: number;
  ema_20?: number;
  ema_50?: number;
  sma_20?: number;
  bb_upper?: number;
  bb_middle?: number;
  bb_lower?: number;
  atr?: number;
  current_price?: number;
  stoch_k?: number;
  stoch_d?: number;
  adx?: number;
}

interface ChartData extends BarData {
  time: string;
  color: string;
  body: [number, number];
  wick: [number, number];
}

export function LiveMarketChart() {
  const [symbol, setSymbol] = useState("MNQ");
  const [selectedInterval, setSelectedInterval] = useState("5");
  const [bars, setBars] = useState<ChartData[]>([]);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchChartData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // For demo, using mock data since we need account_id
      // In production, this would call /api/v1/market/chart/{symbol}
      const response = await fetch(
        `/api/market/chart?symbol=${symbol}&interval=${selectedInterval}&days=1`
      );

      if (!response.ok) {
        // Generate mock data for demo
        const mockBars = generateMockData(symbol, 100);
        setBars(mockBars);
        setIndicators(calculateMockIndicators(mockBars));
        setLastUpdate(new Date());
        return;
      }

      const data = await response.json();
      const chartBars = (data.bars || []).map((bar: BarData) => ({
        ...bar,
        time: formatTime(bar.timestamp),
        color: bar.close >= bar.open ? "#22c55e" : "#ef4444",
        body: [Math.min(bar.open, bar.close), Math.max(bar.open, bar.close)],
        wick: [bar.low, bar.high],
      }));

      setBars(chartBars);
      setIndicators(data.indicators || null);
      setLastUpdate(new Date());
    } catch (err) {
      console.error("Error fetching chart data:", err);
      // Use mock data on error
      const mockBars = generateMockData(symbol, 100);
      setBars(mockBars);
      setIndicators(calculateMockIndicators(mockBars));
      setLastUpdate(new Date());
    } finally {
      setLoading(false);
    }
  }, [symbol, selectedInterval]);

  useEffect(() => {
    fetchChartData();
    // Refresh every 30 seconds
    const timerId = window.setInterval(fetchChartData, 30000);
    return () => window.clearInterval(timerId);
  }, [fetchChartData]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  const formatPrice = (value: number) => {
    return value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const currentPrice = bars.length > 0 ? bars[bars.length - 1].close : 0;
  const prevPrice = bars.length > 1 ? bars[bars.length - 2].close : currentPrice;
  const priceChange = currentPrice - prevPrice;
  const priceChangePercent = prevPrice !== 0 ? (priceChange / prevPrice) * 100 : 0;
  const isPositive = priceChange >= 0;

  // Calculate chart domain
  const allPrices = bars.flatMap((b) => [b.high, b.low]);
  const minPrice = allPrices.length > 0 ? Math.min(...allPrices) : 0;
  const maxPrice = allPrices.length > 0 ? Math.max(...allPrices) : 0;
  const pricePadding = (maxPrice - minPrice) * 0.05 || 10;

  return (
    <Card className="glass glass-hover">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="h-5 w-5 text-primary" />
            Live Market
          </CardTitle>
          <div className="flex items-center gap-2">
            <Select value={symbol} onValueChange={setSymbol}>
              <SelectTrigger className="w-[140px] h-8 text-xs">
                <SelectValue placeholder="Symbol" />
              </SelectTrigger>
              <SelectContent>
                {SYMBOLS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedInterval} onValueChange={setSelectedInterval}>
              <SelectTrigger className="w-[70px] h-8 text-xs">
                <SelectValue placeholder="TF" />
              </SelectTrigger>
              <SelectContent>
                {INTERVALS.map((i) => (
                  <SelectItem key={i.value} value={i.value}>
                    {i.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={fetchChartData}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Price Display */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="text-2xl font-bold font-mono">
              {formatPrice(currentPrice)}
            </div>
            <Badge
              variant="outline"
              className={`flex items-center gap-1 ${
                isPositive
                  ? "border-green-500 text-green-600"
                  : "border-red-500 text-red-600"
              }`}
            >
              {isPositive ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {isPositive ? "+" : ""}
              {priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)
            </Badge>
          </div>
          {lastUpdate && (
            <span className="text-xs text-muted-foreground">
              Updated: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Indicators Row */}
        {indicators && (
          <div className="flex flex-wrap gap-2 mb-3 text-xs">
            {indicators.rsi !== undefined && (
              <Badge
                variant="secondary"
                className={
                  indicators.rsi > 70
                    ? "bg-red-500/20 text-red-500"
                    : indicators.rsi < 30
                    ? "bg-green-500/20 text-green-500"
                    : ""
                }
              >
                RSI: {indicators.rsi.toFixed(1)}
              </Badge>
            )}
            {indicators.macd !== undefined && (
              <Badge
                variant="secondary"
                className={
                  (typeof indicators.macd === 'number' ? indicators.macd : indicators.macd?.macd ?? 0) > 0
                    ? "bg-green-500/20 text-green-500"
                    : "bg-red-500/20 text-red-500"
                }
              >
                MACD: {(typeof indicators.macd === 'number' ? indicators.macd : indicators.macd?.macd ?? 0).toFixed(2)}
              </Badge>
            )}
            {indicators.ema_20 !== undefined && (
              <Badge variant="secondary">
                EMA20: {formatPrice(indicators.ema_20)}
              </Badge>
            )}
            {indicators.atr !== undefined && (
              <Badge variant="secondary">ATR: {indicators.atr.toFixed(2)}</Badge>
            )}
            {indicators.adx !== undefined && (
              <Badge
                variant="secondary"
                className={
                  indicators.adx > 25 ? "bg-blue-500/20 text-blue-500" : ""
                }
              >
                ADX: {indicators.adx.toFixed(1)}
              </Badge>
            )}
          </div>
        )}

        {/* Chart */}
        {loading ? (
          <div className="h-[250px] flex items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Loading chart...</span>
            </div>
          </div>
        ) : bars.length === 0 ? (
          <div className="h-[250px] flex items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <Activity className="h-8 w-8 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">No data available</span>
            </div>
          </div>
        ) : (
          <motion.div
            className="h-[250px] w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={100}>
              <ComposedChart
                data={bars.slice(-50)} // Last 50 bars
                margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  domain={[minPrice - pricePadding, maxPrice + pricePadding]}
                  tick={{ fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => v.toFixed(0)}
                  width={50}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                    fontSize: "11px",
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === "body") return null;
                    return [formatPrice(value), name.toUpperCase()];
                  }}
                  labelFormatter={(label) => `Time: ${label}`}
                />

                {/* EMA lines */}
                {indicators?.ema_20 && (
                  <ReferenceLine
                    y={indicators.ema_20}
                    stroke="#3b82f6"
                    strokeDasharray="3 3"
                    strokeWidth={1}
                  />
                )}

                {/* Bollinger Bands */}
                {indicators?.bb_upper && (
                  <ReferenceLine
                    y={indicators.bb_upper}
                    stroke="#8b5cf6"
                    strokeDasharray="5 5"
                    strokeWidth={1}
                  />
                )}
                {indicators?.bb_lower && (
                  <ReferenceLine
                    y={indicators.bb_lower}
                    stroke="#8b5cf6"
                    strokeDasharray="5 5"
                    strokeWidth={1}
                  />
                )}

                {/* Price bars (simplified candlestick as bars) */}
                <Bar
                  dataKey="close"
                  fill="currentColor"
                  radius={[2, 2, 0, 0]}
                  barSize={4}
                >
                  {bars.slice(-50).map((entry, index) => (
                    <rect
                      key={index}
                      fill={entry.color}
                    />
                  ))}
                </Bar>

                {/* High-Low line */}
                <Line
                  type="monotone"
                  dataKey="high"
                  stroke="#22c55e"
                  strokeWidth={1}
                  dot={false}
                  opacity={0.5}
                />
                <Line
                  type="monotone"
                  dataKey="low"
                  stroke="#ef4444"
                  strokeWidth={1}
                  dot={false}
                  opacity={0.5}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {/* Volume display */}
        {bars.length > 0 && (
          <div className="mt-2 text-xs text-muted-foreground text-center">
            Volume: {bars[bars.length - 1].volume.toLocaleString()} | Bars: {bars.length}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Mock data generator for demo
function generateMockData(symbol: string, count: number): ChartData[] {
  const basePrices: Record<string, number> = {
    MNQ: 21500,
    MES: 5200,
    MYM: 39000,
    M2K: 2050,
    NQ: 21500,
    ES: 5200,
    MCL: 75,
    MGC: 2050,
  };

  const basePrice = basePrices[symbol] || 5000;
  const now = new Date();
  const bars: ChartData[] = [];
  let price = basePrice;

  for (let i = count - 1; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 5 * 60 * 1000);
    const change = (Math.random() - 0.5) * basePrice * 0.002;
    const open = price;
    price = price + change;
    const close = price;
    const high = Math.max(open, close) + Math.random() * basePrice * 0.001;
    const low = Math.min(open, close) - Math.random() * basePrice * 0.001;
    const volume = Math.floor(Math.random() * 5000) + 1000;

    bars.push({
      timestamp: time.toISOString(),
      time: time.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }),
      open,
      high,
      low,
      close,
      volume,
      color: close >= open ? "#22c55e" : "#ef4444",
      body: [Math.min(open, close), Math.max(open, close)],
      wick: [low, high],
    });
  }

  return bars;
}

function calculateMockIndicators(bars: ChartData[]): Indicators {
  if (bars.length === 0) return {};

  const closes = bars.map((b) => b.close);
  const lastClose = closes[closes.length - 1];

  // Simple RSI calculation
  let gains = 0;
  let losses = 0;
  const period = Math.min(14, closes.length - 1);

  for (let i = closes.length - period; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    if (change > 0) gains += change;
    else losses -= change;
  }

  const avgGain = gains / period;
  const avgLoss = losses / period;
  const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  const rsi = 100 - 100 / (1 + rs);

  // Simple EMA
  const ema20 =
    closes.slice(-20).reduce((a, b) => a + b, 0) / Math.min(20, closes.length);

  // Simple ATR
  const highs = bars.map((b) => b.high);
  const lows = bars.map((b) => b.low);
  let atrSum = 0;
  for (let i = bars.length - 14; i < bars.length; i++) {
    if (i > 0) {
      const tr = Math.max(
        highs[i] - lows[i],
        Math.abs(highs[i] - closes[i - 1]),
        Math.abs(lows[i] - closes[i - 1])
      );
      atrSum += tr;
    }
  }
  const atr = atrSum / 14;

  return {
    rsi: Math.max(0, Math.min(100, rsi)),
    macd: (Math.random() - 0.5) * 10,
    ema_20: ema20,
    atr: atr,
    adx: 15 + Math.random() * 30,
    current_price: lastClose,
    bb_upper: ema20 + atr * 2,
    bb_lower: ema20 - atr * 2,
    bb_middle: ema20,
  };
}
