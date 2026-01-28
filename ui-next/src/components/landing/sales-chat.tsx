'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  MessageCircle,
  Search,
  Zap,
  DollarSign,
  Clock,
  Shield,
  BarChart3,
  Check,
  ExternalLink,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SalesFAQ {
  id: string;
  question: string;
  answer: string;
  category: 'pricing' | 'features' | 'getting-started' | 'support' | 'security';
}

const SALES_FAQS: SalesFAQ[] = [
  // Pricing
  {
    id: 'free-trial',
    question: 'Is there a free trial?',
    answer: 'Yes! You get 50 free trades or 7 days (whichever comes first) to test the platform. No credit card required. Just sign up and start trading.',
    category: 'pricing',
  },
  {
    id: 'pricing-plans',
    question: 'What are the pricing plans?',
    answer: 'We offer three tiers:\n\n- **Starter** ($14/mo): 2 broker accounts, 2,000 signals/mo\n- **Pro** ($29/mo): 5 broker accounts, unlimited signals, AI Strategy Suite\n- **Enterprise** ($79/mo): Unlimited accounts, priority support, AI Coach\n\nAll plans include our core signal routing features.',
    category: 'pricing',
  },
  {
    id: 'refund',
    question: 'What is your refund policy?',
    answer: 'We offer a 7-day money-back guarantee on all paid plans. If you\'re not satisfied, contact us within 7 days of purchase for a full refund.',
    category: 'pricing',
  },
  // Features
  {
    id: 'what-does-it-do',
    question: 'What does Tradeflow do?',
    answer: 'Tradeflow automatically executes your TradingView alerts on your broker accounts. Set up an alert in TradingView, and we execute the trade on MT4, MT5, TradeLocker, Tradovate, or TopStep in under 50ms.',
    category: 'features',
  },
  {
    id: 'supported-brokers',
    question: 'Which brokers do you support?',
    answer: 'We support:\n\n- **MetaTrader 4 & 5** (via MetaAPI)\n- **TradeLocker** (direct integration)\n- **Tradovate** (direct integration)\n- **TopStep/ProjectX** (direct integration)\n\nMore brokers coming soon!',
    category: 'features',
  },
  {
    id: 'execution-speed',
    question: 'How fast is signal execution?',
    answer: 'Our average execution time is under 50ms from signal receipt to order placement. We use low-latency infrastructure and direct broker connections to ensure the fastest possible execution.',
    category: 'features',
  },
  {
    id: 'ai-features',
    question: 'What is the AI Strategy Suite?',
    answer: 'The AI Strategy Suite includes:\n\n- **AI-Powered Charts**: Advanced TradingView-style charts with pattern recognition\n- **Pine Script Editor**: Write and test custom indicators\n- **Backtest Engine**: Test strategies on historical data\n- **AI Coach** (Enterprise): Get personalized trading advice\n\nAvailable on Pro and Enterprise plans.',
    category: 'features',
  },
  // Getting Started
  {
    id: 'how-to-start',
    question: 'How do I get started?',
    answer: '1. **Sign up** for a free account\n2. **Connect** your broker account (MT4/MT5, TradeLocker, etc.)\n3. **Copy** your webhook URL from the dashboard\n4. **Create** alerts in TradingView using your webhook\n5. **Done!** Trades execute automatically\n\nThe whole setup takes about 5 minutes.',
    category: 'getting-started',
  },
  {
    id: 'tradingview-required',
    question: 'Do I need TradingView?',
    answer: 'TradingView is the most common signal source, but Tradeflow works with any system that can send webhooks. This includes custom scripts, other trading platforms, or any service that can make HTTP requests.',
    category: 'getting-started',
  },
  // Support
  {
    id: 'support-options',
    question: 'What support do you offer?',
    answer: 'All plans include email support. Pro users get priority email support. Enterprise users get dedicated account management and direct access to our engineering team.\n\nWe also have comprehensive documentation and FAQ guides.',
    category: 'support',
  },
  // Security
  {
    id: 'security',
    question: 'Is my data secure?',
    answer: 'Yes! We use:\n\n- **AES-256 encryption** for all credentials\n- **TLS/SSL** for all connections\n- **SOC 2 compliant** infrastructure\n- We never store your trading passwords in plaintext\n\nYour broker credentials are encrypted and can only be used for trade execution.',
    category: 'security',
  },
  {
    id: 'api-access',
    question: 'Do you have API access?',
    answer: 'Yes! All plans include API access for programmatic signal submission. You can integrate Tradeflow into your custom trading systems, Python scripts, or any application that can make HTTP requests.',
    category: 'features',
  },
];

const CATEGORIES = [
  { id: 'pricing', label: 'Pricing', icon: DollarSign },
  { id: 'features', label: 'Features', icon: Zap },
  { id: 'getting-started', label: 'Getting Started', icon: Clock },
  { id: 'support', label: 'Support', icon: BarChart3 },
  { id: 'security', label: 'Security', icon: Shield },
];

export function SalesChat() {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const filteredFaqs = SALES_FAQS.filter((faq) => {
    const matchesSearch =
      searchQuery === '' ||
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory =
      selectedCategory === null || faq.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          className={cn(
            'fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-lg',
            'bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600',
            'transition-all hover:scale-110',
            'animate-bounce-slow'
          )}
          style={{
            animation: 'bounce 2s ease-in-out infinite',
          }}
        >
          <MessageCircle className="h-6 w-6 text-white" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="pb-4">
          <SheetTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-yellow-500" />
            Have Questions?
          </SheetTitle>
          <SheetDescription>
            Find answers about Tradeflow or get in touch
          </SheetDescription>
        </SheetHeader>

        {/* Free trial banner */}
        <div className="bg-gradient-to-r from-blue-500/10 to-emerald-500/10 border border-blue-500/20 rounded-lg p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Check className="h-4 w-4 text-emerald-500" />
            <span className="font-medium text-sm">Free Trial Available</span>
          </div>
          <p className="text-xs text-muted-foreground">
            50 trades or 7 days free. No credit card required.
          </p>
          <a href="/register">
            <Button size="sm" className="w-full mt-3 bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600">
              Start Free Trial
            </Button>
          </a>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search questions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Category filters */}
        <div className="flex flex-wrap gap-2 mb-4">
          <Badge
            variant={selectedCategory === null ? 'default' : 'outline'}
            className="cursor-pointer"
            onClick={() => setSelectedCategory(null)}
          >
            All
          </Badge>
          {CATEGORIES.map((cat) => (
            <Badge
              key={cat.id}
              variant={selectedCategory === cat.id ? 'default' : 'outline'}
              className="cursor-pointer gap-1"
              onClick={() => setSelectedCategory(cat.id)}
            >
              <cat.icon className="h-3 w-3" />
              {cat.label}
            </Badge>
          ))}
        </div>

        {/* FAQs */}
        <Accordion type="single" collapsible className="w-full">
          {filteredFaqs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No questions match your search</p>
            </div>
          ) : (
            filteredFaqs.map((faq) => (
              <AccordionItem key={faq.id} value={faq.id}>
                <AccordionTrigger className="text-left text-sm hover:no-underline">
                  <span className="pr-2">{faq.question}</span>
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground whitespace-pre-line prose prose-sm dark:prose-invert">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))
          )}
        </Accordion>

        {/* Quick Links */}
        <div className="mt-6 pt-4 border-t">
          <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
            <Zap className="h-4 w-4 text-yellow-500" />
            Quick Links
          </h4>
          <div className="space-y-2">
            <a
              href="/register"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Start Free Trial
            </a>
            <a
              href="/pricing"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              View Pricing
            </a>
            <a
              href="/login"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Sign In
            </a>
          </div>
        </div>

        {/* Contact section */}
        <div className="mt-6 p-4 rounded-lg bg-muted/50 border">
          <p className="text-sm text-muted-foreground">
            Can&apos;t find what you&apos;re looking for?
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2 w-full"
            onClick={() => window.location.href = 'mailto:support@tradeflow.com'}
          >
            <MessageCircle className="h-4 w-4 mr-2" />
            Contact Sales
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
