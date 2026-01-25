"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface RejectedSignal {
  id: number;
  account_id: number;
  symbol: string;
  action: string;
  reason: string;
  reason_detail: string;
  created_at: string;
}

const reasonColors: Record<string, string> = {
  daily_limit: "bg-orange-100 text-orange-800",
  concurrent_limit: "bg-yellow-100 text-yellow-800",
  symbol_limit: "bg-blue-100 text-blue-800",
  cooldown: "bg-gray-100 text-gray-800",
  daily_loss: "bg-red-100 text-red-800",
  drawdown: "bg-red-100 text-red-800",
  risk_reward: "bg-purple-100 text-purple-800",
};

export function RejectedSignalsWidget() {
  const [signals, setSignals] = useState<RejectedSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      try {
        const res = await window.fetch("/api/v1/risk/rejected-signals?limit=5");
        if (res.ok) {
          const data = await res.json();
          setSignals(data.signals || []);
        }
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  if (loading) {
    return (
      <Card className="glass glass-hover">
        <CardHeader>
          <CardTitle>Rejected Signals</CardTitle>
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

  if (signals.length === 0) {
    return (
      <Card className="glass glass-hover">
        <CardHeader>
          <CardTitle className="text-lg">Rejected Signals</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-4">
            No rejected signals today
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass glass-hover">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Rejected Signals</CardTitle>
          <Badge variant="outline">{signals.length} today</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {signals.map((signal) => (
          <div key={signal.id} className="flex items-start gap-3 text-sm">
            <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium">{signal.symbol}</span>
                <Badge variant="secondary" className="text-xs">
                  {signal.action}
                </Badge>
                <Badge className={`text-xs ${reasonColors[signal.reason] || "bg-gray-100"}`}>
                  {signal.reason.replace("_", " ")}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground truncate mt-1">
                {signal.reason_detail}
              </p>
              <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                <Clock className="h-3 w-3" />
                {formatDistanceToNow(new Date(signal.created_at), { addSuffix: true })}
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
