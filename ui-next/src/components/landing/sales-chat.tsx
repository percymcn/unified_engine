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
    answer: 'Tradeflow automatically executes your TradingView alerts on your broker accounts. Set up an alert in TradingView, and we execute the trade on MT4, MT5, TradeLocker, Tradovate, ProjectX, or TopStep in under 50ms.',
    category: 'features',
  },
  {
    id: 'supported-brokers',
    question: 'Which brokers do you support?',
    answer: 'We support:\n\n- **MetaTrader 4 & 5** (MT4 & MT5)\n- **TradeLocker**\n- **Tradovate**\n- **ProjectX**\n- **TopStep** (funded accounts)\n\nMore brokers coming soon!',
    category: 'features',
  },
  {
    id: 'execution-speed',
    question: 'How fast is signal execution?',
    answer: 'Our average execution time is under 50ms from signal receipt to order placement. We use low-latency infrastructure and direct broker connections to ensure the fastest possible execution.',
    category: 'features',
  },
  {
    id: 'signal-intelligence',
    question: 'What is Signal Intelligence Guard?',
    answer: 'Signal Intelligence Guard is our self-protecting execution layer. It includes:\n\n- **Chop Detection**: Detects sideways markets and pauses new entries\n- **Staleness Guard**: Rejects signals older than your threshold (e.g., 5 seconds)\n- **Position P&L Guard**: Blocks/warns when trading against profitable positions\n- **Profit Lock**: Tracks peak profit and only allows flips when profit drops significantly\n- **Auto-Breakeven**: Moves SL to entry when momentum shifts\n- **Trading Session Control**: Only trade during your defined hours\n\nThese features protect your winners and prevent whipsaw losses during consolidation.',
    category: 'features',
  },
  {
    id: 'profit-lock',
    question: 'What is Profit Lock?',
    answer: 'Profit Lock is our smart exit protection feature. It tracks your peak unrealized profit on each position.\n\n**How it works:**\n- You go LONG, profit runs to $800 (peak tracked)\n- Consolidation happens, flip signals start coming in\n- If profit is still near peak ($750): Signal BLOCKED (probably noise)\n- If profit dropped 50% to $400: Signal ALLOWED (trend likely changed)\n\nThis prevents you from closing winners during brief pullbacks while still allowing exits when trends actually reverse. You can configure:\n\n- **Min Profit to Track**: Only start tracking after $X profit (default: $200)\n- **Drop Threshold**: Allow flip after X% drop from peak (default: 50%)',
    category: 'features',
  },
  {
    id: 'risk-management',
    question: 'What risk management controls are available?',
    answer: 'Tradeflow has comprehensive per-account and global risk controls:\n\n**Daily Limits**\n- Max daily trades (e.g., stop after 10 trades)\n- Max daily loss in $ or %\n- Daily profit target — auto-halt when reached\n- Trade cooldown (e.g., wait 60s between trades)\n\n**Position Limits**\n- Max open positions across all symbols\n- Max positions per symbol\n- Max position size cap\n\n**Drawdown Protection**\n- Max drawdown % from peak equity — halts trading if hit\n\n**Position Sizing**\n- Fixed lot size\n- % of account balance\n- % of equity\n- Risk-based sizing (adjusts size based on stop loss distance)\n\nAll settings cascade: account setting → your global default → system default.',
    category: 'features',
  },
  {
    id: 'ai-features',
    question: 'What is the AI Strategy Suite?',
    answer: 'The AI Strategy Suite includes:\n\n- **Pine Script AI Fixer**: Paste your broken Pine Script, get a corrected version with an explanation\n- **Strategy Analyzer**: Get feedback on your strategy logic, risk-reward profile, and improvement suggestions\n- **AI Trading Coach** (Enterprise): Personalized advice, bias detection, and strategy refinement\n\nAvailable on Pro and Enterprise plans.',
    category: 'features',
  },
  {
    id: 'position-sizing',
    question: 'How does position sizing work?',
    answer: 'Each account can have its own sizing mode:\n\n- **Fixed**: Always use the same lot size (e.g., 0.1 lots)\n- **% of Balance**: Size scales with your account balance\n- **% of Equity**: Size scales with real-time equity\n- **Risk-Based** (most advanced): Lot size calculated from your risk % and stop loss distance — wider stop = smaller size, tighter stop = larger size\n\nYou can also set a max position size cap so no single order ever exceeds your limit.',
    category: 'features',
  },
  {
    id: 'symbol-mapping',
    question: 'Does Tradeflow handle symbol name differences between brokers?',
    answer: 'Yes. Symbol mapping is built in. When your TradingView alert fires for "US30", Tradeflow automatically maps it to the correct symbol format for each of your connected brokers. You can also create custom aliases for any symbol on any broker.',
    category: 'features',
  },
  // Getting Started
  {
    id: 'how-to-start',
    question: 'How do I get started?',
    answer: '1. **Sign up** for a free account (no credit card needed)\n2. **Connect** your broker account from the Accounts page\n3. **Copy** your webhook URL from the dashboard\n4. **Create** alerts in TradingView using your webhook URL\n5. **Configure** risk management and Signal Intelligence settings\n6. **Done!** Trades execute automatically\n\nThe whole setup takes about 5 minutes.',
    category: 'getting-started',
  },
  {
    id: 'tradingview-required',
    question: 'Do I need TradingView?',
    answer: 'TradingView is the most common signal source, but Tradeflow works with any system that can send webhooks. This includes custom scripts, other trading platforms, or any service that can make HTTP requests.',
    category: 'getting-started',
  },
  {
    id: 'webhook-format',
    question: 'What format does the webhook payload need to be?',
    answer: 'Your webhook payload should be a JSON object with these fields:\n\n```\n{\n  "action": "buy",\n  "symbol": "EURUSD",\n  "quantity": 0.1,\n  "sl": 1.0800,\n  "tp": 1.0950\n}\n```\n\nOnly `action` and `symbol` are required. Your webhook key authenticates the request — add it as a URL parameter or in the payload. TradingView variables like `{{ticker}}` and `{{close}}` work natively.',
    category: 'getting-started',
  },
  // Support
  {
    id: 'support-options',
    question: 'What support do you offer?',
    answer: 'All plans include email support. Pro users get priority email support (24h response). Enterprise users get dedicated account management and direct access to our engineering team.\n\nWe also have comprehensive documentation, guides, and FAQ content.',
    category: 'support',
  },
  {
    id: 'signal-rejected',
    question: 'Why was my signal rejected?',
    answer: 'Signals can be rejected for several reasons:\n\n- **Risk limit hit**: Daily loss, daily trade count, max drawdown, or max positions exceeded\n- **Signal too old**: Staleness guard rejected a signal that arrived late\n- **Momentum warning**: Signal Intelligence detected market chop and you chose to discard\n- **Position limit**: You already have the maximum positions open for that symbol\n- **Outside trading hours**: Signal arrived outside your configured session\n\nCheck the Signal Log in your dashboard for the exact rejection reason on each signal.',
    category: 'support',
  },
  // Security
  {
    id: 'security',
    question: 'Is my data secure?',
    answer: 'Yes! We use:\n\n- **AES-256 encryption** for all credentials\n- **TLS/SSL** for all connections\n- We never store your trading passwords in plaintext\n- Your broker credentials are encrypted at rest and never exposed in logs\n\nYour credentials can only be used for trade execution on your behalf.',
    category: 'security',
  },
  {
    id: 'api-access',
    question: 'Do you have API access?',
    answer: 'Yes! All plans include API access for programmatic signal submission. You can integrate Tradeflow into your custom trading systems or any application that can make HTTP requests.',
    category: 'features',
  },
  {
    id: 'trading-analytics',
    question: 'What analytics and performance tracking is included?',
    answer: 'Tradeflow includes a comprehensive Trading Analytics Dashboard:\n\n**Performance Metrics**\n- Win rate, profit factor, expectancy\n- Sharpe ratio, max drawdown\n- Average win/loss, largest win/loss\n- Per-strategy performance breakdown\n\n**Time-Based Analysis**\n- Hourly performance heatmap\n- Daily/weekly performance stats\n- Session analysis (Asian, London, NY overlap)\n\nDiscover your best trading hours and optimize your schedule based on real data.',
    category: 'features',
  },
  {
    id: 'circuit-breakers',
    question: 'What are Circuit Breakers?',
    answer: 'Circuit Breakers automatically pause trading when risk limits are hit:\n\n**Daily Loss Limit**\n- Set a $ or % daily loss limit\n- Trading pauses automatically when reached\n\n**Consecutive Losses**\n- Pause after X consecutive losing trades\n- Prevents tilt trading\n\n**Auto Resume**\n- Optional cooling period before resuming\n- Or manually resume when ready\n\nThink of it as your automated risk manager that never sleeps.',
    category: 'features',
  },
  {
    id: 'news-filter',
    question: 'Can I pause trading around news events?',
    answer: 'Yes! The News Event Filter automatically pauses trading around high-impact economic events:\n\n**Supported Events**\n- FOMC meetings\n- Non-Farm Payroll (NFP)\n- CPI releases\n- Central bank decisions (ECB, BOE, BOJ)\n\n**Configurable Settings**\n- Minutes before event to pause\n- Minutes after event to resume\n- Filter by impact level (high/medium/low)\n\nNever get caught in a volatile news spike again.',
    category: 'features',
  },
  {
    id: 'correlation-filter',
    question: 'What is the Correlation Filter?',
    answer: 'The Correlation Filter prevents you from taking highly correlated trades simultaneously:\n\n**Example**: If you\'re long ES (S&P 500 futures), and a signal comes in to go long NQ (Nasdaq futures), the system knows they\'re 92% correlated and blocks the NQ signal.\n\n**Why it matters**:\n- Reduces concentrated risk exposure\n- Prevents "doubling down" on the same market move\n- Built-in correlations for major pairs (ES/NQ, EUR/GBP, Gold/Silver, etc.)\n\nSmarter position management, automatically.',
    category: 'features',
  },
  {
    id: 'dynamic-sizing',
    question: 'Does Tradeflow support dynamic position sizing?',
    answer: 'Yes! Dynamic Position Sizing automatically adjusts your trade size based on performance:\n\n**Streak-Based Sizing**\n- Increase size after consecutive wins\n- Decrease size after consecutive losses\n\n**Equity Curve Trading**\n- Reduce size when equity drops below moving average\n- Scale back up when equity curve recovers\n\nThis helps you ride winning streaks and protect capital during drawdowns.',
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
            onClick={() => window.location.href = 'mailto:support@mytradeflow.app'}
          >
            <MessageCircle className="h-4 w-4 mr-2" />
            Contact Sales
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
