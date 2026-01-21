import Link from "next/link";
import { ArrowRight, Activity, Shield, Clock } from "lucide-react";

import { Button } from "@/components/ui/button";

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
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-8">
            <Activity className="h-4 w-4" />
            <span>Now supporting 4 major brokers</span>
          </div>

          {/* Main headline */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
            Route TradingView Signals to{" "}
            <span className="bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500 bg-clip-text text-transparent">
              Any Broker
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-8">
            Automatically execute your TradingView alerts on TradeLocker, Tradovate,
            TopStep, and MetaTrader. Set up once, trade everywhere.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 mb-16">
            <Button size="lg" asChild className="text-base px-8">
              <Link href="/register">
                Start Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild className="text-base px-8">
              <a href="#pricing">See Pricing</a>
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 w-full max-w-2xl">
            <StatItem
              icon={Activity}
              value="10,000+"
              label="Signals Routed"
            />
            <StatItem
              icon={Clock}
              value="99.9%"
              label="Uptime"
            />
            <StatItem
              icon={Shield}
              value="< 50ms"
              label="Avg Latency"
            />
          </div>
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
}

function StatItem({ icon: Icon, value, label }: StatItemProps) {
  return (
    <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-card/50 border">
      <Icon className="h-5 w-5 text-primary" />
      <span className="text-2xl font-bold">{value}</span>
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  );
}
