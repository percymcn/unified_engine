"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Briefcase, TrendingUp, TrendingDown, X, Loader2, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface PositionAccountInfo {
  broker: string;
  account_name: string | null;
  account_id: number | null;
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
  const [closingPositionId, setClosingPositionId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const { toast } = useToast();

  const fetchPositions = async () => {
    try {
      const response = await fetch("/api/dashboard/positions", {
        credentials: "include",
      });
      if (response.ok) {
        const result = await response.json();
        setData(result);
      }
    } catch (error) {
      console.error("Error fetching positions:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchPositions, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchPositions();
  };

  const handleClosePosition = async (position: Position) => {
    if (!position.account.account_id) {
      toast({
        title: "Error",
        description: "Account ID not available for this position",
        variant: "destructive",
      });
      return;
    }

    setClosingPositionId(position.id);

    try {
      const response = await fetch("/api/dashboard/positions/close", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          position_id: position.id,
          account_id: position.account.account_id,
        }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: "Position Closed",
          description: `Successfully closed ${position.symbol} position`,
        });
        // Refresh positions after closing
        await fetchPositions();
      } else {
        toast({
          title: "Failed to Close",
          description: result.message || "Could not close position",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error closing position:", error);
      toast({
        title: "Error",
        description: "Failed to close position. Please try again.",
        variant: "destructive",
      });
    } finally {
      setClosingPositionId(null);
    }
  };

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
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Briefcase className="h-5 w-5 text-chart-2" />
              Open Positions
            </CardTitle>
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
          <div className="flex items-center gap-2">
            <Badge variant="outline">{data.total_positions} active</Badge>
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
      <CardContent className="space-y-3">
        {/* Position List */}
        {data.positions.slice(0, 5).map((position) => {
          const isProfitable = position.unrealized_pnl >= 0;
          const isClosing = closingPositionId === position.id;

          return (
            <div
              key={position.id}
              className="flex items-center justify-between py-1.5 border-b last:border-0 group"
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
              <div className="flex items-center gap-2">
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

                {/* Close Button with Confirmation */}
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                      disabled={isClosing}
                    >
                      {isClosing ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <X className="h-3 w-3" />
                      )}
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Close Position?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to close this position?
                        <div className="mt-4 p-3 bg-muted rounded-lg space-y-1">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Symbol:</span>
                            <span className="font-medium">{position.symbol}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Side:</span>
                            <span className="font-medium">{position.side}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Volume:</span>
                            <span className="font-medium">{position.volume.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">P&L:</span>
                            <span className={`font-medium ${isProfitable ? "text-green-600" : "text-red-600"}`}>
                              {formatPnL(position.unrealized_pnl)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Broker:</span>
                            <span className="font-medium capitalize">{position.account.broker}</span>
                          </div>
                        </div>
                        <p className="mt-3 text-sm text-amber-600 dark:text-amber-400">
                          This action cannot be undone. The position will be closed at market price.
                        </p>
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => handleClosePosition(position)}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        Close Position
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
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
