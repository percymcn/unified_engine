"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Activity,
  Zap,
  BarChart3,
  Target,
  Shield,
  ArrowRight,
  Sparkles,
  Radio,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

/**
 * SmartFlow AI Indicator Showcase
 *
 * Premium section highlighting the revolutionary AI-powered options flow
 * analysis system that generates high-confidence trading signals.
 *
 * Features:
 * - Live FSS (Flow Sentiment Score) visualization
 * - Real-time signal generation animation
 * - Glassmorphism cards with micro-interactions
 * - Animated flow data representation
 */

// Simulated live flow data
function useFlowData() {
  const [flows, setFlows] = useState<Array<{
    ticker: string;
    type: "CALL" | "PUT";
    premium: string;
    sentiment: "Bullish" | "Bearish";
    size: "Large" | "Medium" | "Sweep";
  }>>([]);

  useEffect(() => {
    const tickers = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA", "AMD", "META", "GOOGL"];
    const sizes = ["Large", "Medium", "Sweep"] as const;

    const generateFlow = () => {
      const type = Math.random() > 0.5 ? "CALL" : "PUT";
      return {
        ticker: tickers[Math.floor(Math.random() * tickers.length)],
        type,
        premium: `$${(Math.random() * 500 + 50).toFixed(0)}K`,
        sentiment: type === "CALL" ? "Bullish" : "Bearish" as const,
        size: sizes[Math.floor(Math.random() * sizes.length)],
      };
    };

    // Initialize with some flows
    setFlows([generateFlow(), generateFlow(), generateFlow()]);

    const interval = setInterval(() => {
      setFlows(prev => [generateFlow(), ...prev.slice(0, 4)]);
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  return flows;
}

// Animated FSS Score gauge
function FSSGauge({ score }: { score: number }) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const duration = 2000;
    const steps = 60;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      const progress = step / steps;
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(score * easeOut);

      if (step >= steps) {
        setAnimatedScore(score);
        clearInterval(timer);
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [score]);

  const isPositive = animatedScore >= 0;
  const absScore = Math.abs(animatedScore);
  const percentage = (absScore / 100) * 100;

  return (
    <div className="relative w-40 h-40">
      {/* Background ring */}
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="80"
          cy="80"
          r="70"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-muted/30"
        />
        {/* Progress ring */}
        <motion.circle
          cx="80"
          cy="80"
          r="70"
          stroke={isPositive ? "#22c55e" : "#ef4444"}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          initial={{ strokeDasharray: "0 440" }}
          animate={{ strokeDasharray: `${percentage * 4.4} 440` }}
          transition={{ duration: 2, ease: "easeOut" }}
        />
      </svg>
      {/* Score display */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl font-bold ${isPositive ? "text-green-400" : "text-red-400"}`}>
          {isPositive ? "+" : ""}{Math.round(animatedScore)}
        </span>
        <span className="text-xs text-muted-foreground">FSS Score</span>
      </div>
    </div>
  );
}

// Live flow feed component
function FlowFeed() {
  const flows = useFlowData();

  return (
    <div className="space-y-2">
      <AnimatePresence mode="popLayout">
        {flows.map((flow, i) => (
          <motion.div
            key={`${flow.ticker}-${flow.premium}-${i}`}
            initial={{ opacity: 0, x: -20, height: 0 }}
            animate={{ opacity: 1, x: 0, height: "auto" }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.3 }}
            className={`flex items-center justify-between p-3 rounded-lg backdrop-blur-sm border ${
              flow.type === "CALL"
                ? "bg-green-500/10 border-green-500/20"
                : "bg-red-500/10 border-red-500/20"
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                flow.type === "CALL" ? "bg-green-500/20" : "bg-red-500/20"
              }`}>
                {flow.type === "CALL" ? (
                  <TrendingUp className="w-4 h-4 text-green-400" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-red-400" />
                )}
              </div>
              <div>
                <div className="font-semibold text-sm">{flow.ticker}</div>
                <div className="text-xs text-muted-foreground">{flow.size} {flow.type}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="font-mono text-sm">{flow.premium}</div>
              <div className={`text-xs ${flow.sentiment === "Bullish" ? "text-green-400" : "text-red-400"}`}>
                {flow.sentiment}
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// Feature highlight card
function FeatureHighlight({
  icon: Icon,
  title,
  description,
  gradient,
  delay,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  gradient: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ scale: 1.02, y: -2 }}
      className={`p-5 rounded-2xl bg-gradient-to-br ${gradient} backdrop-blur-sm border border-white/10 hover:border-white/20 transition-all duration-300`}
    >
      <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center mb-3">
        <Icon className="w-5 h-5" />
      </div>
      <h4 className="font-semibold mb-1">{title}</h4>
      <p className="text-sm text-muted-foreground">{description}</p>
    </motion.div>
  );
}

// Supported instruments display
function SupportedInstruments() {
  const instruments = [
    { symbol: "MES", name: "Micro E-mini S&P", type: "Futures" },
    { symbol: "MNQ", name: "Micro E-mini Nasdaq", type: "Futures" },
    { symbol: "MYM", name: "Micro E-mini Dow", type: "Futures" },
    { symbol: "M2K", name: "Micro E-mini Russell", type: "Futures" },
    { symbol: "MGC", name: "Micro Gold", type: "Futures" },
    { symbol: "ES", name: "E-mini S&P 500", type: "Futures" },
    { symbol: "NQ", name: "E-mini Nasdaq", type: "Futures" },
    { symbol: "GC", name: "Gold Futures", type: "Futures" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {instruments.map((inst, i) => (
        <motion.div
          key={inst.symbol}
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.3, delay: i * 0.05 }}
          className="flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/10 hover:border-primary/30 transition-colors"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
            <span className="text-xs font-mono font-bold text-primary">{inst.symbol}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium truncate">{inst.name}</div>
            <div className="text-[10px] text-muted-foreground">{inst.type}</div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

export function SmartFlowShowcase() {
  const sectionRef = useRef<HTMLElement>(null);
  const isInView = useInView(sectionRef, { once: true, margin: "-100px" });
  const [fssScore] = useState(68);

  return (
    <section
      ref={sectionRef}
      id="smartflow"
      className="py-24 relative overflow-hidden"
    >
      {/* Background gradient */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto px-4">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-purple-500/10 to-violet-500/10 border border-purple-500/20 backdrop-blur-sm mb-6">
            <Brain className="h-4 w-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-400">AI-Powered Trading</span>
          </div>

          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            SmartFlow AI{" "}
            <span className="bg-gradient-to-r from-green-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              Indicator
            </span>
          </h2>

          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Real-time options flow analysis powered by AI. Get institutional-grade signals
            based on unusual options activity across SPY, QQQ, GLD, IWM, and DIA.
          </p>
        </motion.div>

        {/* Main content grid */}
        <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
          {/* Left side - Live visualization */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative"
          >
            <div className="p-6 rounded-3xl bg-gradient-to-br from-background/80 to-background/40 backdrop-blur-xl border border-white/10 shadow-2xl">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Radio className="w-4 h-4 text-green-400 animate-pulse" />
                  <span className="text-sm font-medium">Live Flow Analysis</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-xs text-green-400">Connected</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                {/* FSS Gauge */}
                <div className="flex flex-col items-center">
                  <FSSGauge score={fssScore} />
                  <div className="mt-4 text-center">
                    <div className="text-sm font-medium text-green-400">Bullish Signal</div>
                    <div className="text-xs text-muted-foreground">High Confidence</div>
                  </div>
                </div>

                {/* Flow feed */}
                <div>
                  <div className="text-xs text-muted-foreground mb-2">Recent Unusual Activity</div>
                  <FlowFeed />
                </div>
              </div>

              {/* Signal action */}
              <div className="mt-6 p-4 rounded-xl bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
                      <Target className="w-5 h-5 text-green-400" />
                    </div>
                    <div>
                      <div className="font-semibold text-green-400">Signal Generated</div>
                      <div className="text-xs text-muted-foreground">BUY MES @ Market</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono text-green-400">+68 FSS</div>
                    <div className="text-xs text-muted-foreground">68% Confidence</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Floating accent card */}
            <motion.div
              className="absolute -bottom-4 -left-4 p-4 rounded-2xl bg-gradient-to-br from-background/80 to-background/40 backdrop-blur-xl border border-white/10 shadow-xl"
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            >
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-cyan-400" />
                <div>
                  <div className="text-sm font-bold">24/7 Monitoring</div>
                  <div className="text-xs text-muted-foreground">All Market Sessions</div>
                </div>
              </div>
            </motion.div>
          </motion.div>

          {/* Right side - Features */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="space-y-6"
          >
            <h3 className="text-2xl font-bold">
              Institutional-Grade Flow Analysis
            </h3>
            <p className="text-muted-foreground">
              SmartFlow aggregates and analyzes millions of options trades in real-time,
              identifying unusual activity patterns that signal institutional moves.
              Our AI calculates a Flow Sentiment Score (FSS) to generate high-probability
              trading signals.
            </p>

            <div className="grid grid-cols-2 gap-4">
              <FeatureHighlight
                icon={Brain}
                title="AI Analysis"
                description="Machine learning models analyze flow patterns"
                gradient="from-purple-500/20 to-violet-500/20"
                delay={0.4}
              />
              <FeatureHighlight
                icon={Zap}
                title="Real-Time"
                description="Sub-second signal generation from flow data"
                gradient="from-green-500/20 to-emerald-500/20"
                delay={0.5}
              />
              <FeatureHighlight
                icon={BarChart3}
                title="Multi-Ticker"
                description="SPY, QQQ, GLD, IWM, DIA analysis"
                gradient="from-cyan-500/20 to-blue-500/20"
                delay={0.6}
              />
              <FeatureHighlight
                icon={Shield}
                title="Risk Filtered"
                description="Built-in confidence thresholds"
                gradient="from-amber-500/20 to-orange-500/20"
                delay={0.7}
              />
            </div>

            <Button
              size="lg"
              asChild
              className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 shadow-lg shadow-green-500/25"
            >
              <Link href="/register">
                Start Using SmartFlow
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </motion.div>
        </div>

        {/* Supported instruments section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-center"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-6">
            <Sparkles className="h-3 w-3 text-primary" />
            <span className="text-xs text-muted-foreground">Supported Instruments</span>
          </div>

          <div className="max-w-3xl mx-auto">
            <SupportedInstruments />
          </div>

          <p className="text-sm text-muted-foreground mt-6">
            SmartFlow signals automatically map to your connected brokers - TradeLocker, ProjectX, Tradovate, and MetaTrader.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
