"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { motion } from "framer-motion";

interface SignalHistoryEntry {
  symbol: string;
  action: string;
  created_at: string;
}

interface SignalResponse {
  created_at?: string;
  timestamp?: string;
  symbol?: string;
  action?: string;
}

interface HeatMapProps {
  symbol?: string; // Optional: filter by symbol
}

export function SignalHeatMap({ symbol }: HeatMapProps) {
  const [signals, setSignals] = useState<SignalHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSignals() {
      try {
        // Fetch last 24h signals from history
        const res = await fetch("/api/signals?limit=1000");
        if (res.ok) {
          const data = await res.json();
          const now = new Date();
          const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          
          const recentSignals = (data.signals || data || []).filter((s: SignalResponse) => {
            const signalDate = new Date(s.created_at || s.timestamp || '');
            return signalDate >= yesterday && (!symbol || s.symbol === symbol);
          });
          
          setSignals(recentSignals);
        }
      } catch (error) {
        console.error("Error fetching signals:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchSignals();
    // Refresh every 30 seconds
    const interval = setInterval(fetchSignals, 30000);
    return () => clearInterval(interval);
  }, [symbol]);

  if (loading) {
    return (
      <Card className="glass glass-hover">
        <CardHeader>
          <CardTitle className="text-sm">24h Signal Heat Map</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse h-32 bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  // Group by hour
  const hourlyData: Record<number, { buys: number; sells: number }> = {};
  for (let i = 0; i < 24; i++) {
    hourlyData[i] = { buys: 0, sells: 0 };
  }

  signals.forEach((signal) => {
    const hour = new Date(signal.created_at).getHours();
    if (signal.action.toLowerCase() === "buy") {
      hourlyData[hour].buys++;
    } else if (signal.action.toLowerCase() === "sell") {
      hourlyData[hour].sells++;
    }
  });

  const totalBuys = signals.filter(s => s.action.toLowerCase() === "buy").length;
  const totalSells = signals.filter(s => s.action.toLowerCase() === "sell").length;

  return (
    <Card className="glass glass-hover">
      <CardHeader>
        <CardTitle className="text-sm">24h Signal Heat Map</CardTitle>
      </CardHeader>
      <CardContent>
        <TooltipProvider>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Last 24 hours</span>
              <Tooltip>
                <TooltipTrigger>
                  <span className="font-medium">{totalBuys}/{totalSells}</span>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{totalBuys} buys / {totalSells} sells</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="grid grid-cols-12 gap-1">
              {Object.entries(hourlyData).slice(0, 12).map(([hour, data]) => {
                const intensity = Math.min((data.buys + data.sells) / 10, 1);
                const buyRatio = data.buys + data.sells > 0 ? data.buys / (data.buys + data.sells) : 0.5;
                
                // Green for buys, red for sells, mix for both
                const bgColor = buyRatio > 0.6 
                  ? `bg-green-500` 
                  : buyRatio < 0.4 
                  ? `bg-red-500` 
                  : `bg-amber-500`;
                
                return (
                  <Tooltip key={hour}>
                    <TooltipTrigger asChild>
                      <motion.div
                        className={`h-8 rounded ${bgColor}`}
                        style={{ opacity: 0.3 + intensity * 0.7 }}
                        whileHover={{ scale: 1.08 }}
                        transition={{ type: "spring", stiffness: 300, damping: 18 }}
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs">
                        {hour}:00 - {data.buys} buys, {data.sells} sells
                      </p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
            <div className="grid grid-cols-12 gap-1">
              {Object.entries(hourlyData).slice(12).map(([hour, data]) => {
                const intensity = Math.min((data.buys + data.sells) / 10, 1);
                const buyRatio = data.buys + data.sells > 0 ? data.buys / (data.buys + data.sells) : 0.5;
                
                const bgColor = buyRatio > 0.6 
                  ? `bg-green-500` 
                  : buyRatio < 0.4 
                  ? `bg-red-500` 
                  : `bg-amber-500`;
                
                return (
                  <Tooltip key={hour}>
                    <TooltipTrigger asChild>
                      <motion.div
                        className={`h-8 rounded ${bgColor}`}
                        style={{ opacity: 0.3 + intensity * 0.7 }}
                        whileHover={{ scale: 1.08 }}
                        transition={{ type: "spring", stiffness: 300, damping: 18 }}
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs">
                        {hour}:00 - {data.buys} buys, {data.sells} sells
                      </p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-green-500 rounded" />
                <span>Buy</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded" />
                <span>Sell</span>
              </div>
            </div>
          </div>
        </TooltipProvider>
      </CardContent>
    </Card>
  );
}
