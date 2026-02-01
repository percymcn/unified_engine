"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AccountRiskSummary {
  account_id: number;
  account_name: string;
  broker: string;
  daily_trades: { current: number; limit: number | null; usage_pct: number };
  open_positions: { current: number; limit: number | null; usage_pct: number };
  drawdown: { current: number; limit: number | null; usage_pct: number };
  is_at_limit: boolean;
  is_halted: boolean;
}

interface RiskSummary {
  total_accounts: number;
  accounts_at_limit: number;
  accounts_halted: number;
  accounts: AccountRiskSummary[];
}

export function RiskUsageWidget() {
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const res = await window.fetch("/api/v1/risk/dashboard-summary");
      if (res.ok) {
        setSummary(await res.json());
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  if (loading) {
    return (
      <Card className="glass glass-hover">
        <CardHeader>
          <CardTitle>Risk Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            <div className="h-4 bg-muted rounded w-3/4" />
            <div className="h-4 bg-muted rounded w-1/2" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!summary) return null;

  return (
    <Card className="glass glass-hover">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-lg">Risk Status</CardTitle>
          <div className="flex items-center gap-2">
            {summary.accounts_at_limit > 0 ? (
              <Badge variant="destructive" className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {summary.accounts_at_limit} at limit
              </Badge>
            ) : (
              <Badge variant="outline" className="flex items-center gap-1 text-green-600">
                <CheckCircle className="h-3 w-3" />
                All clear
              </Badge>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {summary.accounts.slice(0, 3).map((account) => (
          <div key={account.account_id} className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{account.account_name}</span>
              <span className="text-muted-foreground text-xs">{account.broker}</span>
            </div>

            {/* Daily Trades */}
            {account.daily_trades.limit && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Daily Trades</span>
                  <span>{account.daily_trades.current}/{account.daily_trades.limit}</span>
                </div>
                <Progress
                  value={account.daily_trades.usage_pct}
                  className={account.daily_trades.usage_pct >= 90 ? "bg-red-100" : ""}
                />
              </div>
            )}

            {/* Drawdown */}
            {account.drawdown.limit && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Drawdown</span>
                  <span>{account.drawdown.current.toFixed(1)}%/{account.drawdown.limit}%</span>
                </div>
                <Progress
                  value={account.drawdown.usage_pct}
                  className={account.drawdown.usage_pct >= 80 ? "bg-red-100" : ""}
                />
              </div>
            )}

            {account.is_halted && (
              <Badge variant="destructive" className="flex items-center gap-1">
                <XCircle className="h-3 w-3" />
                Trading Halted
              </Badge>
            )}
          </div>
        ))}

        {summary.accounts.length > 3 && (
          <p className="text-xs text-muted-foreground text-center">
            +{summary.accounts.length - 3} more accounts
          </p>
        )}
      </CardContent>
    </Card>
  );
}
