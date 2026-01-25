"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Clock, ArrowRight, RefreshCw, Sparkles } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";
import { cn } from "@/lib/utils";
import confetti from "canvas-confetti";

interface ExecutionAccountInfo {
  broker: string;
  account_id: number | null;
}

interface Execution {
  id: number;
  signal_id: string | null;
  account: ExecutionAccountInfo;
  symbol: string;
  action: string;
  volume: number;
  price: number | null;
  status: string;
  guard_reason?: string | null;
  execution_time_ms: number | null;
  created_at: string;
}

const POLL_INTERVAL = 15000; // 15 seconds

// Fire celebratory confetti for successful trades
function fireConfetti() {
  const count = 100;
  const defaults = {
    origin: { y: 0.7 },
    zIndex: 9999,
  };

  function fire(particleRatio: number, opts: confetti.Options) {
    confetti({
      ...defaults,
      ...opts,
      particleCount: Math.floor(count * particleRatio),
    });
  }

  fire(0.25, { spread: 26, startVelocity: 55, colors: ["#10b981", "#22c55e"] });
  fire(0.2, { spread: 60, colors: ["#3b82f6", "#6366f1"] });
  fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8 });
  fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2 });
  fire(0.1, { spread: 120, startVelocity: 45 });
}

export function RecentExecutionsWidget() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPolling, setIsPolling] = useState(false);
  const [newIds, setNewIds] = useState<Set<number>>(new Set());
  const [showSparkle, setShowSparkle] = useState(false);
  const lastSuccessCount = useRef(0);

  const fetchExecutions = useCallback(async (isInitial = false) => {
    try {
      if (!isInitial) setIsPolling(true);
      const response = await fetch("/api/dashboard/executions?limit=10");
      if (response.ok) {
        const data = await response.json();
        const newExecutions = data.executions || [];

        // Detect new executions for highlight animation
        if (!isInitial && executions.length > 0) {
          const existingIds = new Set(executions.map((e: Execution) => e.id));
          const incoming = newExecutions.filter((e: Execution) => !existingIds.has(e.id));
          if (incoming.length > 0) {
            setNewIds(new Set(incoming.map((e: Execution) => e.id)));

            // Fire confetti for successful new executions
            const successfulNew = incoming.filter((e: Execution) => e.status === "success");
            if (successfulNew.length > 0) {
              fireConfetti();
              setShowSparkle(true);
              setTimeout(() => setShowSparkle(false), 2000);
            }

            // Clear highlights after 3 seconds
            setTimeout(() => setNewIds(new Set()), 3000);
          }
        }

        setExecutions(newExecutions);
      }
    } catch (error) {
      console.error("Error fetching executions:", error);
    } finally {
      setLoading(false);
      setIsPolling(false);
    }
  }, [executions]);

  // Initial fetch + polling
  useEffect(() => {
    fetchExecutions(true);

    const interval = setInterval(() => {
      fetchExecutions(false);
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5 text-primary" />
            Recent Executions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="h-4 bg-muted rounded w-20" />
                  <div className="h-3 bg-muted rounded w-16" />
                </div>
                <div className="h-5 bg-muted rounded w-14" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (executions.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5 text-primary" />
            Recent Executions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Activity className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No recent executions</p>
            <p className="text-xs text-muted-foreground mt-1">
              Trade executions will appear here
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="transition-shadow duration-300 hover:shadow-lg dark:hover:shadow-primary/5">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className={cn(
              "h-5 w-5 text-primary transition-transform",
              showSparkle && "animate-bounce"
            )} />
            Recent Executions
            {showSparkle && (
              <Sparkles className="h-4 w-4 text-yellow-500 animate-pulse" />
            )}
            {isPolling && !showSparkle && (
              <RefreshCw className="h-3 w-3 text-muted-foreground animate-spin" />
            )}
          </CardTitle>
          <Link
            href="/dashboard/trades"
            className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1"
          >
            View All
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {executions.map((execution) => (
          <div
            key={execution.id}
            className={cn(
              "flex items-center justify-between py-2 px-2 -mx-2 rounded-lg border-b last:border-0 transition-all duration-500",
              newIds.has(execution.id) && execution.status === "success"
                ? "bg-green-500/10 ring-2 ring-green-500/30 animate-pulse shadow-lg shadow-green-500/20"
                : newIds.has(execution.id)
                ? "bg-primary/10 ring-2 ring-primary/30 animate-pulse"
                : "hover:bg-muted/50"
            )}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{execution.symbol}</span>
                <Badge
                  variant="secondary"
                  className={
                    execution.action.toUpperCase().includes("BUY")
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : execution.action.toUpperCase().includes("CLOSE")
                      ? "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400"
                      : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                  }
                >
                  {execution.action.toUpperCase().includes("BUY")
                    ? "BUY"
                    : execution.action.toUpperCase().includes("CLOSE")
                    ? "CLOSE"
                    : "SELL"}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {execution.volume.toFixed(2)}
                </span>
                {newIds.has(execution.id) && (
                  <Badge variant="default" className="text-xs bg-primary">
                    NEW
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
                <Clock className="h-3 w-3" />
                {formatDistanceToNow(new Date(execution.created_at), {
                  addSuffix: true,
                })}
                <span className="mx-1">-</span>
                <span className="capitalize">{execution.account.broker}</span>
                {execution.guard_reason && (
                  <>
                    <span className="mx-1">-</span>
                    <span className="text-amber-600 dark:text-amber-400">
                      {execution.guard_reason}
                    </span>
                  </>
                )}
              </div>
            </div>
            <Badge
              variant="outline"
              className={
                execution.status === "success"
                  ? "border-green-500 text-green-600"
                  : execution.status === "failed"
                  ? "border-red-500 text-red-600"
                  : execution.status === "skipped"
                  ? "border-gray-500 text-gray-600"
                  : "border-amber-500 text-amber-600"
              }
            >
              {execution.status}
            </Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
