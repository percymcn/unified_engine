"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  ArrowRight,
  Zap,
  CheckCircle2,
  Activity,
  Server,
} from "lucide-react";

/**
 * TradeExecutionAnimation Component
 *
 * Visual animated demonstration showing:
 * 1. TradingView chart with signal
 * 2. Signal flowing to TradeFlow
 * 3. TradeFlow processing
 * 4. Signal flowing to broker
 * 5. Execution confirmation
 *
 * Uses framer-motion for smooth animations.
 * Mobile-friendly with fallback static state.
 */

interface AnimationState {
  phase: "idle" | "tradingview" | "signal-flow-1" | "tradeflow" | "signal-flow-2" | "broker" | "executed";
  cycle: number;
}

export function TradeExecutionAnimation() {
  const [state, setState] = useState<AnimationState>({
    phase: "idle",
    cycle: 0,
  });
  const [hasError, setHasError] = useState(false);

  // Animation sequence loop
  useEffect(() => {
    if (hasError) return;

    const sequence = [
      { phase: "tradingview" as const, duration: 1500 },
      { phase: "signal-flow-1" as const, duration: 800 },
      { phase: "tradeflow" as const, duration: 1200 },
      { phase: "signal-flow-2" as const, duration: 800 },
      { phase: "broker" as const, duration: 1000 },
      { phase: "executed" as const, duration: 1500 },
    ];

    let currentIndex = 0;
    let timeoutId: NodeJS.Timeout;

    const runSequence = () => {
      if (currentIndex >= sequence.length) {
        // Reset and loop
        currentIndex = 0;
        setState((prev) => ({ phase: "idle", cycle: prev.cycle + 1 }));
        timeoutId = setTimeout(runSequence, 500);
        return;
      }

      const step = sequence[currentIndex];
      setState((prev) => ({ ...prev, phase: step.phase }));

      timeoutId = setTimeout(() => {
        currentIndex++;
        runSequence();
      }, step.duration);
    };

    // Start after initial delay
    timeoutId = setTimeout(runSequence, 1000);

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [hasError, state.cycle]);

  // Fallback on error
  useEffect(() => {
    const timer = setTimeout(() => {
      if (state.phase === "idle" && state.cycle === 0) {
        // Animation didn't start, show fallback
        setHasError(true);
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [state.phase, state.cycle]);

  if (hasError) {
    // Static fallback
    return (
      <div className="relative aspect-video rounded-xl overflow-hidden bg-gradient-to-br from-primary/20 to-primary/5 border">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-8">
              <div className="text-center">
                <TrendingUp className="w-12 h-12 mx-auto mb-2 text-blue-400" />
                <p className="text-sm font-medium">TradingView</p>
              </div>
              <ArrowRight className="w-6 h-6 text-muted-foreground" />
              <div className="text-center">
                <Zap className="w-12 h-12 mx-auto mb-2 text-purple-400" />
                <p className="text-sm font-medium">TradeFlow</p>
              </div>
              <ArrowRight className="w-6 h-6 text-muted-foreground" />
              <div className="text-center">
                <Server className="w-12 h-12 mx-auto mb-2 text-green-400" />
                <p className="text-sm font-medium">Broker</p>
              </div>
            </div>
            <CheckCircle2 className="w-8 h-8 mx-auto text-green-500" />
            <p className="text-sm text-muted-foreground">Trade Executed</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative aspect-video rounded-xl overflow-hidden bg-gradient-to-br from-primary/20 to-primary/5 border">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#8882_1px,transparent_1px),linear-gradient(to_bottom,#8882_1px,transparent_1px)] bg-[size:1.5rem_1.5rem] opacity-20" />

      {/* Main content */}
      <div className="relative z-10 h-full flex flex-col items-center justify-center p-6 md:p-8">
        {/* Top row: TradingView Chart */}
        <div className="w-full mb-6 md:mb-8">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{
              opacity: state.phase !== "idle" ? 1 : 0.3,
              y: 0,
            }}
            className="bg-card/80 backdrop-blur-sm rounded-lg border p-4 md:p-6"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-400" />
                <span className="font-semibold text-sm md:text-base">TradingView</span>
              </div>
              {state.phase === "tradingview" && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="flex items-center gap-1 text-xs text-green-500"
                >
                  <Activity className="w-3 h-3" />
                  <span>Signal Alert</span>
                </motion.div>
              )}
            </div>

            {/* Simulated chart */}
            <div className="relative h-24 md:h-32 bg-muted/50 rounded overflow-hidden">
              {/* Chart line */}
              <svg className="w-full h-full" viewBox="0 0 200 100" preserveAspectRatio="none">
                <motion.polyline
                  points="0,80 30,70 60,50 90,40 120,35 150,30 180,25 200,20"
                  fill="none"
                  stroke="hsl(var(--primary))"
                  strokeWidth="2"
                  initial={{ pathLength: 0 }}
                  animate={{
                    pathLength: state.phase !== "idle" ? 1 : 0,
                  }}
                  transition={{ duration: 1 }}
                />
              </svg>

              {/* Signal indicator */}
              <AnimatePresence>
                {state.phase === "tradingview" && (
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 1.5, opacity: 0 }}
                    className="absolute top-2 right-2 md:top-4 md:right-4"
                  >
                    <div className="w-3 h-3 bg-green-500 rounded-full">
                      <motion.div
                        animate={{ scale: [1, 2, 1], opacity: [1, 0, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                        className="absolute inset-0 bg-green-500 rounded-full"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </div>

        {/* Middle row: Flow arrows and TradeFlow */}
        <div className="w-full flex items-center justify-center gap-4 md:gap-8 mb-6 md:mb-8">
          {/* Signal pulse arrow 1 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{
              opacity: state.phase === "signal-flow-1" ? 1 : 0,
              x: state.phase === "signal-flow-1" ? 0 : -20,
            }}
            className="flex items-center"
          >
            <motion.div
              animate={{
                x: state.phase === "signal-flow-1" ? [0, 40, 0] : 0,
              }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
              className="flex items-center gap-2"
            >
              <div className="w-2 h-2 rounded-full bg-primary" />
              <ArrowRight className="w-5 h-5 text-primary" />
            </motion.div>
          </motion.div>

          {/* TradeFlow processing */}
          <motion.div
            animate={{
              scale: state.phase === "tradeflow" ? [1, 1.05, 1] : 1,
              opacity: state.phase === "tradeflow" || state.phase === "signal-flow-2" || state.phase === "broker" || state.phase === "executed" ? 1 : 0.5,
            }}
            transition={{ duration: 0.3 }}
            className="bg-card/80 backdrop-blur-sm rounded-lg border px-4 md:px-6 py-3 md:py-4 flex items-center gap-3"
          >
            <Zap className="w-5 h-5 md:w-6 md:h-6 text-purple-400" />
            <div>
              <p className="font-semibold text-sm md:text-base">TradeFlow</p>
              <p className="text-xs text-muted-foreground">Processing...</p>
            </div>
            {state.phase === "tradeflow" && (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="ml-2"
              >
                <Activity className="w-4 h-4 text-purple-400" />
              </motion.div>
            )}
          </motion.div>

          {/* Signal pulse arrow 2 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{
              opacity: state.phase === "signal-flow-2" ? 1 : 0,
              x: state.phase === "signal-flow-2" ? 0 : -20,
            }}
            className="flex items-center"
          >
            <motion.div
              animate={{
                x: state.phase === "signal-flow-2" ? [0, 40, 0] : 0,
              }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
              className="flex items-center gap-2"
            >
              <div className="w-2 h-2 rounded-full bg-primary" />
              <ArrowRight className="w-5 h-5 text-primary" />
            </motion.div>
          </motion.div>
        </div>

        {/* Bottom row: Broker and execution */}
        <div className="w-full">
          <motion.div
            animate={{
              opacity: state.phase === "broker" || state.phase === "executed" ? 1 : 0.5,
              scale: state.phase === "broker" ? [1, 1.02, 1] : 1,
            }}
            transition={{ duration: 0.3 }}
            className="bg-card/80 backdrop-blur-sm rounded-lg border p-4 md:p-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Server className="w-5 h-5 md:w-6 md:h-6 text-green-400" />
                <div>
                  <p className="font-semibold text-sm md:text-base">Broker</p>
                  <p className="text-xs text-muted-foreground">TradeLocker / MT4 / MT5</p>
                </div>
              </div>

              <AnimatePresence>
                {state.phase === "executed" && (
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.8, opacity: 0 }}
                    className="flex items-center gap-2 text-green-500"
                  >
                    <CheckCircle2 className="w-5 h-5 md:w-6 md:h-6" />
                    <span className="text-sm md:text-base font-semibold">Executed</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </div>

        {/* Speed indicator */}
        <AnimatePresence>
          {state.phase === "executed" && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute bottom-4 left-1/2 -translate-x-1/2"
            >
              <div className="bg-green-500/20 border border-green-500/40 rounded-full px-4 py-2 flex items-center gap-2">
                <Zap className="w-4 h-4 text-green-400" />
                <span className="text-sm font-semibold text-green-400">&lt;50ms</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
