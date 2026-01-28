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
  HelpCircle,
  MessageCircle,
  Search,
  Zap,
  Shield,
  Key,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FAQ {
  id: string;
  question: string;
  answer: string;
  category: 'getting-started' | 'webhooks' | 'brokers' | 'signals' | 'troubleshooting';
}

const FAQS: FAQ[] = [
  // Getting Started
  {
    id: 'what-is-tradeflow',
    question: 'What is Tradeflow?',
    answer: 'Tradeflow is an automated trading signal router that connects your TradingView alerts (or any webhook source) to your broker accounts. It executes trades automatically based on the signals you receive.',
    category: 'getting-started',
  },
  {
    id: 'how-to-start',
    question: 'How do I get started?',
    answer: '1. Generate a webhook key from the dashboard\n2. Connect your broker account(s)\n3. Set up alerts in TradingView with your webhook URL\n4. Your trades will execute automatically when signals arrive',
    category: 'getting-started',
  },
  {
    id: 'supported-brokers',
    question: 'Which brokers are supported?',
    answer: 'We support MT4/MT5 (via MetaAPI), TradeLocker, Tradovate, and ProjectX/TopStep. You can connect multiple brokers and route signals to specific accounts.',
    category: 'getting-started',
  },
  // Webhooks
  {
    id: 'webhook-format',
    question: 'What format should my webhook payload be?',
    answer: 'Your webhook should be JSON with at minimum: action (buy/sell/close), symbol. Optional fields: quantity, price, stop_loss, take_profit, comment. Example:\n{"action": "buy", "symbol": "EURUSD", "quantity": 0.1}',
    category: 'webhooks',
  },
  {
    id: 'webhook-url',
    question: 'What is my webhook URL?',
    answer: 'Your webhook URL is: https://your-domain.com/api/v1/webhook/signal/{YOUR_WEBHOOK_KEY}\n\nReplace {YOUR_WEBHOOK_KEY} with your actual key from the dashboard.',
    category: 'webhooks',
  },
  {
    id: 'test-webhook',
    question: 'How do I test my webhook?',
    answer: 'Use the "Test Webhook" button on the dashboard. It sends a sample buy signal for XAUUSD. Make sure you have at least one broker account connected first.',
    category: 'webhooks',
  },
  // Brokers
  {
    id: 'connect-mt4',
    question: 'How do I connect MT4/MT5?',
    answer: 'Go to Settings > Accounts, click "Add Account", select MT4 or MT5. You can use MetaAPI BYOA (Bring Your Own Account) by entering your MetaAPI account ID, or we can provision one for you.',
    category: 'brokers',
  },
  {
    id: 'broker-disconnected',
    question: 'Why is my broker showing disconnected?',
    answer: 'Check: 1) Your broker credentials are correct, 2) The trading server is online, 3) Your account isn\'t locked or expired. Try reconnecting from Settings > Accounts.',
    category: 'brokers',
  },
  // Signals
  {
    id: 'signal-rejected',
    question: 'Why was my signal rejected?',
    answer: 'Signals can be rejected by AI Guards for various reasons: duplicate signal, staleness (old timestamp), drawdown limit exceeded, daily loss limit, or position size exceeds risk parameters. Check the Rejected Signals widget for details.',
    category: 'signals',
  },
  {
    id: 'ai-guards',
    question: 'What are AI Guards?',
    answer: 'AI Guards are protective filters that analyze incoming signals before execution. They include: Staleness Guard (rejects old signals), Duplicate Guard (prevents double entries), Drawdown Guard (stops trading at loss limit), and more.',
    category: 'signals',
  },
  // Troubleshooting
  {
    id: 'trade-not-executing',
    question: 'Why aren\'t my trades executing?',
    answer: 'Check: 1) Webhook key is correct, 2) Broker is connected, 3) Signal format is valid JSON, 4) Symbol exists on your broker, 5) Account has sufficient margin. Check webhook logs for detailed errors.',
    category: 'troubleshooting',
  },
  {
    id: 'symbol-not-found',
    question: 'Symbol not found error?',
    answer: 'Different brokers use different symbol names. Use Symbol Mapping in Settings to map your TradingView symbols to your broker\'s symbols. For example: XAUUSD might be GOLD on some brokers.',
    category: 'troubleshooting',
  },
];

const CATEGORIES = [
  { id: 'getting-started', label: 'Getting Started', icon: Zap },
  { id: 'webhooks', label: 'Webhooks', icon: Key },
  { id: 'brokers', label: 'Brokers', icon: BarChart3 },
  { id: 'signals', label: 'Signals', icon: Shield },
  { id: 'troubleshooting', label: 'Troubleshooting', icon: AlertTriangle },
];

export function SupportChat() {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const filteredFaqs = FAQS.filter((faq) => {
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
          variant="outline"
          size="icon"
          className={cn(
            'fixed bottom-20 right-4 z-40 h-12 w-12 rounded-full shadow-lg',
            'bg-primary/10 border-primary/30 hover:bg-primary/20',
            'transition-all hover:scale-110'
          )}
        >
          <HelpCircle className="h-5 w-5 text-primary" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="pb-4">
          <SheetTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5 text-primary" />
            Help & Support
          </SheetTitle>
          <SheetDescription>
            Find answers to common questions about Tradeflow
          </SheetDescription>
        </SheetHeader>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search FAQs..."
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
              <HelpCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No FAQs match your search</p>
            </div>
          ) : (
            filteredFaqs.map((faq) => (
              <AccordionItem key={faq.id} value={faq.id}>
                <AccordionTrigger className="text-left text-sm hover:no-underline">
                  <span className="pr-2">{faq.question}</span>
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground whitespace-pre-line">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))
          )}
        </Accordion>

        {/* Quick Links */}
        <div className="mt-6 pt-4 border-t">
          <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500" />
            Quick Links
          </h4>
          <div className="space-y-2">
            <a
              href="/dashboard/settings/accounts"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Add Broker Account
            </a>
            <a
              href="/dashboard/settings/webhooks"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Webhook Settings
            </a>
            <a
              href="/ai-suite"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              AI Strategy Suite
            </a>
            <a
              href="mailto:support@tradeflow.com"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Contact Support
            </a>
          </div>
        </div>

        {/* Feedback section */}
        <div className="mt-6 p-4 rounded-lg bg-muted/50 border">
          <p className="text-sm text-muted-foreground">
            Can't find what you're looking for?
          </p>
          <Button variant="outline" size="sm" className="mt-2 w-full" onClick={() => window.location.href = 'mailto:support@tradeflow.com'}>
            <MessageCircle className="h-4 w-4 mr-2" />
            Contact Support
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
