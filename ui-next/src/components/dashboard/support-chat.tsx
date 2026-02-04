'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  HelpCircle,
  MessageCircle,
  Send,
  Bot,
  User,
  Loader2,
  Mail,
  CheckCircle,
  Sparkles,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

// ============================================================================
// TRADEFLOW KNOWLEDGE BASE - COMPREHENSIVE SYSTEM DOCUMENTATION
// ============================================================================

const KNOWLEDGE_BASE = {
  // Core Platform
  platform: {
    name: 'Tradeflow',
    description: 'Automated trading signal router that connects TradingView alerts (or any webhook source) to broker accounts for automatic trade execution.',
    website: 'mytradeflow.app',
    supportEmail: 'support@mytradeflow.app',
  },

  // Subscription Tiers (matches lib/pricing.ts)
  tiers: {
    free: {
      name: 'Free',
      price: 0,
      features: ['1 broker connection', '50 signals/day', '1 webhook', 'Basic signal routing', 'Fixed lot sizing', '7-day webhook logs', 'Community support'],
    },
    tier_1: {
      name: 'Starter',
      price: 29,
      features: ['1 broker connection', '100 signals/day', '2 webhooks', 'Staleness guard protection', 'Daily trade limits', 'Fixed lot sizing', 'Email support (48h)'],
    },
    tier_2: {
      name: 'Trader',
      price: 59,
      features: ['2 broker connections', 'Unlimited signals', '5 webhooks', 'All 5 AI Signal Guards', 'Full risk management', 'Drawdown protection', '% of balance sizing', 'Symbol mapping', '2 account groups', 'Email support (24h)'],
    },
    tier_3: {
      name: 'Pro',
      price: 99,
      features: ['4 broker connections', 'Unlimited signals & webhooks', 'AI Guards + custom thresholds', 'Risk-based position sizing', 'Advanced rule-based routing', 'AI Strategy Suite', 'API access', '30-day webhook logs', 'Priority support (12h)'],
    },
    tier_4: {
      name: 'Enterprise',
      price: 199,
      features: ['8 broker connections', 'Everything in Pro', 'AI Strategy Suite + AI Coach', 'Pine Script AI Fixer', 'Custom risk profiles per account', 'Strategy-based routing', 'Bulk symbol import/export', '90-day webhook logs', 'SMS & push notifications', 'Priority support + live chat'],
    },
  },

  // Supported Brokers
  brokers: {
    mt5: {
      name: 'MetaTrader 5',
      description: 'Professional forex and CFD trading platform',
      setup: 'Go to Settings > Accounts > Add Account > Select MT5. Enter your MetaAPI account ID or create a new provisioned account.',
      symbols: ['XAUUSD', 'EURUSD', 'GBPUSD', 'BTCUSD', 'ETHUSD'],
      features: ['All order types', 'Trailing stops', 'Hedge mode'],
    },
    mt4: {
      name: 'MetaTrader 4',
      description: 'Classic forex trading platform',
      setup: 'Go to Settings > Accounts > Add Account > Select MT4. Similar to MT5 setup via MetaAPI.',
      symbols: ['XAUUSD', 'EURUSD', 'GBPUSD'],
      features: ['Market orders', 'Pending orders', 'Stop loss/Take profit'],
    },
    tradelocker: {
      name: 'TradeLocker',
      description: 'Modern prop firm compatible trading platform',
      setup: 'Go to Settings > Accounts > Add Account > Select TradeLocker. Enter API credentials from your TradeLocker dashboard.',
      symbols: ['BTCUSD', 'XAUUSD', 'EURUSD', 'ETHUSD'],
      features: ['All order types', 'Real-time updates', 'Bracket orders'],
    },
    projectx: {
      name: 'ProjectX/TopStep',
      description: 'Futures trading for prop firm evaluation',
      setup: 'Go to Settings > Accounts > Add Account > Select ProjectX. Connect with your TopStep credentials.',
      symbols: ['MNQ', 'MES', 'ES', 'NQ'],
      features: ['Futures trading', 'Micro contracts', 'Bracket orders'],
    },
    tradovate: {
      name: 'Tradovate',
      description: 'Commission-free futures trading',
      setup: 'Go to Settings > Accounts > Add Account > Select Tradovate. Connect via OAuth.',
      symbols: ['MNQ', 'MES', 'ES'],
      features: ['Futures trading', 'Real-time data'],
    },
  },

  // Webhook Configuration
  webhooks: {
    url_format: 'https://api.mytradeflow.app/api/v1/webhook/signal/{YOUR_WEBHOOK_KEY}',
    payload_format: {
      required: ['action', 'symbol'],
      optional: ['quantity', 'price', 'stop_loss', 'take_profit', 'account_id', 'comment', 'order_type', 'trailing_stop', 'sl', 'tp'],
      actions: ['buy', 'sell', 'close', 'close_all', 'cancel'],
      order_types: ['market', 'limit', 'stop', 'stop_limit', 'bracket', 'trailing_stop'],
    },
    examples: {
      buy: '{"action": "buy", "symbol": "EURUSD", "quantity": 0.1}',
      sell: '{"action": "sell", "symbol": "XAUUSD", "quantity": 0.05, "stop_loss": 2050, "take_profit": 2100}',
      close: '{"action": "close", "symbol": "EURUSD"}',
      bracket: '{"action": "buy", "symbol": "MNQ", "quantity": 1, "stop_loss": 50, "take_profit": 100}',
      trailing: '{"action": "buy", "symbol": "BTCUSD", "quantity": 0.01, "trailing_stop": 200}',
      futures: '{"action": "buy", "symbol": "MNQ", "quantity": 1}',
      with_sl_tp: '{"action": "buy", "symbol": "EURUSD", "quantity": 0.1, "sl": 1.0850, "tp": 1.0950}',
    },
  },

  // Signal Routing Configuration
  signal_routing: {
    description: 'Route signals to specific accounts based on source, symbol, or custom rules',
    features: [
      'Route by signal source (TradingView, custom)',
      'Route by symbol (forex, crypto, futures)',
      'Route by account (specific broker accounts)',
      'Multi-account broadcasting (same signal to multiple accounts)',
      'Webhook configs for advanced routing',
    ],
    examples: {
      single_account: {
        description: 'Send signal to one specific account',
        payload: '{"action": "buy", "symbol": "EURUSD", "quantity": 0.1, "account_id": 123}',
      },
      multi_account: {
        description: 'Send to all accounts subscribed to the webhook key',
        payload: '{"action": "buy", "symbol": "BTCUSD", "quantity": 0.01}',
      },
      by_broker: {
        description: 'Use different webhook keys for different brokers',
        note: 'Create separate webhook configs for MT5, TradeLocker, etc.',
      },
    },
    setup_steps: [
      '1. Go to Settings > Signal Routing',
      '2. Create a new Webhook Config',
      '3. Set source filter (e.g., "tradingview")',
      '4. Select target accounts',
      '5. Optionally set symbol filters',
      '6. Save and use the generated webhook URL',
    ],
  },

  // AI Guards (FlowGuard AI)
  ai_guards: {
    description: 'Protective filters that analyze signals before execution to manage risk',
    guards: {
      staleness: {
        name: 'Staleness Guard',
        description: 'Rejects signals older than configured threshold (default 30 seconds)',
        configurable: true,
      },
      duplicate: {
        name: 'Duplicate Guard',
        description: 'Prevents double entries within time window',
        configurable: true,
      },
      drawdown: {
        name: 'Drawdown Guard',
        description: 'Stops trading when daily loss limit exceeded',
        configurable: true,
      },
      position_size: {
        name: 'Position Size Guard',
        description: 'Limits maximum position size per trade',
        configurable: true,
      },
      frequency: {
        name: 'Frequency Guard',
        description: 'Limits number of trades per time period',
        configurable: true,
      },
      momentum: {
        name: 'Momentum Guard (Chop Detector)',
        description: 'Detects choppy markets by tracking opposite signals - pauses trading when threshold exceeded',
        configurable: true,
      },
      exposure: {
        name: 'Exposure Guard',
        description: 'Limits total exposure across all positions to prevent over-leveraging',
        configurable: true,
      },
    },
  },

  // Signal Intelligence (Advanced AI Guards)
  signal_intelligence: {
    description: 'Advanced AI-powered signal analysis that protects profitable positions and detects market conditions',
    features: {
      position_pnl_protection: {
        name: 'Position P&L Protection',
        description: 'Warns or blocks signals that would open opposite positions against currently profitable trades',
        modes: {
          warn: 'Shows warning but allows signal to proceed (default)',
          block: 'Automatically rejects signals that would reverse profitable positions',
        },
        example: 'If you have a profitable LONG position in XAUUSD and a SELL signal comes in, the system warns/blocks to protect your gains',
        location: 'Settings > Accounts > Edit > Signal Intelligence tab',
        tier: 'Trader tier and above',
      },
      momentum_flip_detection: {
        name: 'Momentum Flip Detection',
        description: 'Tracks market momentum and detects when signals flip too frequently (choppy conditions)',
        how_it_works: [
          'Tracks buy/sell signal ratio over configurable window',
          'When opposite signals exceed threshold, triggers warning or pause',
          'Helps avoid whipsaws in ranging markets',
        ],
        configurable: ['Window period (minutes)', 'Flip threshold count', 'Cooldown period'],
        location: 'Settings > Accounts > Edit > Signal Intelligence tab',
        tier: 'Trader tier and above',
      },
      daily_trade_limits: {
        name: 'Daily Trade Limits',
        description: 'Limit number of trades per day per symbol to prevent overtrading',
        location: 'Settings > Accounts > Edit > Risk Management',
        tier: 'Starter tier and above',
      },
    },
  },

  // Symbol-Specific Settings
  symbol_settings: {
    description: 'Configure custom stop loss, take profit, and position sizing for individual trading symbols',
    features: {
      per_symbol_sl_tp: {
        name: 'Per-Symbol SL/TP Override',
        description: 'Set different default SL/TP values for specific symbols. Overrides account-level defaults.',
        example: 'Set XAUUSD to use 200 points SL while EURUSD uses 30 pips SL',
        unit_types: ['pips', 'points', 'percent', 'price'],
      },
      position_size_override: {
        name: 'Position Size Override',
        description: 'Set fixed lot/contract size for specific symbols',
        example: 'Always trade 0.1 lots on XAUUSD regardless of risk calculations',
      },
      max_positions_per_symbol: {
        name: 'Max Positions per Symbol',
        description: 'Limit how many simultaneous positions can be open for a specific symbol',
        example: 'Allow max 2 positions on EURUSD to prevent over-exposure to single pair',
      },
    },
    location: 'Settings > Accounts > Edit > Symbol SL/TP tab',
    tier: 'Trader tier and above',
    setup_steps: [
      '1. Go to Settings > Accounts',
      '2. Click Edit on your account',
      '3. Navigate to "Symbol SL/TP" tab',
      '4. Click "Add Symbol" button',
      '5. Enter symbol name (e.g., XAUUSD)',
      '6. Configure SL, TP, position size, or max positions',
      '7. Click Save',
    ],
  },

  // Symbol Blocking
  symbol_blocking: {
    description: 'Allow or block specific symbols from executing trades',
    modes: {
      allow_all: 'All symbols allowed (default)',
      allow_list: 'Only trade symbols in the allowed list',
      block_list: 'Trade all symbols except those in the blocked list',
    },
    use_cases: [
      'Block volatile symbols during news events',
      'Only allow specific forex pairs for focused strategy',
      'Prevent accidental trades on unfamiliar instruments',
    ],
    location: 'Settings > Accounts > Edit > Signal Routing tab',
    tier: 'Trader tier and above',
  },

  // Risk Management Features
  risk_management: {
    description: 'Comprehensive risk management enforced per broker',
    features: {
      stop_loss: {
        name: 'Stop Loss (SL)',
        description: 'Automatic stop loss on every trade. Can be set in pips, points, or percentage.',
        supported_brokers: ['MT5', 'MT4', 'TradeLocker', 'ProjectX', 'Tradovate'],
        webhook_field: 'stop_loss or sl',
        example: '{"action": "buy", "symbol": "EURUSD", "sl": 1.0850}',
      },
      take_profit: {
        name: 'Take Profit (TP)',
        description: 'Automatic take profit on every trade. Can be set in pips, points, or percentage.',
        supported_brokers: ['MT5', 'MT4', 'TradeLocker', 'ProjectX', 'Tradovate'],
        webhook_field: 'take_profit or tp',
        example: '{"action": "buy", "symbol": "EURUSD", "tp": 1.0950}',
      },
      trailing_stop: {
        name: 'Trailing Stop',
        description: 'Dynamic stop that follows price movement',
        supported_brokers: ['MT5', 'TradeLocker', 'ProjectX'],
        webhook_field: 'trailing_stop',
        example: '{"action": "buy", "symbol": "BTCUSD", "trailing_stop": 50}',
      },
      account_defaults: {
        name: 'Account Risk Defaults',
        description: 'Set default SL/TP per account. Auto-calculated if webhook doesn\'t include SL/TP.',
        location: 'Settings > Accounts > Edit > Risk Management > Default Stop Loss & Take Profit',
        unit_types: 'Choose between Pips (forex), Points (futures), or Percentage (% of entry price)',
      },
      partial_tp: {
        name: 'Partial Take Profit',
        description: 'Close portions of position at multiple TP levels (1:1, 1:2, 1:3, etc.)',
        location: 'Settings > Accounts > Edit > Risk Management > Partial TP',
        tier: 'Pro tier and above',
      },
      platform_managed: {
        name: 'Platform-Managed SL/TP',
        description: 'TradeFlow monitors positions and triggers closes instead of relying on broker',
        use_case: 'Useful for brokers with unreliable SL/TP execution',
      },
    },
    position_sizing: {
      description: 'Choose how position sizes are calculated for your trades',
      modes: {
        fixed: {
          name: 'Fixed Lot Size',
          description: 'Use a constant lot/contract size for all trades',
          example: 'Always trade 0.1 lots regardless of account balance or risk',
          tier: 'All tiers',
        },
        percent_balance: {
          name: 'Percent of Balance',
          description: 'Position size as a percentage of account balance',
          example: '2% of $10,000 balance = $200 position value',
          tier: 'Trader tier and above',
        },
        risk_percent: {
          name: 'Risk-Based Sizing',
          description: 'Calculate position size based on risk per trade and stop loss distance',
          example: 'Risk 1% of account per trade with 50 pip SL = position size auto-calculated',
          tier: 'Pro tier and above',
        },
      },
      location: 'Settings > Accounts > Edit > Risk Management > Position Size Mode',
    },
    daily_limits: {
      daily_loss_limit: {
        name: 'Daily Loss Limit',
        description: 'Maximum loss allowed per day before trading is paused',
        example: 'Set to $500 - trading stops when daily P&L reaches -$500',
        location: 'Settings > Accounts > Edit > Risk Management',
      },
      max_daily_drawdown: {
        name: 'Max Daily Drawdown %',
        description: 'Maximum percentage drawdown allowed per day',
        example: 'Set to 3% - trading stops when account drops 3% from daily starting balance',
        location: 'Settings > Accounts > Edit > Risk Management',
      },
      max_positions: {
        name: 'Max Positions per Symbol',
        description: 'Limit simultaneous positions on any single symbol',
        example: 'Set to 2 - no more than 2 XAUUSD positions at once',
        location: 'Settings > Accounts > Edit > Risk Management',
      },
    },
    unit_types: {
      pips: 'Default for forex. 1 pip = 0.0001 for most pairs, 0.01 for JPY pairs',
      points: 'Default for futures. 1 point = minimum tick size (e.g., 0.25 for ES)',
      percent: 'SL/TP as percentage of entry price. Example: 1% SL means SL is 1% below entry for buys',
    },
    broker_specifics: {
      futures: 'ProjectX, TopStep, Tradovate use bracket orders for SL/TP (whole contracts only)',
      forex: 'MT5, MT4, TradeLocker use standard SL/TP (fractional lots like 0.01)',
    },
  },

  // Prop Firm Rules
  prop_rules: {
    description: 'Configure rules for prop firm challenge and funded account compliance',
    features: {
      challenge_tracking: {
        name: 'Challenge Rule Tracking',
        description: 'Track daily loss limits and drawdown rules specific to your prop firm',
        supported_firms: ['FTMO', 'MyForexFunds', 'Funded Next', 'TopStep', 'Custom'],
      },
      auto_pause: {
        name: 'Auto-Pause on Limit',
        description: 'Automatically pause trading when prop firm limits are approached',
        example: 'Pause trading at 4% daily loss if firm limit is 5%',
      },
      trailing_drawdown: {
        name: 'Trailing Drawdown Support',
        description: 'Track trailing drawdown rules used by firms like TopStep',
        how_it_works: 'Monitors high water mark and pauses if drawdown limit is reached',
      },
    },
    location: 'Settings > Accounts > Edit > Risk Management > Prop Firm Rules',
    tier: 'Trader tier and above',
  },

  // Symbol Mapping
  symbol_mapping: {
    description: 'Maps TradingView symbols to broker-specific symbols',
    examples: {
      'XAUUSD → GOLD': 'Some brokers use GOLD instead of XAUUSD',
      'BTCUSD → BTCUSDT': 'Crypto symbol variations',
      'US500 → SPX500': 'Index symbol variations',
    },
    setup: 'Go to Settings > Symbol Mapping > Add new mapping',
  },

  // Common Issues & Solutions
  troubleshooting: {
    'trade_not_executing': {
      problem: 'Trades not executing',
      solutions: [
        'Verify webhook key is correct',
        'Check broker connection status',
        'Ensure JSON payload is valid',
        'Verify symbol exists on broker',
        'Check account has sufficient margin',
        'Review webhook logs for errors',
      ],
    },
    'broker_disconnected': {
      problem: 'Broker showing disconnected',
      solutions: [
        'Check broker credentials',
        'Verify trading server is online',
        'Ensure account is not locked/expired',
        'Try reconnecting from Settings > Accounts',
      ],
    },
    'signal_rejected': {
      problem: 'Signal rejected by AI Guards',
      solutions: [
        'Check Webhook Logs for the rejection reason',
        'Adjust guard thresholds if too strict',
        'Verify signal timestamp is current',
        'Check daily loss limits',
      ],
    },
    'symbol_not_found': {
      problem: 'Symbol not found error',
      solutions: [
        'Use Symbol Mapping to translate symbols',
        'Check broker-specific symbol name',
        'Verify market is open for that symbol',
      ],
    },
    'market_closed': {
      problem: 'Market closed error',
      solutions: [
        'Wait for market hours',
        'Use crypto symbols (BTCUSD, ETHUSD) for 24/7 trading',
        'Check holiday schedules',
      ],
    },
    'pending_confirmation': {
      problem: 'Signal shows "Pending Confirmation"',
      solutions: [
        'Enable auto-confirm in account settings',
        'Or manually approve signals in the dashboard',
        'Settings > Accounts > Edit > Enable Auto-Execute',
      ],
    },
    'invalid_order_size': {
      problem: 'Invalid order size error',
      solutions: [
        'Futures brokers require whole contracts (1, 2, 3...)',
        'Set quantity to at least 1 for ProjectX/Tradovate',
        'Forex brokers accept fractional lots (0.01, 0.1)',
      ],
    },
    'not_enough_margin': {
      problem: 'Not enough margin error',
      solutions: [
        'Reduce position size',
        'Add funds to broker account',
        'Close existing positions to free margin',
      ],
    },
    'exposure_limit': {
      problem: 'Exposure limit reached',
      solutions: [
        'Close some existing positions',
        'Increase exposure limit in Settings > AI Guards',
        'Wait for positions to close',
      ],
    },
    'chop_mode': {
      problem: 'Trading paused due to chop detection',
      solutions: [
        'Wait for market to trend (clear direction)',
        'Reduce opposite signal threshold in AI Guards',
        'Check signal_counters table for momentum status',
      ],
    },
    'missing_credentials': {
      problem: 'Could not create executor / Missing credentials',
      solutions: [
        'Go to Settings > Accounts',
        'Edit the account and re-enter credentials',
        'Verify API keys are correct',
      ],
    },
  },

  // Common Rejection Reasons Reference
  rejection_reasons: {
    'Awaiting manual confirmation': 'Auto-execute is disabled. Enable in account settings or approve manually.',
    'Invalid order size': 'Quantity too small for broker. Futures need whole contracts (1+).',
    'Insufficient margin': 'Not enough funds in broker account for this trade size.',
    'Market closed': 'Trading hours have ended. Check market schedule.',
    'Symbol not found': 'Broker does not recognize this symbol. Set up symbol mapping.',
    'Daily exposure limit reached': 'Risk limit hit. Close positions or increase limit.',
    'Signal too old': 'Signal delayed in transit. Check network/TradingView latency.',
    'Broker connection failed': 'Cannot connect to broker. Verify credentials.',
    'Missing broker credentials': 'No API keys configured for this account.',
    'Chop mode active': 'Market is choppy (alternating buy/sell). Trading paused.',
  },

  // Trading Session Control
  trading_sessions: {
    description: 'Define your active trading hours and days. Signals outside your session are automatically paused.',
    features: [
      'Set trading hours (start/end time)',
      'Select active trading days (Mon-Sun)',
      'Timezone support',
      'Automatic signal pausing outside session',
      'Per-account session configuration',
    ],
    location: 'Settings > Accounts > Edit > Trading Session',
    access: 'Available on Trader tier and above',
    presets: [
      'London Session (08:00-17:00 GMT)',
      'New York Session (13:00-22:00 GMT)',
      'Asian Session (00:00-09:00 GMT)',
      'Custom hours',
    ],
  },

  // Position Management
  position_management: {
    description: 'View and manage positions across all connected brokers from one dashboard',
    features: [
      'Real-time position monitoring',
      'One-click position close',
      'View P&L per position',
      'Close all positions by account',
      'Position grouping by symbol/broker',
    ],
    location: 'Dashboard > Positions widget (or Settings > Accounts)',
    access: 'Available on all tiers',
  },

  // AI Strategy Suite
  ai_suite: {
    description: 'Advanced AI-powered trading tools for strategy development and analysis',
    features: [
      'Strategy Builder - Create custom trading strategies with Pine Script',
      'Pine Script AI Fixer - Get AI-powered fixes for your Pine Script code',
      'Backtesting - Test strategies on historical data',
      'Signal Analysis - AI-powered signal quality scoring',
      'Risk Assessment - Portfolio risk analysis',
    ],
    access: 'Available on Pro tier and above',
  },

  // AI Trading Coach
  ai_coach: {
    description: 'Get intelligent feedback on your trading strategies with bias detection and improvement suggestions',
    features: [
      'Strategy review and feedback',
      'Bias detection (overtrading, revenge trading, etc.)',
      'Performance analysis',
      'Improvement suggestions',
      'Risk assessment feedback',
    ],
    access: 'Available on Enterprise tier only',
    location: 'Dashboard > AI Suite > AI Coach',
  },

  // Quick Start Guide
  quickstart: {
    steps: [
      '1. Sign up and verify your email',
      '2. Generate a webhook key from the dashboard',
      '3. Connect your broker account(s) in Settings > Accounts',
      '4. (Optional) Set up symbol mappings if needed',
      '5. Configure AI Guards to your risk preferences',
      '6. Set up alerts in TradingView with your webhook URL',
      '7. Test with a small trade to verify everything works',
    ],
  },
};

// ============================================================================
// AI RESPONSE GENERATION
// ============================================================================

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

function generateAIResponse(question: string): { response: string; needsHuman: boolean } {
  const q = question.toLowerCase();
  let response = '';
  let needsHuman = false;

  // Greeting detection
  if (q.match(/^(hi|hello|hey|good morning|good afternoon|good evening)/)) {
    return {
      response: `Hello! 👋 I'm TradeBot, your Tradeflow support assistant. I can help you with:\n\n• Setting up webhooks and broker connections\n• Understanding AI Guards and risk management\n• Troubleshooting signal execution issues\n• Explaining features and pricing\n\nWhat would you like to know?`,
      needsHuman: false,
    };
  }

  // What is Tradeflow / Platform overview
  if (q.includes('what is tradeflow') || q.includes('what does tradeflow do') || q.includes('how does tradeflow work')) {
    return {
      response: `**Tradeflow** is an automated trading signal router that connects your TradingView alerts (or any webhook source) to your broker accounts.\n\n**How it works:**\n1. You set up alerts in TradingView or another platform\n2. Alerts send webhook signals to your unique Tradeflow URL\n3. Tradeflow validates the signal through AI Guards\n4. If approved, the trade executes automatically on your broker\n\n**Supported brokers:** MT4/MT5, TradeLocker, ProjectX/TopStep, Tradovate\n\nWould you like help getting started?`,
      needsHuman: false,
    };
  }

  // Getting started / How to start
  if (q.includes('get started') || q.includes('how to start') || q.includes('new user') || q.includes('setup') || q.includes('quickstart')) {
    return {
      response: `**Quick Start Guide:**\n\n${KNOWLEDGE_BASE.quickstart.steps.join('\n')}\n\n**Need help with a specific step?** Just ask about:\n• Webhook setup\n• Connecting brokers\n• TradingView integration\n• Testing your first trade`,
      needsHuman: false,
    };
  }

  // Pricing / Tiers / Plans
  if (q.includes('price') || q.includes('pricing') || q.includes('cost') || q.includes('tier') || q.includes('plan') || q.includes('subscription')) {
    const tiers = Object.entries(KNOWLEDGE_BASE.tiers)
      .filter(([key]) => key !== 'free')
      .map(([_, tier]) => `**${tier.name}** - $${tier.price}/month\n${tier.features.slice(0, 3).join(', ')}`)
      .join('\n\n');
    return {
      response: `**Tradeflow Pricing:**\n\n**Free** - $0/month\n${KNOWLEDGE_BASE.tiers.free.features.join(', ')}\n\n${tiers}\n\nAll paid plans include a 7-day free trial. Upgrade anytime from Settings > Billing.`,
      needsHuman: false,
    };
  }

  // Webhook questions
  if (q.includes('webhook')) {
    if (q.includes('url') || q.includes('endpoint') || q.includes('address')) {
      return {
        response: `**Your Webhook URL:**\n\n\`${KNOWLEDGE_BASE.webhooks.url_format}\`\n\nReplace \`{YOUR_WEBHOOK_KEY}\` with your actual key from the Dashboard or Settings > Webhooks.\n\n**TradingView Setup:**\n1. Create an alert in TradingView\n2. Set "Webhook URL" to your Tradeflow URL\n3. Set the message to your JSON payload`,
        needsHuman: false,
      };
    }
    if (q.includes('format') || q.includes('payload') || q.includes('json')) {
      return {
        response: `**Webhook Payload Format:**\n\n**Required fields:** action, symbol\n**Optional fields:** quantity, price, stop_loss, take_profit, order_type, comment\n\n**Examples:**\n\nBuy: \`${KNOWLEDGE_BASE.webhooks.examples.buy}\`\n\nSell with SL/TP: \`${KNOWLEDGE_BASE.webhooks.examples.sell}\`\n\nClose position: \`${KNOWLEDGE_BASE.webhooks.examples.close}\`\n\n**Actions:** buy, sell, close, close_all, cancel`,
        needsHuman: false,
      };
    }
    if (q.includes('test')) {
      return {
        response: `**Testing Your Webhook:**\n\n1. Go to the Dashboard\n2. Select a broker account from the dropdown\n3. Choose a symbol (crypto like BTCUSD works 24/7)\n4. Click "Test" button\n5. The test opens and closes a small position\n\n**Tips:**\n• Use crypto symbols for weekend testing\n• Check webhook logs for detailed results\n• Start with paper/demo accounts`,
        needsHuman: false,
      };
    }
    return {
      response: `**Webhook Overview:**\n\nWebhooks allow TradingView (or any platform) to send trading signals to Tradeflow.\n\n**Your webhook URL:** \`${KNOWLEDGE_BASE.webhooks.url_format}\`\n\n**Basic payload:**\n\`{"action": "buy", "symbol": "EURUSD", "quantity": 0.1}\`\n\n**What would you like to know?**\n• Webhook URL setup\n• Payload format\n• Testing webhooks\n• TradingView integration`,
      needsHuman: false,
    };
  }

  // Broker questions
  if (q.includes('broker') || q.includes('mt4') || q.includes('mt5') || q.includes('metatrader') || q.includes('tradelocker') || q.includes('projectx') || q.includes('topstep') || q.includes('tradovate')) {
    // Specific broker
    if (q.includes('mt5') || q.includes('metatrader 5')) {
      const broker = KNOWLEDGE_BASE.brokers.mt5;
      return {
        response: `**${broker.name}**\n\n${broker.description}\n\n**Setup:**\n${broker.setup}\n\n**Available symbols:** ${broker.symbols.join(', ')}\n\n**Features:** ${broker.features.join(', ')}`,
        needsHuman: false,
      };
    }
    if (q.includes('mt4') || q.includes('metatrader 4')) {
      const broker = KNOWLEDGE_BASE.brokers.mt4;
      return {
        response: `**${broker.name}**\n\n${broker.description}\n\n**Setup:**\n${broker.setup}\n\n**Available symbols:** ${broker.symbols.join(', ')}`,
        needsHuman: false,
      };
    }
    if (q.includes('tradelocker')) {
      const broker = KNOWLEDGE_BASE.brokers.tradelocker;
      return {
        response: `**${broker.name}**\n\n${broker.description}\n\n**Setup:**\n${broker.setup}\n\n**Available symbols:** ${broker.symbols.join(', ')}\n\n**Features:** ${broker.features.join(', ')}`,
        needsHuman: false,
      };
    }
    if (q.includes('projectx') || q.includes('topstep')) {
      const broker = KNOWLEDGE_BASE.brokers.projectx;
      return {
        response: `**${broker.name}**\n\n${broker.description}\n\n**Setup:**\n${broker.setup}\n\n**Available symbols:** ${broker.symbols.join(', ')}\n\n**Features:** ${broker.features.join(', ')}\n\n**Note:** Great for prop firm evaluations!`,
        needsHuman: false,
      };
    }
    if (q.includes('tradovate')) {
      const broker = KNOWLEDGE_BASE.brokers.tradovate;
      return {
        response: `**${broker.name}**\n\n${broker.description}\n\n**Setup:**\n${broker.setup}\n\n**Available symbols:** ${broker.symbols.join(', ')}`,
        needsHuman: false,
      };
    }
    // Connect broker
    if (q.includes('connect') || q.includes('add') || q.includes('setup')) {
      return {
        response: `**Connecting a Broker Account:**\n\n1. Go to **Settings > Accounts**\n2. Click **"Add Account"**\n3. Select your broker type\n4. Enter your credentials/API keys\n5. Click **"Connect"**\n\n**Supported Brokers:**\n• MT4/MT5 (via MetaAPI)\n• TradeLocker\n• ProjectX/TopStep\n• Tradovate\n\nWhich broker would you like help with?`,
        needsHuman: false,
      };
    }
    // Disconnected
    if (q.includes('disconnect') || q.includes('not working') || q.includes('offline')) {
      const solutions = KNOWLEDGE_BASE.troubleshooting.broker_disconnected.solutions;
      return {
        response: `**Broker Disconnected?**\n\nTry these steps:\n\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\nIf the issue persists, it may be a broker-side problem. Check their status page or contact your broker.`,
        needsHuman: false,
      };
    }
    // General broker info
    return {
      response: `**Supported Brokers:**\n\n• **MT4/MT5** - Forex & CFDs via MetaAPI\n• **TradeLocker** - Prop firm compatible\n• **ProjectX/TopStep** - Futures prop trading\n• **Tradovate** - Commission-free futures\n\nYou can connect multiple accounts and route signals to specific ones.\n\n**Setup:** Settings > Accounts > Add Account\n\nWhich broker would you like help with?`,
      needsHuman: false,
    };
  }

  // AI Guards / FlowGuard
  if (q.includes('guard') || q.includes('flowguard') || q.includes('ai guard') || q.includes('protection') || q.includes('risk')) {
    if (q.includes('staleness') || q.includes('stale') || q.includes('old signal')) {
      return {
        response: `**Staleness Guard**\n\nRejects signals that are too old (delayed in transit).\n\n**Default:** 30 seconds\n**Configure:** Settings > AI Guards > Staleness threshold\n\n**Why it matters:** Old signals may no longer be valid due to price movement.`,
        needsHuman: false,
      };
    }
    if (q.includes('duplicate') || q.includes('double')) {
      return {
        response: `**Duplicate Guard**\n\nPrevents double entries from duplicate webhook calls.\n\n**How it works:** Tracks recent signals and blocks identical ones within a time window.\n\n**Configure:** Settings > AI Guards > Duplicate window`,
        needsHuman: false,
      };
    }
    if (q.includes('drawdown') || q.includes('loss limit')) {
      return {
        response: `**Drawdown Guard**\n\nStops trading when daily loss limit is exceeded.\n\n**Configure:** Settings > AI Guards > Max daily drawdown\n\n**Example:** Set to 5% - trading pauses when account loses 5% in a day.\n\n**Reset:** Automatically resets each day at midnight UTC.`,
        needsHuman: false,
      };
    }
    return {
      response: `**AI Guards (FlowGuard AI)**\n\n${KNOWLEDGE_BASE.ai_guards.description}\n\n**Available Guards:**\n${Object.values(KNOWLEDGE_BASE.ai_guards.guards).map(g => `• **${g.name}** - ${g.description}`).join('\n')}\n\n**Configure:** Settings > AI Guards\n\nWhich guard would you like to know more about?`,
      needsHuman: false,
    };
  }

  // Signal Intelligence
  if (q.includes('signal intelligence') || q.includes('pnl protection') || q.includes('p&l protection') || q.includes('protect profit') || q.includes('profitable position')) {
    const si = KNOWLEDGE_BASE.signal_intelligence;
    const pnl = si.features.position_pnl_protection;
    return {
      response: `**Signal Intelligence - P&L Protection**\n\n${pnl.description}\n\n**How it works:**\n${pnl.example}\n\n**Modes:**\n• **Warn** - ${pnl.modes.warn}\n• **Block** - ${pnl.modes.block}\n\n**Location:** ${pnl.location}\n\n**Access:** ${pnl.tier}\n\nThis helps prevent accidentally reversing winning positions and locking in losses.`,
      needsHuman: false,
    };
  }

  // Symbol-specific settings
  if ((q.includes('symbol') && (q.includes('specific') || q.includes('setting') || q.includes('override') || q.includes('sl') || q.includes('tp'))) || q.includes('per symbol') || q.includes('per-symbol')) {
    const ss = KNOWLEDGE_BASE.symbol_settings;
    return {
      response: `**Symbol-Specific Settings**\n\n${ss.description}\n\n**Features:**\n• **Per-Symbol SL/TP** - ${ss.features.per_symbol_sl_tp.description}\n  Example: ${ss.features.per_symbol_sl_tp.example}\n\n• **Position Size Override** - ${ss.features.position_size_override.description}\n  Example: ${ss.features.position_size_override.example}\n\n• **Max Positions per Symbol** - ${ss.features.max_positions_per_symbol.description}\n  Example: ${ss.features.max_positions_per_symbol.example}\n\n**Setup:**\n${ss.setup_steps.join('\n')}\n\n**Access:** ${ss.tier}`,
      needsHuman: false,
    };
  }

  // Symbol blocking
  if (q.includes('symbol block') || q.includes('block symbol') || q.includes('allow symbol') || q.includes('whitelist') || q.includes('blacklist')) {
    const sb = KNOWLEDGE_BASE.symbol_blocking;
    return {
      response: `**Symbol Blocking**\n\n${sb.description}\n\n**Modes:**\n• **Allow All** - ${sb.modes.allow_all}\n• **Allow List** - ${sb.modes.allow_list}\n• **Block List** - ${sb.modes.block_list}\n\n**Use Cases:**\n${sb.use_cases.map(uc => `• ${uc}`).join('\n')}\n\n**Location:** ${sb.location}\n\n**Access:** ${sb.tier}`,
      needsHuman: false,
    };
  }

  // Position sizing modes
  if (q.includes('position size') || q.includes('lot size') || q.includes('sizing mode') || q.includes('risk percent') || q.includes('percent balance')) {
    const ps = KNOWLEDGE_BASE.risk_management.position_sizing;
    return {
      response: `**Position Sizing Modes**\n\n${ps.description}\n\n**Available Modes:**\n\n• **Fixed Lot Size** - ${ps.modes.fixed.description}\n  Example: ${ps.modes.fixed.example}\n  Access: ${ps.modes.fixed.tier}\n\n• **Percent of Balance** - ${ps.modes.percent_balance.description}\n  Example: ${ps.modes.percent_balance.example}\n  Access: ${ps.modes.percent_balance.tier}\n\n• **Risk-Based Sizing** - ${ps.modes.risk_percent.description}\n  Example: ${ps.modes.risk_percent.example}\n  Access: ${ps.modes.risk_percent.tier}\n\n**Location:** ${ps.location}`,
      needsHuman: false,
    };
  }

  // Prop firm rules
  if (q.includes('prop') || q.includes('funded') || q.includes('challenge') || q.includes('ftmo') || q.includes('evaluation')) {
    const pr = KNOWLEDGE_BASE.prop_rules;
    return {
      response: `**Prop Firm Rules & Compliance**\n\n${pr.description}\n\n**Features:**\n\n• **${pr.features.challenge_tracking.name}** - ${pr.features.challenge_tracking.description}\n  Supported: ${pr.features.challenge_tracking.supported_firms.join(', ')}\n\n• **${pr.features.auto_pause.name}** - ${pr.features.auto_pause.description}\n  Example: ${pr.features.auto_pause.example}\n\n• **${pr.features.trailing_drawdown.name}** - ${pr.features.trailing_drawdown.description}\n\n**Location:** ${pr.location}\n\n**Access:** ${pr.tier}\n\n**Tip:** Always test with demo accounts first when setting up prop firm rules!`,
      needsHuman: false,
    };
  }

  // Max positions
  if (q.includes('max position') || q.includes('maximum position') || q.includes('position limit')) {
    const mp = KNOWLEDGE_BASE.risk_management.daily_limits.max_positions;
    return {
      response: `**Max Positions per Symbol**\n\n${mp.description}\n\n**Example:** ${mp.example}\n\n**Location:** ${mp.location}\n\n**Use Cases:**\n• Prevent over-exposure to single symbol\n• Comply with prop firm rules\n• Manage risk during volatile markets\n\n**Note:** You can also set this per-symbol in the Symbol SL/TP settings for more granular control.`,
      needsHuman: false,
    };
  }

  // Daily loss / drawdown limits
  if (q.includes('daily loss') || q.includes('daily limit') || q.includes('loss limit')) {
    const dl = KNOWLEDGE_BASE.risk_management.daily_limits;
    return {
      response: `**Daily Loss & Drawdown Limits**\n\n**Daily Loss Limit:**\n${dl.daily_loss_limit.description}\nExample: ${dl.daily_loss_limit.example}\n\n**Max Daily Drawdown %:**\n${dl.max_daily_drawdown.description}\nExample: ${dl.max_daily_drawdown.example}\n\n**Location:** ${dl.daily_loss_limit.location}\n\n**How it works:**\n1. Set your maximum acceptable daily loss\n2. System tracks real-time P&L\n3. When limit is reached, trading automatically pauses\n4. Resets at midnight UTC\n\n**Tip:** Set limits slightly below prop firm requirements to have a safety buffer!`,
      needsHuman: false,
    };
  }

  // Partial take profit
  if (q.includes('partial') && (q.includes('tp') || q.includes('take profit') || q.includes('close'))) {
    const ptp = KNOWLEDGE_BASE.risk_management.features.partial_tp;
    return {
      response: `**Partial Take Profit**\n\n${ptp.description}\n\n**How it works:**\n• Close a portion of your position at each TP level\n• Example: Close 50% at 1:1 RR, remaining 50% at 1:2 RR\n• Locks in profits while letting winners run\n\n**Location:** ${ptp.location}\n\n**Access:** ${ptp.tier}`,
      needsHuman: false,
    };
  }

  // Symbol mapping
  if (q.includes('symbol') && (q.includes('map') || q.includes('convert') || q.includes('translate'))) {
    return {
      response: `**Symbol Mapping**\n\n${KNOWLEDGE_BASE.symbol_mapping.description}\n\n**Common mappings:**\n${Object.entries(KNOWLEDGE_BASE.symbol_mapping.examples).map(([k, v]) => `• ${k}: ${v}`).join('\n')}\n\n**Setup:** Settings > Symbol Mapping > Add new mapping\n\n**Tip:** Check your broker's symbol list to find exact names.`,
      needsHuman: false,
    };
  }

  // Symbol not found
  if (q.includes('symbol not found') || q.includes('invalid symbol')) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.symbol_not_found.solutions;
    return {
      response: `**Symbol Not Found Error**\n\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**Common fixes:**\n• XAUUSD → GOLD (some brokers)\n• BTCUSD → BTCUSDT (crypto)\n\nSet up mappings in **Settings > Symbol Mapping**`,
      needsHuman: false,
    };
  }

  // Trade not executing
  if (q.includes('trade') && (q.includes('not executing') || q.includes('not working') || q.includes('failed') || q.includes("won't"))) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.trade_not_executing.solutions;
    return {
      response: `**Trades Not Executing?**\n\nCheck these in order:\n\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**Quick diagnosis:**\n• Dashboard > Webhook Logs - See incoming signals\n• Dashboard > Rejected Signals - See what AI Guards blocked\n\nStill having issues? I can connect you with human support.`,
      needsHuman: false,
    };
  }

  // Signal routing
  if (q.includes('routing') || q.includes('route signal') || q.includes('multi account') || q.includes('multiple account')) {
    const routing = KNOWLEDGE_BASE.signal_routing;
    return {
      response: `**Signal Routing**\n\n${routing.description}\n\n**Features:**\n${routing.features.map(f => `• ${f}`).join('\n')}\n\n**Setup Steps:**\n${routing.setup_steps.join('\n')}\n\n**Examples:**\n\n**Single account:**\n\`${routing.examples.single_account.payload}\`\n\n**All accounts:**\n\`${routing.examples.multi_account.payload}\`\n\n**Tip:** Use account_id in payload to target specific accounts!`,
      needsHuman: false,
    };
  }

  // Stop loss / Take profit / Risk management
  if (q.includes('stop loss') || q.includes('take profit') || q.includes('sl') || q.includes('tp') || q.includes('trailing stop') || q.includes('risk management') || q.includes('percent') || q.includes('pips') || q.includes('points')) {
    const rm = KNOWLEDGE_BASE.risk_management;
    return {
      response: `**Risk Management**\n\n${rm.description}\n\n**Stop Loss (SL):**\n• Field: \`stop_loss\` or \`sl\`\n• Example: \`${rm.features.stop_loss.example}\`\n\n**Take Profit (TP):**\n• Field: \`take_profit\` or \`tp\`\n• Example: \`${rm.features.take_profit.example}\`\n\n**Trailing Stop:**\n• Field: \`trailing_stop\`\n• Supported: ${rm.features.trailing_stop.supported_brokers.join(', ')}\n• Example: \`${rm.features.trailing_stop.example}\`\n\n**Unit Types (Choose in Account Settings):**\n• **Pips** - ${rm.unit_types.pips}\n• **Points** - ${rm.unit_types.points}\n• **Percent** - ${rm.unit_types.percent}\n\n**Account Defaults:**\nSet default SL/TP per account in **${rm.features.account_defaults.location}**\n\nWhen you set defaults, if your webhook doesn't include SL/TP, TradeFlow automatically calculates and applies them using the current market price.\n\n**Broker Notes:**\n• ${rm.broker_specifics.futures}\n• ${rm.broker_specifics.forex}`,
      needsHuman: false,
    };
  }

  // Pending confirmation
  if (q.includes('pending') || q.includes('confirmation') || q.includes('auto confirm') || q.includes('auto-confirm') || q.includes('auto execute')) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.pending_confirmation.solutions;
    return {
      response: `**Pending Confirmation**\n\nSignals show "Pending" when auto-execute is disabled.\n\n**Solutions:**\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**To enable auto-execute:**\n1. Go to Settings > Accounts\n2. Edit the account\n3. Enable "Auto-Execute Trades"\n4. Save changes\n\nWith auto-execute enabled, signals will execute immediately.`,
      needsHuman: false,
    };
  }

  // Invalid order size / quantity
  if (q.includes('invalid order') || q.includes('order size') || q.includes('quantity') && (q.includes('error') || q.includes('invalid'))) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.invalid_order_size.solutions;
    return {
      response: `**Invalid Order Size Error**\n\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**Broker Requirements:**\n• **Futures (ProjectX, TopStep, Tradovate):** Whole contracts only (1, 2, 3...)\n• **Forex (MT5, TradeLocker):** Fractional lots allowed (0.01, 0.1, 1.0)\n\n**Fix:** Change quantity to 1 or higher for futures brokers.`,
      needsHuman: false,
    };
  }

  // Margin / not enough margin
  if (q.includes('margin') || q.includes('insufficient')) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.not_enough_margin.solutions;
    return {
      response: `**Insufficient Margin Error**\n\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**What causes this:**\n• Position size too large for account balance\n• Too many open positions\n• High leverage requirements\n\n**Solution:** Reduce quantity in your webhook payload or add funds to your broker account.`,
      needsHuman: false,
    };
  }

  // Chop mode / momentum
  if (q.includes('chop') || q.includes('choppy') || q.includes('momentum') || q.includes('opposite signal')) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.chop_mode.solutions;
    return {
      response: `**Chop Mode (Momentum Guard)**\n\nThe system detects choppy markets by tracking alternating buy/sell signals.\n\n**How it works:**\n• Counts opposite signals (buy when biased sell, etc.)\n• When threshold is exceeded, trading pauses\n• Prevents losses in ranging/choppy conditions\n\n**Solutions:**\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**Configure:** Settings > AI Guards > Momentum Guard`,
      needsHuman: false,
    };
  }

  // Signal rejected
  if (q.includes('rejected') || q.includes('blocked')) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.signal_rejected.solutions;
    return {
      response: `**Signal Rejected by AI Guards**\n\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**Common reasons:**\n${Object.entries(KNOWLEDGE_BASE.rejection_reasons).slice(0, 5).map(([reason, fix]) => `• **${reason}:** ${fix}`).join('\n')}\n\n**View details:** Settings > Webhook Logs (shows rejection reason)`,
      needsHuman: false,
    };
  }

  // Market closed
  if (q.includes('market closed') || q.includes('market hours')) {
    const solutions = KNOWLEDGE_BASE.troubleshooting.market_closed.solutions;
    return {
      response: `**Market Closed Error**\n\n${solutions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n**24/7 Markets:**\n• Crypto (BTCUSD, ETHUSD) - Trade anytime\n\n**Forex Hours:**\n• Sunday 5pm - Friday 5pm EST\n• Closed on major holidays`,
      needsHuman: false,
    };
  }

  // Trading Session / Trading Hours
  if (q.includes('trading session') || q.includes('trading hours') || q.includes('active hours') || q.includes('trade time') || q.includes('when to trade')) {
    const sessions = KNOWLEDGE_BASE.trading_sessions;
    return {
      response: `**Trading Session Control**\n\n${sessions.description}\n\n**Features:**\n${sessions.features.map(f => `• ${f}`).join('\n')}\n\n**Available Presets:**\n${sessions.presets.map(p => `• ${p}`).join('\n')}\n\n**Setup:** ${sessions.location}\n\n**Access:** ${sessions.access}`,
      needsHuman: false,
    };
  }

  // Position Management
  if (q.includes('position') || q.includes('close position') || q.includes('view position') || q.includes('open trade')) {
    const pm = KNOWLEDGE_BASE.position_management;
    return {
      response: `**Position Management**\n\n${pm.description}\n\n**Features:**\n${pm.features.map(f => `• ${f}`).join('\n')}\n\n**Location:** ${pm.location}\n\n**Access:** ${pm.access}`,
      needsHuman: false,
    };
  }

  // AI Coach
  if (q.includes('ai coach') || q.includes('trading coach') || q.includes('bias detection') || q.includes('improve') && q.includes('trading')) {
    const coach = KNOWLEDGE_BASE.ai_coach;
    return {
      response: `**AI Trading Coach**\n\n${coach.description}\n\n**Features:**\n${coach.features.map(f => `• ${f}`).join('\n')}\n\n**Location:** ${coach.location}\n\n**Access:** ${coach.access}`,
      needsHuman: false,
    };
  }

  // AI Suite
  if (q.includes('ai suite') || q.includes('strategy') || q.includes('backtest') || q.includes('pine script')) {
    return {
      response: `**AI Strategy Suite**\n\n${KNOWLEDGE_BASE.ai_suite.description}\n\n**Features:**\n${KNOWLEDGE_BASE.ai_suite.features.map(f => `• ${f}`).join('\n')}\n\n**Access:** ${KNOWLEDGE_BASE.ai_suite.access}\n\n**Location:** Dashboard > AI Suite (sidebar)`,
      needsHuman: false,
    };
  }

  // TradingView
  if (q.includes('tradingview') || q.includes('trading view')) {
    return {
      response: `**TradingView Integration**\n\n**Setting up alerts:**\n\n1. Open a chart in TradingView\n2. Click "Alert" (clock icon)\n3. Set your conditions\n4. In "Notifications":\n   • Check "Webhook URL"\n   • Paste: \`${KNOWLEDGE_BASE.webhooks.url_format}\`\n5. In "Message" put your JSON:\n   \`{"action": "buy", "symbol": "EURUSD", "quantity": 0.1}\`\n6. Click "Create"\n\n**Pro tip:** Use TradingView's {{ticker}} placeholder for dynamic symbols!`,
      needsHuman: false,
    };
  }

  // Support / Contact
  if (q.includes('support') || q.includes('contact') || q.includes('help') || q.includes('human') || q.includes('email')) {
    return {
      response: `**Contact Support**\n\nI can answer most questions, but for complex issues:\n\n📧 **Email:** ${KNOWLEDGE_BASE.platform.supportEmail}\n\n**When to contact human support:**\n• Billing or payment issues\n• Account security concerns\n• Bug reports\n• Feature requests\n• Custom integrations\n\nWould you like me to help you send a support request?`,
      needsHuman: true,
    };
  }

  // Billing issues
  if (q.includes('billing') || q.includes('payment') || q.includes('charge') || q.includes('refund') || q.includes('cancel subscription')) {
    needsHuman = true;
    return {
      response: `**Billing Support**\n\nFor billing-related questions, I recommend contacting human support:\n\n📧 **Email:** ${KNOWLEDGE_BASE.platform.supportEmail}\n\n**Self-service options:**\n• **View invoices:** Settings > Billing\n• **Update payment method:** Settings > Billing > Payment Method\n• **Change plan:** Settings > Billing > Change Plan\n• **Cancel subscription:** Settings > Billing > Cancel\n\nWould you like me to connect you with billing support?`,
      needsHuman: true,
    };
  }

  // Order types
  if (q.includes('order type') || q.includes('limit order') || q.includes('stop order') || q.includes('bracket') || q.includes('trailing stop')) {
    return {
      response: `**Supported Order Types:**\n\n• **Market** - Execute immediately at best price\n• **Limit** - Execute at specified price or better\n• **Stop** - Trigger when price reaches level\n• **Bracket** - Entry with SL and TP\n• **Trailing Stop** - Dynamic stop that follows price\n\n**Webhook examples:**\n\nBracket order:\n\`${KNOWLEDGE_BASE.webhooks.examples.bracket}\`\n\nTrailing stop:\n\`${KNOWLEDGE_BASE.webhooks.examples.trailing}\``,
      needsHuman: false,
    };
  }

  // Account / Login issues
  if (q.includes('login') || q.includes('password') || q.includes('account') && (q.includes('locked') || q.includes('access'))) {
    needsHuman = true;
    return {
      response: `**Account Access Issues**\n\n**Forgot password?**\nUse the "Forgot Password" link on the login page.\n\n**Account locked?**\nThis can happen after multiple failed attempts. Wait 15 minutes or contact support.\n\n**Email verification issues?**\nCheck spam folder or request a new verification email.\n\n**Still locked out?**\nContact support: ${KNOWLEDGE_BASE.platform.supportEmail}`,
      needsHuman: true,
    };
  }

  // Can't understand / Fallback
  if (response === '') {
    // Try to find keywords and give relevant info
    const keywords = ['webhook', 'broker', 'mt5', 'guard', 'signal', 'trade', 'symbol', 'price'];
    const foundKeyword = keywords.find(k => q.includes(k));

    if (foundKeyword) {
      return {
        response: `I found your question relates to "${foundKeyword}". Could you be more specific?\n\n**Common questions about ${foundKeyword}:**\n• How do I set up ${foundKeyword}?\n• Why is my ${foundKeyword} not working?\n• How do I configure ${foundKeyword}?\n\nOr I can connect you with human support for detailed help.`,
        needsHuman: false,
      };
    }

    needsHuman = true;
    return {
      response: `I'm not sure I understand that question. Here's what I can help with:\n\n• **Getting started** with Tradeflow\n• **Webhook** setup and configuration\n• **Broker** connections (MT4/MT5, TradeLocker, etc.)\n• **AI Guards** and risk management\n• **Troubleshooting** signal execution\n• **Pricing** and features\n\nCan you rephrase your question, or would you like to contact human support?`,
      needsHuman: true,
    };
  }

  return { response, needsHuman };
}

// ============================================================================
// SUPPORT CHAT COMPONENT
// ============================================================================

export function SupportChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `👋 Hi! I'm **TradeBot**, your Tradeflow support assistant.\n\nI can help you with:\n• Setting up webhooks and brokers\n• Understanding AI Guards\n• Troubleshooting issues\n• Explaining features\n\nHow can I help you today?`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showEscalation, setShowEscalation] = useState(false);
  const [escalationSubject, setEscalationSubject] = useState('');
  const [escalationMessage, setEscalationMessage] = useState('');
  const [sendingEscalation, setSendingEscalation] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Suggested questions
  const suggestions = [
    'How do I get started?',
    'What is Signal Intelligence?',
    'How do I set symbol-specific SL/TP?',
    'What position sizing modes are available?',
  ];

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Simulate typing delay
    await new Promise((resolve) => setTimeout(resolve, 500 + Math.random() * 1000));

    const { response, needsHuman } = generateAIResponse(userMessage.content);

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsTyping(false);

    // Show escalation option if needed
    if (needsHuman) {
      setTimeout(() => {
        setShowEscalation(true);
      }, 500);
    }
  };

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion);
    setTimeout(() => {
      handleSend();
    }, 100);
  };

  const handleEscalate = async () => {
    if (!escalationSubject.trim() || !escalationMessage.trim()) {
      toast({
        title: 'Missing information',
        description: 'Please fill in both subject and message.',
        variant: 'destructive',
      });
      return;
    }

    setSendingEscalation(true);

    try {
      const response = await fetch('/api/support/ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          subject: escalationSubject,
          message: escalationMessage,
          chat_history: messages.map(m => ({ role: m.role, content: m.content })),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        toast({
          title: 'Support ticket created',
          description: `Ticket #${data.ticket_id || 'submitted'}. We'll respond within 24 hours.`,
        });
        setShowEscalation(false);
        setEscalationSubject('');
        setEscalationMessage('');

        // Add confirmation message
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: 'assistant',
            content: `✅ I've sent your message to our support team. They'll respond to your email within 24 hours.\n\nTicket reference: #${data.ticket_id || 'submitted'}\n\nIs there anything else I can help you with?`,
            timestamp: new Date(),
          },
        ]);
      } else {
        throw new Error('Failed to create ticket');
      }
    } catch (error) {
      toast({
        title: 'Failed to send',
        description: 'Please try again or email support@mytradeflow.app directly.',
        variant: 'destructive',
      });
    } finally {
      setSendingEscalation(false);
    }
  };

  const resetChat = () => {
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: `👋 Hi! I'm **TradeBot**, your Tradeflow support assistant.\n\nI can help you with:\n• Setting up webhooks and brokers\n• Understanding AI Guards\n• Troubleshooting issues\n• Explaining features\n\nHow can I help you today?`,
        timestamp: new Date(),
      },
    ]);
    setShowEscalation(false);
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className={cn(
            'fixed bottom-20 right-4 z-40 h-12 w-12 rounded-full shadow-lg',
            'bg-gradient-to-br from-primary/20 to-primary/5 border-primary/30 hover:from-primary/30 hover:to-primary/10',
            'transition-all hover:scale-110'
          )}
        >
          <Sparkles className="h-5 w-5 text-primary" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-lg flex flex-col p-0">
        {/* Header */}
        <div className="p-4 border-b bg-gradient-to-r from-primary/10 to-transparent">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div>
                <span>TradeBot</span>
                <Badge variant="secondary" className="ml-2 text-[10px]">AI Assistant</Badge>
              </div>
            </SheetTitle>
            <SheetDescription className="text-xs">
              Your 24/7 Tradeflow support assistant
            </SheetDescription>
          </SheetHeader>
        </div>

        {/* Messages */}
        <ScrollArea ref={scrollRef} className="flex-1 p-4">
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'flex gap-2',
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                {message.role === 'assistant' && (
                  <div className="h-6 w-6 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-1">
                    <Bot className="h-3 w-3 text-primary" />
                  </div>
                )}
                <div
                  className={cn(
                    'rounded-lg px-3 py-2 max-w-[85%] text-sm',
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  )}
                >
                  <div className="whitespace-pre-wrap prose prose-sm dark:prose-invert max-w-none [&>p]:my-1 [&>ul]:my-1 [&_strong]:text-foreground">
                    {message.content.split('\n').map((line, i) => {
                      // Handle markdown-style bold
                      const parts = line.split(/\*\*(.*?)\*\*/g);
                      return (
                        <p key={i} className="my-1">
                          {parts.map((part, j) =>
                            j % 2 === 1 ? <strong key={j}>{part}</strong> : part
                          )}
                        </p>
                      );
                    })}
                  </div>
                </div>
                {message.role === 'user' && (
                  <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-1">
                    <User className="h-3 w-3" />
                  </div>
                )}
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-2 items-center">
                <div className="h-6 w-6 rounded-full bg-primary/20 flex items-center justify-center">
                  <Bot className="h-3 w-3 text-primary" />
                </div>
                <div className="bg-muted rounded-lg px-3 py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Suggestions (show only at start or after reset) */}
        {messages.length <= 2 && !isTyping && (
          <div className="px-4 pb-2">
            <p className="text-xs text-muted-foreground mb-2">Suggested questions:</p>
            <div className="flex flex-wrap gap-1">
              {suggestions.map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => handleSuggestion(suggestion)}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Escalation dialog */}
        {showEscalation && (
          <div className="px-4 py-2 border-t bg-amber-500/10">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="w-full gap-2 border-amber-500/50 text-amber-700 dark:text-amber-400">
                  <Mail className="h-4 w-4" />
                  Contact Human Support
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Contact Support Team</DialogTitle>
                  <DialogDescription>
                    Send a message to our human support team. We typically respond within 24 hours.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Input
                      placeholder="Subject (e.g., Billing question)"
                      value={escalationSubject}
                      onChange={(e) => setEscalationSubject(e.target.value)}
                    />
                  </div>
                  <div>
                    <Textarea
                      placeholder="Describe your issue in detail..."
                      value={escalationMessage}
                      onChange={(e) => setEscalationMessage(e.target.value)}
                      rows={5}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    onClick={handleEscalate}
                    disabled={sendingEscalation}
                    className="gap-2"
                  >
                    {sendingEscalation ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    Send to Support
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        )}

        {/* Input */}
        <div className="p-4 border-t">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2"
          >
            <Input
              placeholder="Type your question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isTyping}
              className="flex-1"
            />
            <Button type="submit" size="icon" disabled={!input.trim() || isTyping}>
              <Send className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={resetChat}
              title="Reset chat"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </form>
          <p className="text-[10px] text-muted-foreground mt-2 text-center">
            TradeBot may make mistakes. Verify important information.
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}
