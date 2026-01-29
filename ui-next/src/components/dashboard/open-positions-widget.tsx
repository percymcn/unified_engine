"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Briefcase, TrendingUp, TrendingDown } from "lucide-react";

interface PositionAccountInfo {
  broker: string;
  account_name: string | null;
}

interface Position {
  id: string;  // String to preserve large TradeLocker position IDs
  symbol: string;
  side: string;
  volume: number;
  unrealized_pnl: number;
  account: PositionAccountInfo;
}

interface PositionsResponse {
  positions: Position[];
  total_pnl: number;
  total_positions: number;
}

export function OpenPositionsWidget() {
  const [data, setData] = useState<PositionsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPositions() {
      try {
        const response = await fetch("/api/dashboard/positions");
        if (response.ok) {
          const result = await response.json();
          setData(result);
        }
      } catch (error) {
        console.error("Error fetching positions:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchPositions();
  }, []);

  const formatPnL = (value: number) => {
    const formatted = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: "always",
    }).format(value);
    return formatted;
  };

  if (loading) {
    return (
      <Card className="glass glass-hover">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Briefcase className="h-5 w-5 text-chart-2" />
            Open Positions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="h-4 bg-muted rounded w-16" />
                  <div className="h-3 bg-muted rounded w-24" />
                </div>
                <div className="h-5 bg-muted rounded w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.positions || data.positions.length === 0) {
    return (
      <Card className="glass glass-hover">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Briefcase className="h-5 w-5 text-chart-2" />
            Open Positions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6">
            <Briefcase className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No open positions</p>
            <p className="text-xs text-muted-foreground mt-1">
              Active trades will appear here
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const totalPnLPositive = data.total_pnl >= 0;

  return (
    <Card className="glass glass-hover">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Briefcase className="h-5 w-5 text-chart-2" />
            Open Positions
          </CardTitle>
          <Badge variant="outline">{data.total_positions} active</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Position List */}
        {data.positions.slice(0, 5).map((position) => {
          const isProfitable = position.unrealized_pnl >= 0;
          return (
            <div
              key={position.id}
              className="flex items-center justify-between py-1.5 border-b last:border-0"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{position.symbol}</span>
                  <Badge
                    variant="secondary"
                    className={
                      position.side === "Long"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                    }
                  >
                    {position.side}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {position.volume.toFixed(2)}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5 capitalize">
                  {position.account.account_name || position.account.broker}
                </div>
              </div>
              <div
                className={`flex items-center gap-1 text-sm font-medium ${
                  isProfitable ? "text-green-600" : "text-red-600"
                }`}
              >
                {isProfitable ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {formatPnL(position.unrealized_pnl)}
              </div>
            </div>
          );
        })}

        {/* Show more indicator */}
        {data.positions.length > 5 && (
          <p className="text-xs text-muted-foreground text-center">
            +{data.positions.length - 5} more positions
          </p>
        )}

        {/* Total P&L */}
        <div className="pt-2 border-t flex items-center justify-between">
          <span className="text-sm font-medium">Total P&L</span>
          <span
            className={`text-sm font-bold flex items-center gap-1 ${
              totalPnLPositive ? "text-green-600" : "text-red-600"
            }`}
          >
            {totalPnLPositive ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            {formatPnL(data.total_pnl)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
