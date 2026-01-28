'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  BookOpen,
  Calendar,
  Clock,
  ArrowRight,
  Search,
  TrendingUp,
  Shield,
  Zap,
  Settings,
} from 'lucide-react';

const blogPosts = [
  {
    id: 1,
    title: 'Getting Started with TradingView Webhooks',
    description: 'Learn how to set up TradingView alerts and connect them to Tradeflow for automated trading execution.',
    category: 'Tutorial',
    readTime: '5 min read',
    date: 'Jan 15, 2026',
    icon: Settings,
    featured: true,
  },
  {
    id: 2,
    title: 'Understanding Signal Latency and Why It Matters',
    description: 'Discover how latency affects your trading performance and what Tradeflow does to minimize execution delays.',
    category: 'Education',
    readTime: '7 min read',
    date: 'Jan 10, 2026',
    icon: Zap,
    featured: true,
  },
  {
    id: 3,
    title: 'Risk Management Best Practices for Automated Trading',
    description: 'Essential risk management strategies to protect your capital when running automated trading systems.',
    category: 'Strategy',
    readTime: '10 min read',
    date: 'Jan 5, 2026',
    icon: Shield,
    featured: false,
  },
  {
    id: 4,
    title: 'Connecting Your Prop Firm Account to Tradeflow',
    description: 'Step-by-step guide to connecting FTMO, The Funded Trader, and other prop firm accounts.',
    category: 'Tutorial',
    readTime: '6 min read',
    date: 'Dec 28, 2025',
    icon: TrendingUp,
    featured: false,
  },
  {
    id: 5,
    title: 'Pine Script Alert Syntax for Tradeflow',
    description: 'Master the alert message format to send complex signals including stop loss, take profit, and position sizing.',
    category: 'Tutorial',
    readTime: '8 min read',
    date: 'Dec 20, 2025',
    icon: BookOpen,
    featured: false,
  },
  {
    id: 6,
    title: 'Multi-Account Trading: Route Signals to Multiple Brokers',
    description: 'Learn how to configure Tradeflow to execute the same signal across multiple trading accounts simultaneously.',
    category: 'Advanced',
    readTime: '12 min read',
    date: 'Dec 15, 2025',
    icon: Settings,
    featured: false,
  },
];

const categories = ['All', 'Tutorial', 'Education', 'Strategy', 'Advanced'];

export default function BlogPage() {
  const featuredPosts = blogPosts.filter((post) => post.featured);
  const regularPosts = blogPosts.filter((post) => !post.featured);

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
      <section className="py-16 bg-gradient-to-b from-primary/5 to-background">
        <div className="container mx-auto px-4">
          <div className="max-w-2xl mx-auto text-center">
            <BookOpen className="h-12 w-12 mx-auto mb-4 text-primary" />
            <h1 className="text-4xl font-bold mb-4">Tradeflow Blog</h1>
            <p className="text-lg text-muted-foreground mb-8">
              Tutorials, tips, and strategies to help you get the most out of automated trading.
            </p>
            <div className="relative max-w-md mx-auto">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search articles..."
                className="pl-10"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="py-6 border-b">
        <div className="container mx-auto px-4">
          <div className="flex flex-wrap justify-center gap-2">
            {categories.map((category) => (
              <Button
                key={category}
                variant={category === 'All' ? 'default' : 'outline'}
                size="sm"
              >
                {category}
              </Button>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Posts */}
      <section className="py-12">
        <div className="container mx-auto px-4">
          <h2 className="text-2xl font-bold mb-8">Featured Articles</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {featuredPosts.map((post) => (
              <Card key={post.id} className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="secondary">{post.category}</Badge>
                    <Badge variant="outline" className="text-primary border-primary">Featured</Badge>
                  </div>
                  <CardTitle className="text-xl hover:text-primary transition-colors">
                    {post.title}
                  </CardTitle>
                  <CardDescription>{post.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      {post.date}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {post.readTime}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* All Posts */}
      <section className="py-12 bg-muted/30">
        <div className="container mx-auto px-4">
          <h2 className="text-2xl font-bold mb-8">All Articles</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {regularPosts.map((post) => (
              <Card key={post.id} className="hover:shadow-lg transition-shadow cursor-pointer bg-background">
                <CardHeader>
                  <div className="flex items-center gap-2 mb-2">
                    <post.icon className="h-5 w-5 text-primary" />
                    <Badge variant="secondary">{post.category}</Badge>
                  </div>
                  <CardTitle className="text-lg hover:text-primary transition-colors">
                    {post.title}
                  </CardTitle>
                  <CardDescription className="line-clamp-2">{post.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      {post.date}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {post.readTime}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Newsletter */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <div className="max-w-xl mx-auto text-center">
            <h2 className="text-2xl font-bold mb-4">Stay Updated</h2>
            <p className="text-muted-foreground mb-6">
              Get the latest trading tips, platform updates, and educational content delivered to your inbox.
            </p>
            <div className="flex gap-2">
              <Input placeholder="Enter your email" type="email" className="flex-1" />
              <Button>
                Subscribe <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              No spam, unsubscribe anytime. We respect your privacy.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-primary/5">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold mb-4">Ready to Start Automating?</h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Put what you&apos;ve learned into practice. Connect your TradingView to any broker in minutes.
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
