"use client";

import Link from "next/link";
import { ArrowRight, Shield, Clock, Zap, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";

/**
 * Enhanced Hero Component
 *
 * Key improvements:
 * - Urgency-focused headline addressing trader pain points
 * - Emotional subheadline about missed trades and slippage
 * - Strong CTA with "no card needed" trust signal
 * - Animated entrance using framer-motion
 * - Trust badges with real stats
 */
export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Animated gradient background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 -left-1/4 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl animate-blob" />
        <div className="absolute top-1/3 -right-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl animate-blob animation-delay-2000" />
        <div className="absolute -bottom-1/4 left-1/3 w-96 h-96 bg-cyan-500/20 rounded-full blur-3xl animate-blob animation-delay-4000" />
      </div>

      <div className="container mx-auto px-4 md:px-6">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          {/* Urgency badge with animation */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm font-medium mb-8"
          >
            <AlertTriangle className="h-4 w-4" />
            <span>Stop missing trades while you sleep</span>
          </motion.div>

          {/* Main headline with staggered animation */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6"
          >
            Never Miss a Trade Again{" "}
            <span className="block mt-2 bg-gradient-to-r from-green-400 via-emerald-500 to-cyan-500 bg-clip-text text-transparent">
              Auto-Execute in &lt;55ms
            </span>
          </motion.h1>

          {/* Emotional subheadline addressing pain points */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-4"
          >
            Tired of waking up to missed setups? Frustrated by slippage eating your edge?
          </motion.p>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-lg md:text-xl text-foreground/80 max-w-2xl mb-8"
          >
            Tradeflow routes your TradingView alerts to TradeLocker, Tradovate, TopStep,
            and MetaTrader <strong className="text-primary">instantly</strong> so you can trade while you sleep.
          </motion.p>

          {/* CTAs with strong value proposition */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex flex-col sm:flex-row gap-4 mb-6"
          >
            <Button size="lg" asChild className="text-base px-8 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700">
              <Link href="/register">
                Start Free - No Card Needed
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild className="text-base px-8">
              <a href="#how-it-works">See How It Works</a>
            </Button>
          </motion.div>

          {/* Trust signal */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="text-sm text-muted-foreground mb-12"
          >
            Join 500+ traders already automating their strategies
          </motion.p>

          {/* Stats with animations */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="grid grid-cols-1 sm:grid-cols-3 gap-8 w-full max-w-2xl"
          >
            <StatItem
              icon={Zap}
              value="< 50ms"
              label="Execution Speed"
              highlight="Beat slippage"
            />
            <StatItem
              icon={Clock}
              value="99.9%"
              label="Uptime"
              highlight="24/7 reliability"
            />
            <StatItem
              icon={Shield}
              value="10,000+"
              label="Signals Routed"
              highlight="Proven at scale"
            />
          </motion.div>
        </div>
      </div>

      {/* Decorative grid */}
      <div className="absolute inset-0 -z-10 h-full w-full bg-[linear-gradient(to_right,#8882_1px,transparent_1px),linear-gradient(to_bottom,#8882_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />
    </section>
  );
}

interface StatItemProps {
  icon: React.ElementType;
  value: string;
  label: string;
  highlight?: string;
}

function StatItem({ icon: Icon, value, label, highlight }: StatItemProps) {
  return (
    <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-card/50 border hover:border-primary/50 transition-colors">
      <Icon className="h-5 w-5 text-primary" />
      <span className="text-2xl font-bold">{value}</span>
      <span className="text-sm text-muted-foreground">{label}</span>
      {highlight && (
        <span className="text-xs text-primary font-medium">{highlight}</span>
      )}
    </div>
  );
}
