"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import { Shield, Lock, Globe, CheckCircle, Zap, TrendingUp, Building2, Coins, BarChart2, Bitcoin } from "lucide-react";

/**
 * Premium Social Proof Component - Enterprise 2026
 *
 * Features:
 * - All asset classes: Futures, Forex, Crypto, Indices, Commodities
 * - Vibrant gradient color scheme
 * - Enterprise-level trust signals
 */

// Stats for animated counters
const stats = [
  { value: 10000, suffix: "+", label: "Signals Executed", icon: TrendingUp, color: "text-blue-400" },
  { value: 50, suffix: "+", label: "Countries", icon: Globe, color: "text-violet-400" },
  { value: 99.9, suffix: "%", label: "Uptime SLA", decimals: 1, icon: Shield, color: "text-cyan-400" },
  { value: 5, suffix: "", label: "Broker Integrations", icon: Building2, color: "text-purple-400" },
];

// Supported broker platforms
const brokers = [
  { name: "TradeLocker", description: "CFD & Forex", gradient: "from-blue-500/20 to-blue-600/10", border: "border-blue-500/20" },
  { name: "ProjectX", description: "Micro Futures", gradient: "from-violet-500/20 to-violet-600/10", border: "border-violet-500/20", isNew: true },
  { name: "Tradovate", description: "Futures", gradient: "from-cyan-500/20 to-cyan-600/10", border: "border-cyan-500/20" },
  { name: "TopStep", description: "Prop Firm", gradient: "from-purple-500/20 to-purple-600/10", border: "border-purple-500/20" },
  { name: "MetaTrader", description: "MT4 & MT5", gradient: "from-amber-500/20 to-amber-600/10", border: "border-amber-500/20" },
];

// Comprehensive instrument list
const instruments = {
  futures: [
    { symbol: "MES", name: "Micro S&P" },
    { symbol: "MNQ", name: "Micro Nasdaq" },
    { symbol: "MYM", name: "Micro Dow" },
    { symbol: "M2K", name: "Micro Russell" },
    { symbol: "MGC", name: "Micro Gold" },
    { symbol: "ES", name: "E-mini S&P" },
    { symbol: "NQ", name: "E-mini Nasdaq" },
    { symbol: "YM", name: "E-mini Dow" },
    { symbol: "RTY", name: "E-mini Russell" },
    { symbol: "GC", name: "Gold" },
    { symbol: "CL", name: "Crude Oil" },
    { symbol: "SI", name: "Silver" },
  ],
  crypto: [
    { symbol: "BTC/USD", name: "Bitcoin" },
    { symbol: "ETH/USD", name: "Ethereum" },
    { symbol: "SOL/USD", name: "Solana" },
    { symbol: "XRP/USD", name: "Ripple" },
    { symbol: "ADA/USD", name: "Cardano" },
    { symbol: "DOGE/USD", name: "Dogecoin" },
    { symbol: "AVAX/USD", name: "Avalanche" },
    { symbol: "LINK/USD", name: "Chainlink" },
    { symbol: "DOT/USD", name: "Polkadot" },
    { symbol: "MATIC/USD", name: "Polygon" },
    { symbol: "LTC/USD", name: "Litecoin" },
    { symbol: "UNI/USD", name: "Uniswap" },
  ],
  forex: [
    { symbol: "EUR/USD", name: "Euro" },
    { symbol: "GBP/USD", name: "Pound" },
    { symbol: "USD/JPY", name: "Yen" },
    { symbol: "AUD/USD", name: "Aussie" },
    { symbol: "USD/CAD", name: "Loonie" },
    { symbol: "USD/CHF", name: "Swiss" },
    { symbol: "NZD/USD", name: "Kiwi" },
    { symbol: "EUR/GBP", name: "Euro/Pound" },
    { symbol: "EUR/JPY", name: "Euro/Yen" },
    { symbol: "GBP/JPY", name: "Pound/Yen" },
    { symbol: "XAU/USD", name: "Gold Spot" },
    { symbol: "XAG/USD", name: "Silver Spot" },
  ],
  indices: [
    { symbol: "US500", name: "S&P 500" },
    { symbol: "US100", name: "Nasdaq 100" },
    { symbol: "US30", name: "Dow Jones" },
    { symbol: "UK100", name: "FTSE 100" },
    { symbol: "DE40", name: "DAX 40" },
    { symbol: "JP225", name: "Nikkei 225" },
  ],
};

// Trust signals
const trustSignals = [
  { icon: Lock, text: "Secure Payments", description: "PCI-DSS Level 1" },
  { icon: Shield, text: "256-bit SSL", description: "End-to-end encryption" },
  { icon: Globe, text: "GDPR Compliant", description: "Privacy protected" },
  { icon: CheckCircle, text: "SOC 2 Type II", description: "Enterprise security" },
];

// Animated counter
function AnimatedCounter({ value, suffix, decimals = 0, isVisible }: { value: number; suffix: string; decimals?: number; isVisible: boolean }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!isVisible) return;
    const duration = 2000;
    const steps = 60;
    let step = 0;
    const timer = setInterval(() => {
      step++;
      const progress = step / steps;
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(value * easeOut);
      if (step >= steps) {
        setCount(value);
        clearInterval(timer);
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [value, isVisible]);

  return <span>{decimals > 0 ? count.toFixed(decimals) : Math.floor(count)}{suffix}</span>;
}

// Instruments showcase
function InstrumentsShowcase({ isInView }: { isInView: boolean }) {
  const [activeCategory, setActiveCategory] = useState<"futures" | "crypto" | "forex" | "indices">("futures");

  const categoryConfig = {
    futures: { icon: BarChart2, color: "bg-blue-500", textColor: "text-blue-400" },
    crypto: { icon: Bitcoin, color: "bg-violet-500", textColor: "text-violet-400" },
    forex: { icon: Globe, color: "bg-cyan-500", textColor: "text-cyan-400" },
    indices: { icon: TrendingUp, color: "bg-purple-500", textColor: "text-purple-400" },
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: 0.4 }}
    >
      {/* Category tabs */}
      <div className="flex justify-center gap-2 mb-8">
        {(Object.keys(instruments) as Array<keyof typeof instruments>).map((cat) => {
          const config = categoryConfig[cat];
          const Icon = config.icon;
          return (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`
                flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300
                ${activeCategory === cat
                  ? `${config.color} text-white shadow-lg`
                  : "bg-white/5 text-muted-foreground hover:bg-white/10 border border-white/10"
                }
              `}
            >
              <Icon className="w-4 h-4" />
              <span className="capitalize">{cat}</span>
              <span className="text-xs opacity-70">({instruments[cat].length})</span>
            </button>
          );
        })}
      </div>

      {/* Instruments grid */}
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3 max-w-5xl mx-auto">
        {instruments[activeCategory].map((inst, i) => (
          <motion.div
            key={inst.symbol}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, delay: i * 0.02 }}
            className={`
              p-3 rounded-xl backdrop-blur-sm transition-all duration-300 cursor-default
              bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10
              hover:border-${categoryConfig[activeCategory].textColor.replace('text-', '')}/50 hover:scale-105
            `}
          >
            <div className={`text-sm font-mono font-bold ${categoryConfig[activeCategory].textColor}`}>
              {inst.symbol}
            </div>
            <div className="text-[10px] text-muted-foreground truncate">{inst.name}</div>
          </motion.div>
        ))}
      </div>

      {/* All markets message */}
      <p className="text-center text-sm text-muted-foreground mt-6">
        <span className="text-foreground font-medium">1000+ instruments</span> supported across all major markets
      </p>
    </motion.div>
  );
}

export function SocialProof() {
  const sectionRef = useRef<HTMLElement>(null);
  const isInView = useInView(sectionRef, { once: true, margin: "-50px" });

  return (
    <section ref={sectionRef} className="py-20 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-gradient-to-r from-blue-500/5 to-violet-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-gradient-to-l from-cyan-500/5 to-purple-500/5 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto px-4 space-y-16">
        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-6 p-8 rounded-3xl bg-gradient-to-br from-slate-900/90 to-slate-800/50 backdrop-blur-xl border border-white/10"
        >
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="text-center"
              >
                <div className="flex justify-center mb-3">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br from-white/10 to-white/5 flex items-center justify-center`}>
                    <Icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                </div>
                <div className={`text-3xl md:text-4xl font-bold ${stat.color}`}>
                  <AnimatedCounter value={stat.value} suffix={stat.suffix} decimals={stat.decimals} isVisible={isInView} />
                </div>
                <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Brokers */}
        <div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            className="text-center text-sm text-muted-foreground mb-6"
          >
            Seamlessly connects with your favorite brokers
          </motion.p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 max-w-4xl mx-auto">
            {brokers.map((broker, index) => (
              <motion.div
                key={broker.name}
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className={`
                  relative p-5 rounded-2xl
                  bg-gradient-to-br ${broker.gradient}
                  backdrop-blur-sm border ${broker.border}
                  hover:scale-105 transition-transform duration-300 cursor-default
                `}
              >
                {broker.isNew && (
                  <span className="absolute -top-2 -right-2 px-2 py-0.5 rounded-full bg-violet-500 text-[10px] font-bold text-white">
                    NEW
                  </span>
                )}
                <div className="flex flex-col items-center text-center">
                  <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center mb-3">
                    <Zap className="w-6 h-6" />
                  </div>
                  <span className="font-semibold">{broker.name}</span>
                  <span className="text-xs text-muted-foreground">{broker.description}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Trust signals */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-wrap justify-center gap-4"
        >
          {trustSignals.map((signal, index) => (
            <motion.div
              key={signal.text}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={isInView ? { opacity: 1, scale: 1 } : {}}
              transition={{ duration: 0.3, delay: 0.4 + index * 0.1 }}
              className="flex items-center gap-3 px-5 py-3 rounded-xl bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10 hover:border-cyan-500/30 transition-all"
            >
              <signal.icon className="w-5 h-5 text-cyan-400" />
              <div>
                <span className="text-sm font-medium">{signal.text}</span>
                <span className="text-xs text-muted-foreground ml-2">{signal.description}</span>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Instruments showcase */}
        <div className="pt-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-violet-500/10 to-cyan-500/10 border border-violet-500/20 mb-4">
              <Coins className="h-4 w-4 text-violet-400" />
              <span className="text-sm font-medium text-violet-400">All Markets Supported</span>
            </div>
            <h3 className="text-2xl font-bold">
              Trade{" "}
              <span className="bg-gradient-to-r from-blue-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
                Any Instrument
              </span>
            </h3>
          </div>
          <InstrumentsShowcase isInView={isInView} />
        </div>
      </div>
    </section>
  );
}
