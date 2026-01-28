'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Zap,
  Shield,
  Users,
  Target,
  TrendingUp,
  Globe,
  Clock,
  Award,
  ArrowRight,
} from 'lucide-react';

const stats = [
  { label: 'Signals Processed', value: '1M+', icon: Zap },
  { label: 'Active Traders', value: '5,000+', icon: Users },
  { label: 'Avg Latency', value: '<50ms', icon: Clock },
  { label: 'Uptime', value: '99.9%', icon: Shield },
];

const values = [
  {
    icon: Target,
    title: 'Precision',
    description: 'Every millisecond counts in trading. We obsess over latency optimization to ensure your signals execute exactly when they should.',
  },
  {
    icon: Shield,
    title: 'Security',
    description: 'Bank-grade encryption protects your credentials. We never store passwords - only secure tokens needed for execution.',
  },
  {
    icon: Users,
    title: 'Reliability',
    description: 'Built for 24/7 operation with redundant systems and automatic failover. Your strategies run even while you sleep.',
  },
  {
    icon: TrendingUp,
    title: 'Transparency',
    description: 'Full execution logs, real-time status updates, and detailed analytics. Know exactly what happened with every signal.',
  },
];

const milestones = [
  { year: '2024', event: 'Founded with a mission to democratize automated trading' },
  { year: '2024', event: 'Launched TradeLocker and ProjectX integrations' },
  { year: '2025', event: 'Added MT4/MT5 support via MetaAPI' },
  { year: '2025', event: 'Reached 5,000+ active traders' },
  { year: '2026', event: 'Expanding to more brokers and prop firms' },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="font-bold text-xl">
            Tradeflow
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost">Login</Button>
            </Link>
            <Link href="/register">
              <Button>Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 bg-gradient-to-b from-primary/5 to-background">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            About Tradeflow
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
            We&apos;re on a mission to make automated trading accessible to everyone.
            No coding required, no complex setup - just connect and trade.
          </p>
          <div className="flex justify-center gap-4">
            <Link href="/register">
              <Button size="lg">
                Start Trading <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/contact">
              <Button size="lg" variant="outline">
                Contact Us
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 border-b">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <stat.icon className="h-8 w-8 mx-auto mb-3 text-primary" />
                <div className="text-3xl font-bold mb-1">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Story */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold mb-6 text-center">Our Story</h2>
            <div className="prose prose-lg dark:prose-invert mx-auto">
              <p className="text-muted-foreground leading-relaxed mb-6">
                Tradeflow was born from a simple frustration: why is it so hard to automate
                TradingView strategies? As traders ourselves, we spent countless hours
                trying to connect our signals to brokers, dealing with complex APIs,
                unreliable webhooks, and constant maintenance.
              </p>
              <p className="text-muted-foreground leading-relaxed mb-6">
                We built Tradeflow to solve this problem once and for all. Our platform
                handles the technical complexity so you can focus on what matters -
                developing and refining your trading strategies.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                Today, Tradeflow connects thousands of traders to their favorite brokers
                and prop firms, executing millions of signals with sub-50ms latency.
                Whether you&apos;re trading forex, futures, or crypto, we&apos;ve got you covered.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold mb-12 text-center">Our Values</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {values.map((value) => (
              <Card key={value.title} className="bg-background">
                <CardContent className="pt-6">
                  <value.icon className="h-10 w-10 text-primary mb-4" />
                  <h3 className="font-semibold text-lg mb-2">{value.title}</h3>
                  <p className="text-sm text-muted-foreground">{value.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold mb-12 text-center">Our Journey</h2>
          <div className="max-w-2xl mx-auto">
            {milestones.map((milestone, index) => (
              <div key={index} className="flex gap-4 mb-8 last:mb-0">
                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                    {milestone.year}
                  </div>
                  {index < milestones.length - 1 && (
                    <div className="w-0.5 h-full bg-border mt-2" />
                  )}
                </div>
                <div className="pt-3">
                  <p className="text-muted-foreground">{milestone.event}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Supported Brokers */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Supported Platforms</h2>
          <p className="text-muted-foreground mb-12 max-w-2xl mx-auto">
            We integrate with the most popular brokers and prop firms to give you
            maximum flexibility in where you trade.
          </p>
          <div className="flex flex-wrap justify-center gap-8 items-center">
            <div className="flex flex-col items-center gap-2">
              <Globe className="h-12 w-12 text-muted-foreground" />
              <span className="font-semibold">TradeLocker</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Globe className="h-12 w-12 text-muted-foreground" />
              <span className="font-semibold">ProjectX / TopStep</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Globe className="h-12 w-12 text-muted-foreground" />
              <span className="font-semibold">MetaTrader 4</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Globe className="h-12 w-12 text-muted-foreground" />
              <span className="font-semibold">MetaTrader 5</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Globe className="h-12 w-12 text-muted-foreground" />
              <span className="font-semibold">Tradovate</span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <Award className="h-16 w-16 mx-auto mb-6 text-primary" />
          <h2 className="text-3xl font-bold mb-4">Ready to Automate Your Trading?</h2>
          <p className="text-muted-foreground mb-8 max-w-xl mx-auto">
            Join thousands of traders who trust Tradeflow to execute their strategies
            24/7 with lightning-fast speed.
          </p>
          <Link href="/register">
            <Button size="lg">
              Start Free Trial <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} Tradeflow. All rights reserved.</p>
          <div className="flex justify-center gap-4 mt-4">
            <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
            <Link href="/terms" className="hover:text-foreground">Terms</Link>
            <Link href="/contact" className="hover:text-foreground">Contact</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
