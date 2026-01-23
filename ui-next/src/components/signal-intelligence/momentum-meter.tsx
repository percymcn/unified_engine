"use client";

import { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface SignalCounter {
  user_id: number;
  session_key: string;
  current_bias: string;
  opposite_momentum: number;
  last_signal_ts: string | null;
  last8_pattern: string | null;
  chop_mode: boolean;
  updated_at: string;
}

interface MomentumMeterProps {
  sessionKey: string;
  warnAt?: number;
}

export function MomentumMeter({ sessionKey, warnAt = 6 }: MomentumMeterProps) {
  const [counter, setCounter] = useState<SignalCounter | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCounter() {
      try {
        const res = await fetch(`/api/signal-intelligence/counters?session_key=${encodeURIComponent(sessionKey)}`);
        if (res.ok) {
          const data = await res.json();
          setCounter(data);
        }
      } catch (error) {
        console.error("Error fetching counter:", error);
      } finally {
        setLoading(false);
      }
    }

    if (sessionKey) {
      fetchCounter();
      // Refresh every 5 seconds
      const interval = setInterval(fetchCounter, 5000);
      return () => clearInterval(interval);
    }
  }, [sessionKey]);

  if (loading || !counter) {
    return null;
  }

  const momentum = counter.opposite_momentum;
  const progress = Math.min((momentum / warnAt) * 100, 100);
  
  // Color progression: green → amber → red
  let colorClass = "bg-green-500";
  if (progress >= 83) { // 5/6 threshold
    colorClass = "bg-red-500";
  } else if (progress >= 50) { // 3/6 threshold
    colorClass = "bg-amber-500";
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Momentum</span>
              <span className={progress >= 50 ? "font-medium text-amber-600" : ""}>
                {momentum}/{warnAt}
              </span>
            </div>
            <Progress
              value={progress}
              className={`h-2 ${colorClass}`}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span className="text-[10px]">Bias: {counter.current_bias}</span>
              {counter.chop_mode && (
                <span className="text-[10px] text-amber-600">Choppy</span>
              )}
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1 text-xs">
            <p>Opposite Momentum: {momentum}</p>
            <p>Current Bias: {counter.current_bias}</p>
            <p>Pattern: {counter.last8_pattern || "N/A"}</p>
            {counter.chop_mode && <p className="text-amber-500">Market is choppy</p>}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
