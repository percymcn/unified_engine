"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

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
        const response = await fetch(`/api/dashboard/equity?days=${timeRange}`);
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
      <Card className="col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5 text-chart-1" />
            Account Equity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="flex justify-between items-center">
              <div className="h-8 bg-muted rounded w-32" />
              <div className="h-6 bg-muted rounded w-16" />
            </div>
            <div className="h-[200px] bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!equityData || equityData.data.length === 0) {
    return (
      <Card className="col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5 text-chart-1" />
            Account Equity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <TrendingUp className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No equity history yet</p>
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
  const padding = (maxEquity - minEquity) * 0.1 || 100;

  return (
    <Card className="col-span-2">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5 text-chart-1" />
            Account Equity
          </CardTitle>
          <div className="flex items-center gap-2">
            {(["7", "30", "90"] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  timeRange === range
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted hover:bg-muted/80"
                }`}
              >
                {range}d
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Current Balance Display */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-2xl font-bold">
              {formatCurrency(equityData.current_equity)}
            </div>
            <div className="text-xs text-muted-foreground">
              Balance: {formatCurrency(equityData.current_balance)}
            </div>
          </div>
          {equityData.change_percent !== null && (
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
              {equityData.change_percent.toFixed(1)}%
            </Badge>
          )}
        </div>

        {/* Chart */}
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={equityData.data}
              margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
            >
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={isPositive ? "#22c55e" : "#ef4444"}
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor={isPositive ? "#22c55e" : "#ef4444"}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) =>
                  `$${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`
                }
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                domain={[minEquity - padding, maxEquity + padding]}
                width={50}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "6px",
                  fontSize: "12px",
                }}
                formatter={(value: number | string | Array<number | string> | undefined) => [formatCurrency(Number(value || 0)), "Equity"]}
                labelFormatter={(label) => formatDate(String(label))}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke={isPositive ? "#22c55e" : "#ef4444"}
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
