"use client";

import { useRef, useState, useEffect } from "react";
import { motion, useInView } from "framer-motion";
import {
  Zap,
  Shield,
  Globe,
  ArrowRightLeft,
  BarChart3,
  Users,
  Sparkles,
  Brain,
  Clock,
  TrendingDown,
  RefreshCw,
  Target,
  Lock,
  Activity,
  LineChart,
  Newspaper,
  GitBranch,
  Pause,
  Scale,
  CalendarClock,
  Boxes,
  Bitcoin,
  Coins,
} from "lucide-react";

/**
 * Premium Bento Grid Features - Enterprise 2026
 *
 * Features:
 * - Clean bento grid layout
 * - Vibrant gradient color scheme (blue to violet to cyan)
 * - Fixed card heights with full content visible
 * - No distracting animations
 */

const features = [
  {
    icon: Globe,
    title: "Multi-Broker Support",
    description: "TradeLocker, ProjectX, Tradovate, TopStep, MetaTrader - all from one unified dashboard.",
    color: "blue",
  },
  {
    icon: Zap,
    title: "Sub-55ms Execution",
    description: "Lightning-fast signal processing. Your trades execute before you can blink.",
    color: "violet",
  },
  {
    icon: Coins,
    title: "All Asset Classes",
    description: "Futures, Forex, Crypto, Indices, Commodities - trade any market from one platform.",
    color: "cyan",
  },
  {
    icon: Shield,
    title: "Signal Intelligence Guard",
    description: "Self-protecting execution layer. Blocks stale signals, detects choppy markets, prevents bad entries.",
    color: "purple",
  },
  {
    icon: Lock,
    title: "Profit Lock Protection",
    description: "Smart exit protection tracks peak profits and only allows flips when profits drop significantly.",
    color: "blue",
  },
  {
    icon: TrendingDown,
    title: "Complete Risk Suite",
    description: "Daily loss limits, max drawdown, position limits, and trade cooldowns protect your capital.",
    color: "violet",
  },
  {
    icon: BarChart3,
    title: "Smart Position Sizing",
    description: "Auto lot sizing based on balance, risk percentage, or fixed size.",
    color: "cyan",
  },
  {
    icon: Activity,
    title: "Chop Detection",
    description: "Detects sideways markets and pauses entries to prevent whipsaw losses.",
    color: "purple",
  },
  {
    icon: Pause,
    title: "Circuit Breakers",
    description: "Auto-pause when daily loss or consecutive losses hit limits. Resume after cooling.",
    color: "blue",
  },
  {
    icon: Sparkles,
    title: "AI Strategy Suite",
    description: "Build strategies with Pine Script, get AI-powered fixes, deploy to live alerts instantly.",
    color: "violet",
  },
  {
    icon: Brain,
    title: "AI Trading Coach",
    description: "Intelligent feedback with bias detection and improvement suggestions.",
    color: "cyan",
  },
  {
    icon: Boxes,
    title: "SmartFlow Indicator",
    description: "AI-powered options flow analysis for institutional-grade signals.",
    color: "purple",
    isNew: true,
  },
  {
    icon: LineChart,
    title: "Trading Analytics",
    description: "Win rate, profit factor, expectancy, Sharpe ratio - know exactly how you perform.",
    color: "blue",
  },
  {
    icon: CalendarClock,
    title: "Time-Based Analysis",
    description: "Performance heatmaps by hour, day, and trading session.",
    color: "violet",
  },
  {
    icon: Users,
    title: "Multi-Account Routing",
    description: "Route one signal to multiple accounts across different brokers simultaneously.",
    color: "cyan",
  },
  {
    icon: RefreshCw,
    title: "Symbol Mapping",
    description: "Auto-map symbols per broker. BTCUSD to BTC/USD seamlessly.",
    color: "purple",
  },
  {
    icon: Target,
    title: "Position Management",
    description: "View and close positions from any broker with one click.",
    color: "blue",
  },
  {
    icon: Newspaper,
    title: "News Event Filter",
    description: "Pause around FOMC, NFP, CPI releases automatically.",
    color: "violet",
  },
  {
    icon: GitBranch,
    title: "Correlation Filter",
    description: "Prevent correlated trades to reduce risk concentration.",
    color: "cyan",
  },
  {
    icon: Scale,
    title: "Dynamic Sizing",
    description: "Scale up winners, scale down during drawdowns automatically.",
    color: "purple",
  },
];

const colorClasses = {
  blue: {
    bg: "from-blue-500/15 to-blue-600/5",
    border: "border-blue-500/20 hover:border-blue-500/40",
    icon: "from-blue-500/30 to-blue-600/20",
    text: "text-blue-400",
  },
  violet: {
    bg: "from-violet-500/15 to-violet-600/5",
    border: "border-violet-500/20 hover:border-violet-500/40",
    icon: "from-violet-500/30 to-violet-600/20",
    text: "text-violet-400",
  },
  cyan: {
    bg: "from-cyan-500/15 to-cyan-600/5",
    border: "border-cyan-500/20 hover:border-cyan-500/40",
    icon: "from-cyan-500/30 to-cyan-600/20",
    text: "text-cyan-400",
  },
  purple: {
    bg: "from-purple-500/15 to-purple-600/5",
    border: "border-purple-500/20 hover:border-purple-500/40",
    icon: "from-purple-500/30 to-purple-600/20",
    text: "text-purple-400",
  },
};

function FeatureCard({
  feature,
  index,
  isInView,
}: {
  feature: typeof features[0];
  index: number;
  isInView: boolean;
}) {
  const Icon = feature.icon;
  const colors = colorClasses[feature.color as keyof typeof colorClasses];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.4, delay: Math.min(index * 0.05, 0.5) }}
      className={`
        relative p-5 rounded-2xl
        bg-gradient-to-br ${colors.bg}
        border ${colors.border}
        backdrop-blur-sm
        transition-all duration-300 hover:scale-[1.02]
        cursor-default
      `}
    >
      {feature.isNew && (
        <span className="absolute -top-2 -right-2 px-2 py-0.5 rounded-full bg-violet-500 text-[10px] font-bold text-white shadow-lg shadow-violet-500/30">
          NEW
        </span>
      )}

      <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${colors.icon} flex items-center justify-center mb-4`}>
        <Icon className={`w-5 h-5 ${colors.text}`} />
      </div>

      <h4 className="font-semibold text-base mb-2">{feature.title}</h4>
      <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
    </motion.div>
  );
}

// Animated stat
function AnimatedStat({ value, label, suffix = "", color }: { value: number; label: string; suffix?: string; color: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;
    const duration = 1500;
    const steps = 40;
    let step = 0;
    const timer = setInterval(() => {
      step++;
      const progress = step / steps;
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(value * easeOut));
      if (step >= steps) {
        setCount(value);
        clearInterval(timer);
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [value, isInView]);

  return (
    <div ref={ref} className="text-center">
      <div className={`text-3xl md:text-4xl font-bold ${color}`}>
        {count}{suffix}
      </div>
      <div className="text-sm text-muted-foreground mt-1">{label}</div>
    </div>
  );
}

export function Features() {
  const sectionRef = useRef<HTMLElement>(null);
  const isInView = useInView(sectionRef, { once: true, margin: "-100px" });

  return (
    <section ref={sectionRef} id="features" className="py-24 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 left-0 w-[500px] h-[500px] bg-gradient-to-r from-blue-500/5 to-violet-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-0 w-[400px] h-[400px] bg-gradient-to-l from-cyan-500/5 to-purple-500/5 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto px-4">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-blue-500/10 to-violet-500/10 border border-blue-500/20 backdrop-blur-sm mb-6">
            <Sparkles className="h-4 w-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-400">Enterprise Features</span>
          </div>

          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            Everything You Need to{" "}
            <span className="bg-gradient-to-r from-blue-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Dominate Markets
            </span>
          </h2>

          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Built for professional traders. Trade any market, any asset, any broker — all from one powerful platform.
          </p>
        </motion.div>

        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-16 p-8 rounded-3xl bg-gradient-to-br from-slate-900/90 to-slate-800/50 backdrop-blur-xl border border-white/10"
        >
          <AnimatedStat value={20} label="Features" suffix="+" color="text-blue-400" />
          <AnimatedStat value={5} label="Brokers" color="text-violet-400" />
          <AnimatedStat value={1000} label="Instruments" suffix="+" color="text-cyan-400" />
          <AnimatedStat value={99} label="Uptime" suffix="%" color="text-purple-400" />
        </motion.div>

        {/* Features grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((feature, index) => (
            <FeatureCard key={feature.title} feature={feature} index={index} isInView={isInView} />
          ))}
        </div>
      </div>
    </section>
  );
}
