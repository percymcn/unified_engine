"use client";

import { useEffect, useRef, useState } from "react";
import { Shield, Lock, Globe, CheckCircle, Zap } from "lucide-react";

/**
 * Stats for animated counters
 */
const stats = [
  { value: 10000, suffix: "+", label: "Signals Executed" },
  { value: 50, suffix: "+", label: "Countries" },
  { value: 99.9, suffix: "%", label: "Uptime", decimals: 1 },
  { value: 4, suffix: "", label: "Broker Integrations" },
];

/**
 * Supported broker platforms
 */
const brokers = [
  { name: "TradeLocker", description: "Full API Integration" },
  { name: "Tradovate", description: "OAuth + REST API" },
  { name: "TopStep", description: "ProjectX SDK" },
  { name: "MetaTrader", description: "MT4 & MT5 via MetaAPI" },
];

/**
 * Trust signals configuration
 * These badges display security and compliance indicators to build credibility
 */
const trustSignals = [
  {
    icon: Lock,
    text: "Secure Payments via Stripe",
    description: "PCI-compliant payment processing",
  },
  {
    icon: Shield,
    text: "256-bit SSL Encryption",
    description: "All data encrypted in transit",
  },
  {
    icon: Globe,
    text: "GDPR Compliant",
    description: "Privacy by design",
  },
  {
    icon: CheckCircle,
    text: "No API Key Exposure",
    description: "Keys never leave our servers",
  },
];

/**
 * AnimatedCounter component for smooth number counting animation
 */
function AnimatedCounter({
  value,
  suffix,
  decimals = 0,
  isVisible,
}: {
  value: number;
  suffix: string;
  decimals?: number;
  isVisible: boolean;
}) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!isVisible) return;

    const duration = 2000; // 2 seconds
    const steps = 60;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      // Ease-out animation
      const progress = step / steps;
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = value * easeOut;

      setCount(current);

      if (step >= steps) {
        setCount(value);
        clearInterval(timer);
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [value, isVisible]);

  const displayValue = decimals > 0 ? count.toFixed(decimals) : Math.floor(count);

  return (
    <span>
      {displayValue}
      {suffix}
    </span>
  );
}

/**
 * SocialProof component displays trust signals, stats, and broker compatibility
 * Enhanced with animated counters and scroll-triggered animations
 */
export function SocialProof() {
  const sectionRef = useRef<HTMLElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="py-16 border-y bg-background/50">
      <div className="container mx-auto px-4 space-y-12">
        {/* Animated stats bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((stat, index) => (
            <div
              key={stat.label}
              className={`transition-all duration-500 ${
                isVisible
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-4"
              }`}
              style={{ transitionDelay: `${index * 100}ms` }}
            >
              <div className="text-3xl md:text-4xl font-bold text-primary">
                <AnimatedCounter
                  value={stat.value}
                  suffix={stat.suffix}
                  decimals={stat.decimals}
                  isVisible={isVisible}
                />
              </div>
              <div className="text-sm text-muted-foreground mt-1">
                {stat.label}
              </div>
            </div>
          ))}
        </div>

        {/* Broker logos section */}
        <div
          className={`transition-all duration-500 delay-300 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          <p className="text-center text-sm text-muted-foreground mb-6">
            Works with your favorite brokers
          </p>
          <div className="flex flex-wrap justify-center gap-6 md:gap-10">
            {brokers.map((broker) => (
              <div
                key={broker.name}
                className="flex flex-col items-center gap-1 group"
              >
                {/* Broker icon placeholder - styled text */}
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                  <Zap className="w-6 h-6 text-primary" />
                </div>
                <span className="text-sm font-medium">{broker.name}</span>
                <span className="text-xs text-muted-foreground">
                  {broker.description}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Trust signal badges */}
        <div
          className={`transition-all duration-500 delay-500 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          <div className="flex flex-wrap justify-center gap-6 md:gap-8">
            {trustSignals.map((signal) => (
              <div
                key={signal.text}
                className="flex items-center gap-2 text-sm group"
                title={signal.description}
              >
                <signal.icon className="w-4 h-4 text-green-500 group-hover:scale-110 transition-transform" />
                <span className="text-foreground/80">{signal.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
