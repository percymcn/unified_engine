"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Shield, Clock, Zap, Sparkles, TrendingUp, Play, Coins, BarChart2, Globe2 } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";

/**
 * Premium 2026 Hero Component - Enterprise Edition
 *
 * Features:
 * - Vibrant gradient color scheme (deep blue to electric purple to cyan)
 * - Subtle particle background
 * - All asset classes showcase
 * - Premium enterprise feel
 */

// Subtle particle animation component
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let particles: Array<{
      x: number;
      y: number;
      size: number;
      speedX: number;
      speedY: number;
      opacity: number;
      hue: number;
    }> = [];

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    const createParticles = () => {
      particles = [];
      const particleCount = Math.floor((canvas.width * canvas.height) / 20000);

      for (let i = 0; i < particleCount; i++) {
        particles.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: Math.random() * 1.5 + 0.5,
          speedX: (Math.random() - 0.5) * 0.3,
          speedY: (Math.random() - 0.5) * 0.3,
          opacity: Math.random() * 0.4 + 0.1,
          hue: Math.random() * 60 + 200, // Blue to purple range
        });
      }
    };

    const drawParticles = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((particle, i) => {
        particle.x += particle.speedX;
        particle.y += particle.speedY;

        if (particle.x < 0) particle.x = canvas.width;
        if (particle.x > canvas.width) particle.x = 0;
        if (particle.y < 0) particle.y = canvas.height;
        if (particle.y > canvas.height) particle.y = 0;

        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${particle.hue}, 80%, 70%, ${particle.opacity})`;
        ctx.fill();

        // Subtle connections
        particles.slice(i + 1, i + 5).forEach((otherParticle) => {
          const dx = particle.x - otherParticle.x;
          const dy = particle.y - otherParticle.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 80) {
            ctx.beginPath();
            ctx.strokeStyle = `hsla(220, 80%, 60%, ${0.05 * (1 - distance / 80)})`;
            ctx.lineWidth = 0.5;
            ctx.moveTo(particle.x, particle.y);
            ctx.lineTo(otherParticle.x, otherParticle.y);
            ctx.stroke();
          }
        });
      });

      animationFrameId = requestAnimationFrame(drawParticles);
    };

    resize();
    createParticles();
    drawParticles();

    window.addEventListener("resize", () => {
      resize();
      createParticles();
    });

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 -z-10 opacity-50"
      style={{ pointerEvents: "none" }}
    />
  );
}

// Asset class badges
function AssetClassBadges() {
  const assets = [
    { name: "Futures", icon: BarChart2, examples: "ES, NQ, MES, MNQ" },
    { name: "Forex", icon: Globe2, examples: "EUR/USD, GBP/USD" },
    { name: "Crypto", icon: Coins, examples: "BTC, ETH, SOL" },
    { name: "Indices", icon: TrendingUp, examples: "SPX, NDX, DJI" },
  ];

  return (
    <div className="flex flex-wrap justify-center gap-3 mt-8">
      {assets.map((asset, i) => (
        <motion.div
          key={asset.name}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.5 + i * 0.1 }}
          className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-sm"
        >
          <asset.icon className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-medium">{asset.name}</span>
          <span className="text-xs text-muted-foreground hidden sm:inline">
            {asset.examples}
          </span>
        </motion.div>
      ))}
    </div>
  );
}

// Live execution ticker
function ExecutionTicker() {
  const [trades, setTrades] = useState<Array<{ symbol: string; action: string; time: string; asset: string }>>([]);

  useEffect(() => {
    const symbols = [
      { symbol: "MES", asset: "Futures" },
      { symbol: "MNQ", asset: "Futures" },
      { symbol: "BTC/USD", asset: "Crypto" },
      { symbol: "ETH/USD", asset: "Crypto" },
      { symbol: "EUR/USD", asset: "Forex" },
      { symbol: "GBP/USD", asset: "Forex" },
      { symbol: "ES", asset: "Futures" },
      { symbol: "NQ", asset: "Futures" },
      { symbol: "SOL/USD", asset: "Crypto" },
      { symbol: "XAU/USD", asset: "Commodity" },
    ];
    const actions = ["BUY", "SELL"];

    const addTrade = () => {
      const sym = symbols[Math.floor(Math.random() * symbols.length)];
      const newTrade = {
        symbol: sym.symbol,
        asset: sym.asset,
        action: actions[Math.floor(Math.random() * actions.length)],
        time: new Date().toLocaleTimeString(),
      };
      setTrades((prev) => [newTrade, ...prev.slice(0, 4)]);
    };

    addTrade();
    const interval = setInterval(addTrade, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col gap-2 w-full">
      {trades.map((trade, i) => (
        <motion.div
          key={`${trade.time}-${i}`}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1 - i * 0.15, x: 0 }}
          className="flex items-center justify-between text-xs font-mono p-2 rounded-lg bg-white/5"
        >
          <span className={trade.action === "BUY" ? "text-emerald-400" : "text-rose-400"}>
            {trade.action}
          </span>
          <span className="text-foreground/80 font-semibold">{trade.symbol}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-white/10 text-muted-foreground">
            {trade.asset}
          </span>
        </motion.div>
      ))}
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20 pb-10">
      {/* Gradient background */}
      <div className="absolute inset-0 -z-20">
        {/* Main gradient mesh */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-blue-950/50 to-slate-950" />

        {/* Accent gradients - subtle, not moving */}
        <div
          className="absolute w-[800px] h-[800px] rounded-full opacity-30"
          style={{
            background: "radial-gradient(circle, rgba(59,130,246,0.3) 0%, rgba(147,51,234,0.2) 40%, transparent 70%)",
            top: "-20%",
            left: "-10%",
          }}
        />
        <div
          className="absolute w-[600px] h-[600px] rounded-full opacity-25"
          style={{
            background: "radial-gradient(circle, rgba(6,182,212,0.3) 0%, rgba(59,130,246,0.15) 50%, transparent 70%)",
            bottom: "-10%",
            right: "-5%",
          }}
        />
        <div
          className="absolute w-[400px] h-[400px] rounded-full opacity-20"
          style={{
            background: "radial-gradient(circle, rgba(168,85,247,0.3) 0%, transparent 70%)",
            top: "40%",
            right: "20%",
          }}
        />
      </div>

      <ParticleField />

      {/* Grid pattern */}
      <div className="absolute inset-0 -z-10 h-full w-full bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />

      <div className="container mx-auto px-4 md:px-6">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left content */}
          <div className="flex flex-col items-center lg:items-start text-center lg:text-left">
            {/* New feature badge */}
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-violet-500/20 to-cyan-500/20 border border-violet-500/30 backdrop-blur-sm mb-6"
            >
              <Sparkles className="h-4 w-4 text-violet-400" />
              <span className="text-sm font-medium bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                New: SmartFlow AI Indicator
              </span>
              <ArrowRight className="h-3 w-3 text-cyan-400" />
            </motion.div>

            {/* Main headline */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight mb-6"
            >
              Trade{" "}
              <span className="bg-gradient-to-r from-blue-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
                Any Market
              </span>
              <br />
              <span className="text-3xl md:text-4xl lg:text-5xl text-foreground/80">
                Execute in &lt;55ms
              </span>
            </motion.h1>

            {/* Subheadline */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-lg md:text-xl text-muted-foreground max-w-xl mb-6"
            >
              Route TradingView alerts to{" "}
              <span className="text-foreground font-medium">any broker</span> instantly.
              Futures, Forex, Crypto, Indices, Commodities — all from one platform.
            </motion.p>

            {/* Asset class badges */}
            <AssetClassBadges />

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="flex flex-col sm:flex-row gap-4 mt-8"
            >
              <Button
                size="lg"
                asChild
                className="text-base px-8 h-14 bg-gradient-to-r from-blue-500 via-violet-500 to-cyan-500 hover:from-blue-600 hover:via-violet-600 hover:to-cyan-600 shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all duration-300 border-0"
              >
                <Link href="/register">
                  Start Free - No Card Required
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                asChild
                className="text-base px-8 h-14 backdrop-blur-sm bg-white/5 border-white/20 hover:bg-white/10 hover:border-violet-500/50"
              >
                <a href="#demo">
                  <Play className="mr-2 h-4 w-4" />
                  Watch Demo
                </a>
              </Button>
            </motion.div>

            {/* Trust indicators */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 }}
              className="flex items-center gap-6 text-sm text-muted-foreground mt-8"
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>500+ Active Traders</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-cyan-500" />
                <span>Enterprise Security</span>
              </div>
            </motion.div>
          </div>

          {/* Right side - Dashboard preview */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="relative hidden lg:block"
          >
            {/* Main dashboard card */}
            <div className="p-6 rounded-3xl bg-gradient-to-br from-slate-900/90 to-slate-800/50 backdrop-blur-xl border border-white/10 shadow-2xl shadow-violet-500/10">
              {/* Performance stats */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/20">
                  <Zap className="w-5 h-5 text-blue-400 mb-2" />
                  <div className="text-xl font-bold text-blue-400">&lt;55ms</div>
                  <div className="text-xs text-muted-foreground">Execution</div>
                </div>
                <div className="p-3 rounded-xl bg-gradient-to-br from-violet-500/20 to-violet-600/10 border border-violet-500/20">
                  <Clock className="w-5 h-5 text-violet-400 mb-2" />
                  <div className="text-xl font-bold text-violet-400">99.9%</div>
                  <div className="text-xs text-muted-foreground">Uptime</div>
                </div>
                <div className="p-3 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border border-cyan-500/20">
                  <TrendingUp className="w-5 h-5 text-cyan-400 mb-2" />
                  <div className="text-xl font-bold text-cyan-400">10K+</div>
                  <div className="text-xs text-muted-foreground">Signals</div>
                </div>
              </div>

              {/* Live executions */}
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium">Live Executions</span>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs text-emerald-400">Live</span>
                </div>
              </div>
              <ExecutionTicker />
            </div>

            {/* Floating badge - brokers */}
            <div className="absolute -bottom-4 -left-4 p-4 rounded-2xl bg-gradient-to-br from-slate-900/95 to-slate-800/80 backdrop-blur-xl border border-white/10 shadow-xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/30 to-violet-600/20 flex items-center justify-center">
                  <Globe2 className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <div className="text-lg font-bold">5 Brokers</div>
                  <div className="text-xs text-muted-foreground">Connected</div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Bottom stats */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
          className="mt-16 lg:mt-24"
        >
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 max-w-5xl mx-auto">
            <StatCard label="Futures" examples="ES, NQ, MES, MNQ, GC" color="blue" />
            <StatCard label="Forex" examples="EUR/USD, GBP/USD, USD/JPY" color="violet" />
            <StatCard label="Crypto" examples="BTC, ETH, SOL, XRP" color="cyan" />
            <StatCard label="Indices" examples="SPX, NDX, DJI, RUT" color="purple" />
            <StatCard label="Commodities" examples="Gold, Silver, Oil" color="amber" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function StatCard({ label, examples, color }: { label: string; examples: string; color: string }) {
  const colorClasses = {
    blue: "from-blue-500/20 to-blue-600/10 border-blue-500/20 text-blue-400",
    violet: "from-violet-500/20 to-violet-600/10 border-violet-500/20 text-violet-400",
    cyan: "from-cyan-500/20 to-cyan-600/10 border-cyan-500/20 text-cyan-400",
    purple: "from-purple-500/20 to-purple-600/10 border-purple-500/20 text-purple-400",
    amber: "from-amber-500/20 to-amber-600/10 border-amber-500/20 text-amber-400",
  };

  return (
    <div className={`p-4 rounded-2xl bg-gradient-to-br ${colorClasses[color as keyof typeof colorClasses]} border backdrop-blur-sm`}>
      <div className={`text-lg font-bold ${colorClasses[color as keyof typeof colorClasses].split(' ').pop()}`}>
        {label}
      </div>
      <div className="text-xs text-muted-foreground mt-1">{examples}</div>
    </div>
  );
}
