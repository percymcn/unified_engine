"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Activity, Sparkles } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { motion, AnimatePresence } from "framer-motion";

interface EquityDataPoint {
  date: string;
  equity: number;
  balance: number;
}

interface EquityResponse {
  data: EquityDataPoint[];
  current_equity: number;
  current_balance: number;
  change_percent: number | null;
}

type TimeRange = "7" | "30" | "90";

export function EquityChartWidget() {
  const [equityData, setEquityData] = useState<EquityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>("30");

  useEffect(() => {
    async function fetchEquity() {
      try {
        setLoading(true);
        const response = await fetch(`/api/dashboard/equity?days=${timeRange}`, {
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          setEquityData(data);
        }
      } catch (error) {
        console.error("Error fetching equity:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchEquity();
  }, [timeRange]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const isPositive =
    equityData?.change_percent !== null &&
    equityData?.change_percent !== undefined &&
    equityData.change_percent >= 0;

  if (loading) {
    return (
      <Card className="col-span-2 glass glass-hover relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5" />
        <CardHeader className="pb-2 relative z-10">
          <CardTitle className="flex items-center gap-2 text-lg">
            <div className="p-1.5 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20">
              <Activity className="h-4 w-4 text-primary animate-pulse" />
            </div>
            Account Equity
          </CardTitle>
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="animate-pulse space-y-3">
            <div className="flex justify-between items-center">
              <div className="h-8 bg-muted/50 rounded-lg w-32" />
              <div className="h-6 bg-muted/50 rounded-lg w-16" />
            </div>
            <div className="h-[220px] bg-gradient-to-b from-muted/30 to-transparent rounded-xl" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!equityData || equityData.data.length === 0) {
    return (
      <Card className="col-span-2 glass glass-hover relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5" />
        <CardHeader className="pb-2 relative z-10">
          <CardTitle className="flex items-center gap-2 text-lg">
            <div className="p-1.5 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20">
              <Activity className="h-4 w-4 text-primary" />
            </div>
            Account Equity
          </CardTitle>
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 rounded-full bg-gradient-to-br from-muted/50 to-muted/20 flex items-center justify-center mb-4">
              <TrendingUp className="h-8 w-8 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground font-medium">No equity history yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Connect an account and trade to see your equity chart
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate min/max for better chart scaling
  const equities = equityData.data.map((d) => d.equity);
  const minEquity = Math.min(...equities);
  const maxEquity = Math.max(...equities);
  const padding = (maxEquity - minEquity) * 0.15 || 100;
  const avgEquity = equities.reduce((a, b) => a + b, 0) / equities.length;

  // Primary color based on performance
  const primaryColor = isPositive ? "#10b981" : "#ef4444";
  const secondaryColor = isPositive ? "#34d399" : "#f87171";

  return (
    <Card className="col-span-2 glass glass-hover relative overflow-hidden group">
      {/* Animated background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 transition-opacity duration-500" />
      <div
        className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 ${
          isPositive
            ? 'bg-gradient-to-br from-green-500/5 via-transparent to-emerald-500/5'
            : 'bg-gradient-to-br from-red-500/5 via-transparent to-orange-500/5'
        }`}
      />

      {/* Subtle glow effect on hover */}
      <div
        className={`absolute -inset-1 opacity-0 group-hover:opacity-20 blur-2xl transition-all duration-700 ${
          isPositive ? 'bg-green-500' : 'bg-red-500'
        }`}
      />

      <CardHeader className="pb-2 relative z-10">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <motion.div
              className="p-1.5 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20"
              whileHover={{ scale: 1.1, rotate: 5 }}
              transition={{ type: "spring", stiffness: 400, damping: 17 }}
            >
              <Activity className="h-4 w-4 text-primary" />
            </motion.div>
            <span className="bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text">
              Account Equity
            </span>
          </CardTitle>

          {/* Time range selector with animated indicator */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/30 backdrop-blur-sm">
            {(["7", "30", "90"] as TimeRange[]).map((range) => (
              <motion.button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`relative px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  timeRange === range
                    ? "text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <AnimatePresence>
                  {timeRange === range && (
                    <motion.div
                      layoutId="activeTimeRange"
                      className="absolute inset-0 bg-gradient-to-r from-primary to-accent rounded-md"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ type: "spring", stiffness: 300, damping: 25 }}
                    />
                  )}
                </AnimatePresence>
                <span className="relative z-10">{range}d</span>
              </motion.button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative z-10">
        {/* Current Balance Display */}
        <div className="flex items-center justify-between mb-4">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-muted-foreground bg-clip-text">
                {formatCurrency(equityData.current_equity)}
              </span>
              <Sparkles className="h-4 w-4 text-primary/60" />
            </div>
            <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-muted-foreground/30" />
              Balance: {formatCurrency(equityData.current_balance)}
            </div>
          </motion.div>

          {equityData.change_percent !== null && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <Badge
                variant="outline"
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold backdrop-blur-sm ${
                  isPositive
                    ? "border-green-500/50 text-green-500 bg-green-500/10 shadow-lg shadow-green-500/10"
                    : "border-red-500/50 text-red-500 bg-red-500/10 shadow-lg shadow-red-500/10"
                }`}
              >
                <motion.div
                  animate={{ y: isPositive ? [0, -2, 0] : [0, 2, 0] }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                >
                  {isPositive ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                </motion.div>
                {isPositive ? "+" : ""}
                {equityData.change_percent.toFixed(2)}%
              </Badge>
            </motion.div>
          )}
        </div>

        {/* Chart */}
        <motion.div
          className="h-[220px] w-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={equityData.data}
              margin={{ top: 10, right: 10, left: 0, bottom: 5 }}
            >
              <defs>
                {/* Main gradient fill */}
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={primaryColor} stopOpacity={0.4} />
                  <stop offset="50%" stopColor={primaryColor} stopOpacity={0.1} />
                  <stop offset="100%" stopColor={primaryColor} stopOpacity={0} />
                </linearGradient>

                {/* Glow effect for the line */}
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>

                {/* Animated gradient for line */}
                <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={secondaryColor} />
                  <stop offset="50%" stopColor={primaryColor} />
                  <stop offset="100%" stopColor={secondaryColor} />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--muted-foreground))"
                opacity={0.1}
                vertical={false}
              />

              {/* Average line */}
              <ReferenceLine
                y={avgEquity}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="5 5"
                strokeOpacity={0.3}
              />

              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={{ stroke: "hsl(var(--border))", strokeOpacity: 0.3 }}
                tickLine={false}
                tickMargin={8}
              />
              <YAxis
                tickFormatter={(v) =>
                  `$${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`
                }
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                domain={[minEquity - padding, maxEquity + padding]}
                width={55}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card) / 0.95)",
                  backdropFilter: "blur(8px)",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "12px",
                  fontSize: "12px",
                  boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
                  padding: "12px 16px",
                }}
                cursor={{
                  stroke: "hsl(var(--primary))",
                  strokeWidth: 1,
                  strokeDasharray: "4 4"
                }}
                formatter={(value: number | string | Array<number | string> | undefined) => [
                  <span key="value" className="font-semibold">{formatCurrency(Number(value || 0))}</span>,
                  "Equity"
                ]}
                labelFormatter={(label) => (
                  <span className="text-muted-foreground text-xs">{formatDate(String(label))}</span>
                )}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="url(#lineGradient)"
                strokeWidth={2.5}
                fill="url(#equityGradient)"
                filter="url(#glow)"
                animationDuration={1000}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Chart legend */}
        <div className="flex items-center justify-center gap-6 mt-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-0.5 rounded-full"
              style={{ backgroundColor: primaryColor }}
            />
            <span>Equity</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 rounded-full bg-muted-foreground/30" style={{ backgroundImage: 'repeating-linear-gradient(90deg, currentColor 0, currentColor 3px, transparent 3px, transparent 6px)' }} />
            <span>Average</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
