"use client";

import { useEffect, useRef, useState } from "react";
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
} from "lucide-react";

const features = [
  {
    icon: Globe,
    title: "Multi-Broker Support",
    description:
      "Connect to TradeLocker, Tradovate, TopStep, ProjectX, and MetaTrader from one dashboard.",
  },
  {
    icon: Zap,
    title: "Instant Execution",
    description:
      "Sub-55ms signal processing. Your trades execute before you blink.",
  },
  {
    icon: Shield,
    title: "Signal Intelligence Guard",
    description:
      "Self-protecting execution layer. Blocks stale signals, detects choppy markets, and prevents trading against profitable positions.",
  },
  {
    icon: Lock,
    title: "Profit Lock Protection",
    description:
      "Smart exit protection. Tracks peak profits and only allows position flips when profits drop significantly - protecting your winners.",
  },
  {
    icon: ArrowRightLeft,
    title: "TradingView Native",
    description:
      "Built for TradingView webhooks. Copy your URL and start routing signals.",
  },
  {
    icon: BarChart3,
    title: "Smart Position Sizing",
    description:
      "Automatic lot sizing based on account balance, risk percentage, or fixed size.",
  },
  {
    icon: Users,
    title: "Multi-Account Routing",
    description:
      "Route one signal to multiple accounts across different brokers simultaneously.",
  },
  {
    icon: Clock,
    title: "Trading Session Control",
    description:
      "Define your active trading hours and days. Signals outside your session are automatically paused.",
  },
  {
    icon: TrendingDown,
    title: "Risk Management",
    description:
      "Set daily loss limits, max drawdown, position limits, and trade cooldowns to protect your capital.",
  },
  {
    icon: Activity,
    title: "Chop Detection",
    description:
      "Automatically detects sideways/choppy markets and pauses new entries to prevent whipsaw losses.",
  },
  {
    icon: RefreshCw,
    title: "Symbol Mapping",
    description:
      "Map TradingView symbols to broker-specific formats automatically. BTCUSD → BTC/USD per broker.",
  },
  {
    icon: Target,
    title: "Position Management",
    description:
      "View and close positions from any broker directly in your dashboard with one click.",
  },
  {
    icon: Sparkles,
    title: "AI Strategy Suite",
    description:
      "Build strategies with Pine Script, get AI-powered fixes, and deploy to live alerts instantly.",
  },
  {
    icon: Brain,
    title: "AI Trading Coach",
    description:
      "Get intelligent feedback on your strategies with bias detection and improvement suggestions.",
  },
  {
    icon: LineChart,
    title: "Trading Analytics Dashboard",
    description:
      "Track win rate, profit factor, expectancy, Sharpe ratio, and max drawdown. Know exactly how your strategies perform.",
  },
  {
    icon: Pause,
    title: "Circuit Breakers",
    description:
      "Auto-pause trading when daily loss limits or consecutive losses are hit. Resume manually or after cooling period.",
  },
  {
    icon: Newspaper,
    title: "News Event Filter",
    description:
      "Automatically pause trading around high-impact news events like FOMC, NFP, and CPI releases.",
  },
  {
    icon: GitBranch,
    title: "Correlation Filter",
    description:
      "Prevent correlated trades. If you're long ES, it blocks another long NQ signal to reduce risk concentration.",
  },
  {
    icon: CalendarClock,
    title: "Time-Based Analysis",
    description:
      "Discover your best trading hours and days with performance heatmaps. See which sessions (Asian, London, NY) work best.",
  },
  {
    icon: Scale,
    title: "Dynamic Position Sizing",
    description:
      "Automatically adjust position size based on recent performance. Scale up winners, scale down during drawdowns.",
  },
];

export function Features() {
  const sectionRef = useRef<HTMLElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section
      id="features"
      ref={sectionRef}
      className="py-20 bg-muted/30"
    >
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-4">
          Everything You Need to Automate Your Trading
        </h2>
        <p className="text-center text-muted-foreground mb-16 max-w-2xl mx-auto">
          Built by traders, for traders. Tradeflow handles the complexity so you
          can focus on your strategy.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {features.map((feature, index) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
              index={index}
              isVisible={isVisible}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

interface FeatureCardProps {
  icon: React.ElementType;
  title: string;
  description: string;
  index: number;
  isVisible: boolean;
}

function FeatureCard({
  icon: Icon,
  title,
  description,
  index,
  isVisible,
}: FeatureCardProps) {
  return (
    <div
      className={`
        group p-6 rounded-xl bg-card border
        transition-all duration-500 ease-out
        hover:shadow-lg hover:border-primary/50 hover:-translate-y-1
        ${
          isVisible
            ? "opacity-100 translate-y-0"
            : "opacity-0 translate-y-4"
        }
      `}
      style={{
        transitionDelay: isVisible ? `${index * 100}ms` : "0ms",
      }}
    >
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-primary/10 text-primary mb-4 group-hover:bg-primary/20 transition-colors">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <p className="text-muted-foreground text-sm leading-relaxed">
        {description}
      </p>
    </div>
  );
}
