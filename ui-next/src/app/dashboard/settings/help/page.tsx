"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  HelpCircle,
  Book,
  Zap,
  CheckCircle2,
  XCircle,
  Copy,
  ExternalLink,
  Info,
  AlertTriangle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

// Broker documentation data
const BROKER_DOCS = {
  mt5: {
    name: "MetaTrader 5 (MT5)",
    description: "Connect your MT5 account via MetaAPI Cloud for automated webhook execution",
    setup: [
      "Go to Settings > Accounts and click 'Add Account'",
      "Select 'MetaTrader 5' as the broker",
      "Enter your MT5 login number, password, and server name",
      "Click 'Test Connection' to verify credentials",
      "Save the account - it will auto-provision via MetaAPI Cloud",
    ],
    orderTypes: [
      { name: "Market Buy", supported: true, example: '{"symbol": "EURUSD", "action": "buy", "volume": 0.01}' },
      { name: "Market Sell", supported: true, example: '{"symbol": "EURUSD", "action": "sell", "volume": 0.01}' },
      { name: "Limit Buy", supported: true, example: '{"symbol": "EURUSD", "action": "limit_buy", "volume": 0.01, "price": 1.0850}' },
      { name: "Limit Sell", supported: true, example: '{"symbol": "EURUSD", "action": "limit_sell", "volume": 0.01, "price": 1.0900}' },
      { name: "Stop Buy", supported: true, example: '{"symbol": "EURUSD", "action": "stop_buy", "volume": 0.01, "price": 1.0900}' },
      { name: "Stop Sell", supported: true, example: '{"symbol": "EURUSD", "action": "stop_sell", "volume": 0.01, "price": 1.0800}' },
      { name: "Close Position", supported: true, example: '{"symbol": "EURUSD", "action": "close"}' },
      { name: "Close All", supported: true, example: '{"action": "close_all"}' },
      { name: "Modify SL/TP", supported: true, example: '{"symbol": "EURUSD", "action": "modify", "sl": 1.0800, "tp": 1.0950}' },
      { name: "Trailing Stop", supported: true, example: '{"symbol": "EURUSD", "action": "modify", "trailing_stop": 500}' },
    ],
    fields: {
      symbol: "Symbol name (e.g., EURUSD, BTCUSD, XAUUSD)",
      volume: "Lot size (0.01 = micro lot, 0.1 = mini lot, 1.0 = standard lot)",
      sl: "Stop loss price level",
      tp: "Take profit price level",
      trailing_stop: "Trailing stop distance in points (500 = 50 pips for 5-digit broker)",
      price: "Entry price for limit/stop orders",
      comment: "Order comment (max 26 characters)",
    },
    notes: [
      "MetaAPI Cloud handles the connection - no local MT5 terminal needed",
      "Trailing stops are managed server-side by MetaAPI (updates every 15 seconds)",
      "Comments are limited to 26 characters by MT5",
      "Symbol names may vary by broker (e.g., EURUSD vs EURUSD.pro)",
    ],
  },
  mt4: {
    name: "MetaTrader 4 (MT4)",
    description: "Connect your MT4 account via MetaAPI Cloud for automated webhook execution",
    setup: [
      "Go to Settings > Accounts and click 'Add Account'",
      "Select 'MetaTrader 4' as the broker",
      "Enter your MT4 login number, password, and server name",
      "Click 'Test Connection' to verify credentials",
      "Save the account - it will auto-provision via MetaAPI Cloud",
    ],
    orderTypes: [
      { name: "Market Buy", supported: true, example: '{"symbol": "EURUSD", "action": "buy", "volume": 0.01}' },
      { name: "Market Sell", supported: true, example: '{"symbol": "EURUSD", "action": "sell", "volume": 0.01}' },
      { name: "Limit Buy", supported: true, example: '{"symbol": "EURUSD", "action": "limit_buy", "volume": 0.01, "price": 1.0850}' },
      { name: "Limit Sell", supported: true, example: '{"symbol": "EURUSD", "action": "limit_sell", "volume": 0.01, "price": 1.0900}' },
      { name: "Stop Buy", supported: true, example: '{"symbol": "EURUSD", "action": "stop_buy", "volume": 0.01, "price": 1.0900}' },
      { name: "Stop Sell", supported: true, example: '{"symbol": "EURUSD", "action": "stop_sell", "volume": 0.01, "price": 1.0800}' },
      { name: "Close Position", supported: true, example: '{"symbol": "EURUSD", "action": "close"}' },
      { name: "Close All", supported: true, example: '{"action": "close_all"}' },
      { name: "Modify SL/TP", supported: true, example: '{"symbol": "EURUSD", "action": "modify", "sl": 1.0800, "tp": 1.0950}' },
      { name: "Trailing Stop", supported: true, example: '{"symbol": "EURUSD", "action": "modify", "trailing_stop": 500}' },
    ],
    fields: {
      symbol: "Symbol name (e.g., EURUSD, GBPUSD, XAUUSD)",
      volume: "Lot size (0.01 = micro lot, 0.1 = mini lot, 1.0 = standard lot)",
      sl: "Stop loss price level",
      tp: "Take profit price level",
      trailing_stop: "Trailing stop distance in points",
      price: "Entry price for limit/stop orders",
      comment: "Order comment (max 26 characters)",
    },
    notes: [
      "MetaAPI Cloud handles the connection - no local MT4 terminal needed",
      "Trailing stops are managed server-side by MetaAPI",
      "MT4 has hedging mode by default",
    ],
  },
  tradelocker: {
    name: "TradeLocker",
    description: "Connect your TradeLocker account for automated forex/CFD/crypto trading with full order support",
    setup: [
      "Go to Settings > Accounts and click 'Add Account'",
      "Select 'TradeLocker' as the broker",
      "Enter your TradeLocker email, password, and server (e.g., 'Pips')",
      "Wait for account discovery - select the trading account you want to use",
      "Click 'Test Connection' to verify everything works",
      "Save the account - credentials are encrypted and stored securely",
    ],
    orderTypes: [
      { name: "Market Buy", supported: true, example: '{"ticker": "BTCUSD", "action": "buy", "quantity": 0.01}' },
      { name: "Market Sell", supported: true, example: '{"ticker": "BTCUSD", "action": "sell", "quantity": 0.01}' },
      { name: "Buy with SL/TP", supported: true, example: '{"ticker": "XAUUSD", "action": "buy", "quantity": 0.01, "sl": 2650.00, "tp": 2700.00}' },
      { name: "Limit Buy", supported: true, example: '{"ticker": "EURUSD", "action": "limit_buy", "quantity": 0.01, "price": 1.0850}' },
      { name: "Limit Sell", supported: true, example: '{"ticker": "EURUSD", "action": "limit_sell", "quantity": 0.01, "price": 1.0900}' },
      { name: "Stop Buy", supported: true, example: '{"ticker": "EURUSD", "action": "stop_buy", "quantity": 0.01, "price": 1.0900}' },
      { name: "Stop Sell", supported: true, example: '{"ticker": "EURUSD", "action": "stop_sell", "quantity": 0.01, "price": 1.0800}' },
      { name: "Close Position", supported: true, example: '{"ticker": "BTCUSD", "action": "close"}' },
      { name: "Close All", supported: true, example: '{"action": "close_all"}' },
      { name: "Modify SL/TP", supported: true, example: '{"ticker": "XAUUSD", "action": "modify", "sl": 2640.00, "tp": 2720.00}' },
      { name: "Trailing Stop", supported: true, example: '{"ticker": "BTCUSD", "action": "modify", "trailing_stop": 50}' },
    ],
    fields: {
      ticker: "Symbol/ticker name (e.g., EURUSD, XAUUSD, BTCUSD, ETHUSD)",
      quantity: "Position size in lots (0.01 = micro lot, 0.1 = mini lot, 1.0 = standard lot)",
      sl: "Stop loss as absolute price level (e.g., 2650.00 for XAUUSD)",
      tp: "Take profit as absolute price level (e.g., 2700.00 for XAUUSD)",
      trailing_stop: "Trailing stop distance in pips (e.g., 50 = 50 pip trailing stop)",
      price: "Entry price for limit orders, or trigger price for stop orders",
      comment: "Optional order comment for tracking",
    },
    notes: [
      "TradeLocker supports crypto trading 24/7 (BTCUSD, ETHUSD) - perfect for testing on weekends",
      "Trailing stop uses 'trailingOffset' mode - price follows your position automatically",
      "Symbol names are uppercase without suffixes (EURUSD not EURUSDx)",
      "Account credentials are encrypted with AES-256 and never stored in plain text",
      "Session tokens refresh automatically - no need to re-authenticate",
      "Use the Test Webhook button in dashboard to verify your setup before going live",
    ],
  },
  projectx: {
    name: "ProjectX / TopStep",
    description: "Connect your ProjectX or TopStep futures trading account for automated futures execution",
    setup: [
      "Go to Settings > Accounts and click 'Add Account'",
      "Select 'ProjectX' as the broker",
      "Enter your TopStep username and API key (from TopStep dashboard)",
      "Wait for account discovery - select your active trading account",
      "Click 'Test Connection' to verify everything works",
      "Save the account - the system auto-resolves contract rollovers (MNQ → MNQH5)",
    ],
    orderTypes: [
      { name: "Market Buy", supported: true, example: '{"ticker": "MNQ", "action": "buy", "contracts": 1}' },
      { name: "Market Sell", supported: true, example: '{"ticker": "MNQ", "action": "sell", "contracts": 1}' },
      { name: "Buy with SL/TP", supported: true, example: '{"ticker": "MES", "action": "buy", "contracts": 2, "sl": 5950, "tp": 6050}' },
      { name: "Limit Buy", supported: true, example: '{"ticker": "MNQ", "action": "limit_buy", "contracts": 1, "price": 21450}' },
      { name: "Limit Sell", supported: true, example: '{"ticker": "MNQ", "action": "limit_sell", "contracts": 1, "price": 21550}' },
      { name: "Stop Buy", supported: true, example: '{"ticker": "MNQ", "action": "stop_buy", "contracts": 1, "price": 21600}' },
      { name: "Stop Sell", supported: true, example: '{"ticker": "MNQ", "action": "stop_sell", "contracts": 1, "price": 21400}' },
      { name: "Bracket Order", supported: true, example: '{"ticker": "MNQ", "action": "buy", "contracts": 1, "sl": 21400, "tp": 21700}' },
      { name: "Close Position", supported: true, example: '{"ticker": "MNQ", "action": "close"}' },
      { name: "Close All", supported: true, example: '{"action": "close_all"}' },
      { name: "Trailing Stop", supported: true, example: '{"ticker": "MNQ", "action": "modify", "trailing_stop": 10}' },
    ],
    fields: {
      ticker: "Futures base symbol - auto-resolves to active contract (MNQ → MNQH5, MES → MESH5)",
      contracts: "Number of contracts (whole numbers only, no decimals)",
      sl: "Stop loss as absolute price level (e.g., 21400 for MNQ)",
      tp: "Take profit as absolute price level (e.g., 21700 for MNQ)",
      trailing_stop: "Trailing stop distance in ticks (e.g., 10 = 10 ticks = 2.5 points on MNQ)",
      price: "Entry price for limit orders, trigger price for stop orders",
      comment: "Optional order comment for tracking",
    },
    notes: [
      "Automatic contract rollover - use base symbols like MNQ, MES, ES (system resolves to active contract)",
      "Contracts must be whole numbers (1, 2, 3...) - no fractional contracts",
      "Micro contracts (MNQ, MES, MYM, M2K) are great for smaller position sizing",
      "Prices are in index points (21500 for MNQ means Nasdaq at 21,500)",
      "Trailing stops are in ticks - 1 tick = 0.25 points on MNQ/MES",
      "Bracket orders (OCO) automatically place SL and TP with the entry order",
      "Market hours: CME Globex hours (Sunday 5pm - Friday 4pm CT with daily breaks)",
    ],
  },
};

// SL/TP Configuration Guide by Symbol Type
const SLTP_GUIDE = {
  overview: `Stop Loss (SL) and Take Profit (TP) values work differently depending on the symbol type and broker.
TradeFlow automatically converts your configured SL/TP values to absolute prices based on the entry price and symbol-specific tick sizes.`,

  unitTypes: [
    {
      type: "pips",
      description: "Standard forex unit (1 pip = 0.0001 for most pairs, 0.01 for JPY pairs)",
      bestFor: "Forex pairs (EURUSD, GBPUSD, USDJPY)",
      example: "SL: 50 pips = 0.0050 price distance on EURUSD",
    },
    {
      type: "points",
      description: "Smallest price increment for the symbol (tick size varies by symbol)",
      bestFor: "Futures (MNQ, MES, ES), Crypto (BTC, ETH), Indices (US30, NAS100)",
      example: "SL: 100 points on NAS100 (tick = 0.25) = 25 price distance",
    },
    {
      type: "percent",
      description: "Percentage of entry price",
      bestFor: "Any symbol, especially when position sizing by risk",
      example: "SL: 1% on entry at 100.00 = SL at 99.00",
    },
    {
      type: "price",
      description: "Absolute price level (no conversion)",
      bestFor: "When you know exact price levels from chart analysis",
      example: "SL: 21450.00 = exact stop price",
    },
  ],

  symbolTypes: [
    {
      category: "Forex Pairs",
      symbols: ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"],
      tickSize: "0.00001 (5-digit) or 0.0001 (4-digit)",
      recommendedUnit: "pips",
      notes: "1 pip = 10 points on 5-digit brokers. JPY pairs use 0.01 as 1 pip.",
      examples: [
        { setting: "SL: 30 pips", result: "Entry 1.0850 → SL at 1.0820 (buy) or 1.0880 (sell)" },
        { setting: "TP: 60 pips", result: "Entry 1.0850 → TP at 1.0910 (buy) or 1.0790 (sell)" },
      ],
    },
    {
      category: "JPY Forex Pairs",
      symbols: ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY"],
      tickSize: "0.001 (3-digit) or 0.01 (2-digit)",
      recommendedUnit: "pips",
      notes: "1 pip = 0.01 for JPY pairs. Different from other forex pairs!",
      examples: [
        { setting: "SL: 50 pips", result: "Entry 155.50 → SL at 155.00 (buy) or 156.00 (sell)" },
        { setting: "TP: 100 pips", result: "Entry 155.50 → TP at 156.50 (buy) or 154.50 (sell)" },
      ],
    },
    {
      category: "Crypto",
      symbols: ["BTCUSD", "ETHUSD", "BTCUSDT", "ETHUSDT"],
      tickSize: "1.0 (BTC), 0.1 (ETH)",
      recommendedUnit: "points or percent",
      notes: "Crypto has large price values - use points for fixed distance or percent for proportional stops.",
      examples: [
        { setting: "SL: 500 points (BTC)", result: "Entry 95000 → SL at 94500 (buy) or 95500 (sell)" },
        { setting: "SL: 1% (BTC)", result: "Entry 95000 → SL at 94050 (buy) or 95950 (sell)" },
      ],
    },
    {
      category: "Micro Futures (MNQ, MES, MYM, M2K)",
      symbols: ["MNQ", "MES", "MYM", "M2K"],
      tickSize: "0.25 (MNQ/MES), 1.0 (MYM/M2K)",
      recommendedUnit: "points",
      notes: "1 tick = 0.25 points on MNQ/MES. SL/TP should be in points, not ticks. TopStep/ProjectX bracket orders use absolute prices.",
      examples: [
        { setting: "SL: 50 points (MNQ)", result: "Entry 21500 → SL at 21450 (buy) or 21550 (sell)" },
        { setting: "TP: 100 points (MES)", result: "Entry 6000 → TP at 6100 (buy) or 5900 (sell)" },
      ],
    },
    {
      category: "Standard Futures (ES, NQ, YM, RTY)",
      symbols: ["ES", "NQ", "YM", "RTY"],
      tickSize: "0.25 (ES/NQ), 1.0 (YM/RTY)",
      recommendedUnit: "points",
      notes: "Same tick sizes as micro contracts. Larger contract values.",
      examples: [
        { setting: "SL: 20 points (ES)", result: "Entry 6000 → SL at 5980 (buy) or 6020 (sell)" },
        { setting: "TP: 50 points (NQ)", result: "Entry 21500 → TP at 21550 (buy) or 21450 (sell)" },
      ],
    },
    {
      category: "Index CFDs",
      symbols: ["US30", "NAS100", "SPX500", "US500"],
      tickSize: "1.0 (US30), 0.25 (NAS100), 0.1 (SPX500)",
      recommendedUnit: "points",
      notes: "CFD indices have different tick sizes than futures. Check your broker's specifications.",
      examples: [
        { setting: "SL: 100 points (US30)", result: "Entry 44000 → SL at 43900 (buy) or 44100 (sell)" },
        { setting: "SL: 50 points (NAS100)", result: "Entry 21500 → SL at 21450 (buy) or 21550 (sell)" },
      ],
    },
    {
      category: "Metals",
      symbols: ["XAUUSD", "XAGUSD", "GC", "MGC"],
      tickSize: "0.01 (XAUUSD), 0.001 (XAGUSD), 0.1 (GC/MGC)",
      recommendedUnit: "points or price",
      notes: "Gold (XAUUSD) uses 0.01 tick. Futures gold (GC/MGC) uses 0.1 tick.",
      examples: [
        { setting: "SL: 500 points (XAUUSD)", result: "Entry 2650.00 → SL at 2645.00 (buy) or 2655.00 (sell)" },
        { setting: "TP: 1000 points (XAUUSD)", result: "Entry 2650.00 → TP at 2660.00 (buy) or 2640.00 (sell)" },
      ],
    },
    {
      category: "Energy",
      symbols: ["CL", "MCL", "NG", "USOIL", "UKOIL"],
      tickSize: "0.01 (CL/MCL/OILS), 0.001 (NG)",
      recommendedUnit: "points or price",
      notes: "Crude oil uses 0.01 tick. Natural gas uses 0.001 tick.",
      examples: [
        { setting: "SL: 50 points (CL)", result: "Entry 75.00 → SL at 74.50 (buy) or 75.50 (sell)" },
        { setting: "TP: 100 points (CL)", result: "Entry 75.00 → TP at 76.00 (buy) or 74.00 (sell)" },
      ],
    },
  ],

  brokerSpecific: [
    {
      broker: "MT5 / MT4 (MetaAPI)",
      slTpBehavior: "SL/TP sent as absolute prices. TradeFlow converts your settings to prices.",
      trailingStop: "Trailing stop in points (500 = 50 pips on 5-digit broker)",
      tips: [
        "Use 'pips' for forex, 'points' for indices/commodities",
        "Trailing stops update every 15 seconds via MetaAPI",
        "Symbol names vary by broker (check exact format)",
      ],
    },
    {
      broker: "TradeLocker",
      slTpBehavior: "SL/TP sent as absolute prices. Supports bracket orders natively.",
      trailingStop: "Uses 'trailingOffset' mode - automatic price following",
      tips: [
        "Use 'pips' for forex, 'points' for crypto/indices",
        "Crypto available 24/7 - great for testing",
        "Symbol names are uppercase without suffixes",
      ],
    },
    {
      broker: "ProjectX / TopStep",
      slTpBehavior: "Bracket orders (OCO) - SL and TP placed simultaneously with entry as stop-limit orders.",
      trailingStop: "Trailing stop in ticks (not points). 1 tick = 0.25 points on MNQ/MES.",
      tips: [
        "Always use 'points' unit type for consistent behavior",
        "Bracket orders may fail if price moves during execution - this is normal",
        "Contracts must be whole numbers (1, 2, 3...)",
        "System auto-resolves contract rollovers (MNQ → MNQH5)",
        "If bracket fails, position opens without SL/TP - monitor manually",
      ],
    },
  ],
};

// Platform Features Documentation
const PLATFORM_FEATURES = {
  tradingAnalytics: {
    title: "Trading Analytics Dashboard",
    description: "Comprehensive performance tracking and analysis tools",
    features: [
      {
        name: "Performance Metrics",
        description: "Track all key trading metrics in real-time",
        settings: [
          { name: "Win Rate", description: "Percentage of winning trades" },
          { name: "Profit Factor", description: "Gross profit divided by gross loss" },
          { name: "Expectancy", description: "Average expected profit per trade" },
          { name: "Sharpe Ratio", description: "Risk-adjusted return metric" },
          { name: "Max Drawdown", description: "Largest peak-to-trough decline" },
        ],
        example: "Track a 65% win rate with 1.8 profit factor to understand your edge.",
        location: "Dashboard > Analytics > Performance",
      },
      {
        name: "Circuit Breakers",
        description: "Auto-pause trading when risk limits are hit",
        settings: [
          { name: "Daily Loss Limit", description: "Pause when daily loss exceeds $ or % threshold" },
          { name: "Consecutive Losses", description: "Pause after X consecutive losing trades" },
          { name: "Auto Resume", description: "Automatically resume after cooling period" },
        ],
        example: "Set $500 daily loss limit - trading pauses automatically when hit, protecting your account.",
        location: "Dashboard > Analytics > Circuit Breakers",
      },
      {
        name: "News Event Filter",
        description: "Pause trading around high-impact economic events",
        settings: [
          { name: "Filter High Impact", description: "Pause for FOMC, NFP, CPI, etc." },
          { name: "Minutes Before", description: "Pause X minutes before event" },
          { name: "Minutes After", description: "Resume X minutes after event" },
        ],
        example: "Auto-pause 15 min before and after NFP to avoid volatility spikes.",
        location: "Dashboard > Analytics > Filters",
      },
      {
        name: "Correlation Filter",
        description: "Prevent taking correlated positions simultaneously",
        settings: [
          { name: "Max Correlation", description: "Block trades above correlation threshold (0.7 = 70%)" },
          { name: "Action on Correlation", description: "Block or warn when correlated trade detected" },
        ],
        example: "If you're long ES, the system blocks a long NQ signal (92% correlated) to reduce risk concentration.",
        location: "Dashboard > Analytics > Filters",
      },
      {
        name: "Time-Based Analysis",
        description: "Discover your best trading hours and days",
        settings: [
          { name: "Hourly Heatmap", description: "Performance breakdown by hour of day" },
          { name: "Daily Stats", description: "Performance by day of week" },
          { name: "Session Analysis", description: "Asian, London, NY session performance" },
        ],
        example: "Discover you win 75% of trades during London session but only 45% during Asian - adjust your schedule.",
        location: "Dashboard > Analytics > Time Analysis",
      },
      {
        name: "Dynamic Position Sizing",
        description: "Auto-adjust position size based on performance",
        settings: [
          { name: "Enable Dynamic Sizing", description: "Scale positions based on recent results" },
          { name: "Equity Curve Trading", description: "Reduce size when below moving average" },
        ],
        example: "After 3 consecutive wins, increase size by 25%. After 2 losses, reduce by 50%.",
        location: "Dashboard > Analytics > Position Sizing",
      },
    ],
  },
  signalIntelligence: {
    title: "Signal Intelligence Guard",
    description: "Self-protecting execution layer with advanced signal filtering",
    features: [
      {
        name: "Position P&L Protection",
        description: "Warns or blocks signals that trade against your profitable positions",
        settings: [
          { name: "Enable Position P&L Check", description: "Turn on/off the P&L check" },
          { name: "Profit Threshold", description: "Minimum profit ($) before warnings trigger" },
          { name: "Block Mode", description: "Auto-reject signals instead of just warning" },
        ],
        example: "If you have a BUY position in XAUUSD that's +$500 profit, and a SELL signal comes in, the system will warn or block it.",
        location: "Settings > Risk Intelligence",
      },
      {
        name: "Profit Lock (Smart Exit)",
        description: "Tracks peak profit and only allows position flips when profit drops significantly - protecting your winners during brief pullbacks",
        settings: [
          { name: "Enable Profit Lock", description: "Turn on peak profit tracking" },
          { name: "Min Profit to Track ($)", description: "Only track positions with $X+ profit" },
          { name: "Allow Flip Drop (%)", description: "Allow flip after profit drops X% from peak" },
        ],
        example: "Position peaks at $800 profit. If a flip signal comes while at $750 (6% drop), it's BLOCKED. If profit drops to $400 (50% drop), flip is ALLOWED - trend likely changed.",
        location: "Settings > Risk Intelligence > Profit Lock",
      },
      {
        name: "Chop Detection",
        description: "Detects sideways/choppy markets and pauses new entries to prevent whipsaw losses",
        settings: [
          { name: "Enable Chop Detection", description: "Turn on chop pattern recognition" },
          { name: "Pause on Chop", description: "Auto-pause new entries when chop detected" },
        ],
        example: "If signals alternate BUY-SELL-BUY-SELL rapidly, system detects chop mode and pauses entries.",
        location: "Settings > Risk Intelligence",
      },
      {
        name: "Auto-Breakeven",
        description: "Automatically moves stop loss to entry when momentum warning triggers",
        settings: [
          { name: "Enable Auto-Breakeven", description: "Auto-move SL to entry on momentum shift" },
        ],
        example: "When a flip signal is detected but blocked, the system can auto-move your stop to breakeven to protect profits.",
        location: "Settings > Risk Intelligence",
      },
      {
        name: "Daily Trade Limits",
        description: "Prevent overtrading by limiting signals per day",
        settings: [
          { name: "Max Daily Trades", description: "Maximum trades allowed per day per account" },
          { name: "Trade Cooldown", description: "Minimum seconds between trades" },
        ],
        example: "Set to 10 trades/day to prevent excessive trading during volatile markets.",
        location: "Account Settings > Risk Limits",
      },
    ],
  },
  symbolSettings: {
    title: "Symbol-Specific SL/TP",
    description: "Configure custom stop loss and take profit for individual symbols",
    features: [
      {
        name: "Per-Symbol SL/TP Override",
        description: "Set different SL/TP values for specific symbols instead of using account defaults",
        settings: [
          { name: "Symbol", description: "The trading symbol (e.g., XAUUSD, NAS100)" },
          { name: "Stop Loss", description: "Default SL for this symbol" },
          { name: "Take Profit", description: "Default TP for this symbol" },
          { name: "SL/TP Type", description: "Unit type: pips, points, percent, or price" },
        ],
        example: "Set XAUUSD to use 500 points SL while keeping EURUSD at 30 pips SL.",
        location: "Account Settings > Symbol SL/TP tab",
      },
      {
        name: "Position Size Override",
        description: "Set a fixed lot size for specific symbols",
        settings: [
          { name: "Position Size Override", description: "Fixed lot size for this symbol (optional)" },
          { name: "Max Positions", description: "Maximum positions allowed for this symbol" },
        ],
        example: "Trade BTCUSD with 0.01 lots always, regardless of account position sizing mode.",
        location: "Account Settings > Symbol SL/TP tab",
      },
    ],
  },
  riskManagement: {
    title: "Risk Management",
    description: "Comprehensive risk controls for each account",
    features: [
      {
        name: "Position Sizing Modes",
        description: "Control how position sizes are calculated",
        settings: [
          { name: "Fixed Lot", description: "Use the same lot size for every trade" },
          { name: "Percent of Balance", description: "Size based on account balance percentage" },
          { name: "Percent of Equity", description: "Size based on account equity percentage" },
          { name: "Risk Percent", description: "Calculate size based on risk per trade" },
        ],
        example: "Use 1% risk per trade to automatically size positions based on your SL distance.",
        location: "Account Settings > Position Sizing tab",
      },
      {
        name: "Daily Loss Limits",
        description: "Stop trading when daily loss threshold is reached",
        settings: [
          { name: "Max Daily Loss ($)", description: "Absolute dollar amount" },
          { name: "Max Daily Loss (%)", description: "Percentage of starting balance" },
        ],
        example: "Set $500 max daily loss to automatically pause trading when hit.",
        location: "Account Settings > Risk Limits tab",
      },
      {
        name: "Drawdown Protection",
        description: "Stop trading when account drawdown exceeds threshold",
        settings: [
          { name: "Max Drawdown (%)", description: "Maximum allowed drawdown from peak equity" },
        ],
        example: "Set 5% max drawdown for prop firm compliance.",
        location: "Account Settings > Risk Limits tab",
      },
      {
        name: "Position Limits",
        description: "Control maximum exposure",
        settings: [
          { name: "Max Open Positions", description: "Total positions allowed across all symbols" },
          { name: "Max Positions Per Symbol", description: "Positions allowed per individual symbol" },
          { name: "Max Position Size", description: "Maximum lot size per trade" },
        ],
        example: "Allow max 5 total positions, but only 2 per symbol.",
        location: "Account Settings > Risk Limits tab",
      },
    ],
  },
  propRules: {
    title: "Prop Firm Rules",
    description: "Pre-configured rules for prop trading challenges",
    features: [
      {
        name: "Challenge Tracking",
        description: "Track your prop firm challenge progress",
        settings: [
          { name: "Provider", description: "Prop firm name (FTMO, TopStep, etc.)" },
          { name: "Phase", description: "Current phase (Evaluation, Verification, Funded)" },
          { name: "Profit Target", description: "Required profit to pass" },
          { name: "Max Daily Loss", description: "Daily loss limit for the challenge" },
          { name: "Max Drawdown", description: "Total drawdown limit" },
          { name: "Trailing Drawdown", description: "Whether drawdown trails your equity high" },
        ],
        example: "Configure FTMO rules: 10% profit target, 5% daily loss, 10% max drawdown.",
        location: "Account Settings > Prop Rules tab",
      },
    ],
  },
  signalRouting: {
    title: "Signal Routing",
    description: "Control which signals reach which accounts",
    features: [
      {
        name: "Enable/Disable Signals",
        description: "Turn signal reception on/off per account",
        settings: [
          { name: "Enable Signals", description: "Whether this account receives webhook signals" },
          { name: "Auto-Confirm", description: "Auto-execute signals without manual confirmation" },
        ],
        example: "Disable signals on demo account while keeping live account active.",
        location: "Account Settings > Signal Routing tab",
      },
      {
        name: "Symbol Blocking",
        description: "Block specific symbols from being traded",
        settings: [
          { name: "Blocked Symbols", description: "Comma-separated list of symbols to block" },
        ],
        example: "Block XAUUSD,BTCUSD to prevent trading volatile instruments on this account.",
        location: "Account Settings > Signal Routing tab",
      },
      {
        name: "Account Groups",
        description: "Organize accounts into groups for easier management",
        settings: [
          { name: "Group Name", description: "Name for the account group" },
          { name: "Color", description: "Visual identifier for the group" },
        ],
        example: "Create 'Live Accounts' and 'Demo Accounts' groups.",
        location: "Settings > Account Groups",
      },
    ],
  },
};

// Common webhook examples
const COMMON_EXAMPLES = [
  {
    title: "Basic Buy Signal",
    description: "Simple market buy order",
    json: {
      symbol: "EURUSD",
      action: "buy",
      volume: 0.01,
    },
  },
  {
    title: "Buy with Risk Management",
    description: "Market buy with stop loss and take profit",
    json: {
      symbol: "EURUSD",
      action: "buy",
      volume: 0.01,
      sl: 1.0800,
      tp: 1.0950,
    },
  },
  {
    title: "TradingView Alert Format",
    description: "With timestamp for staleness protection",
    json: {
      symbol: "{{ticker}}",
      action: "buy",
      volume: 0.01,
      timestamp: "{{timenow}}",
    },
  },
  {
    title: "Close All Positions",
    description: "Emergency close all open positions",
    json: {
      action: "close_all",
    },
  },
  {
    title: "Trailing Stop",
    description: "Add trailing stop to existing position",
    json: {
      symbol: "EURUSD",
      action: "modify",
      trailing_stop: 500,
    },
  },
];

export default function HelpPage() {
  const [selectedBroker, setSelectedBroker] = useState<keyof typeof BROKER_DOCS>("mt5");
  const { toast } = useToast();

  const broker = BROKER_DOCS[selectedBroker];

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied!", description: "JSON copied to clipboard" });
  }

  return (
    <div className="space-y-4 sm:space-y-6 px-2 sm:px-0">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
          <HelpCircle className="h-5 w-5 sm:h-6 sm:w-6" />
          Help & Support
        </h1>
        <p className="text-sm sm:text-base text-muted-foreground">
          Complete documentation for webhook signals and broker integrations
        </p>
      </div>

      <Tabs defaultValue="brokers" className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1 p-1 md:grid md:w-full md:grid-cols-5">
          <TabsTrigger value="brokers" className="flex-1 min-w-[70px] text-xs sm:text-sm">
            <Book className="w-4 h-4 md:mr-1" />
            <span className="hidden sm:inline">Broker Guides</span>
            <span className="sm:hidden">Brokers</span>
          </TabsTrigger>
          <TabsTrigger value="features" className="flex-1 min-w-[70px] text-xs sm:text-sm">
            <Zap className="w-4 h-4 md:mr-1" />
            <span className="hidden sm:inline">Platform Features</span>
            <span className="sm:hidden">Features</span>
          </TabsTrigger>
          <TabsTrigger value="sltp" className="flex-1 min-w-[70px] text-xs sm:text-sm">
            <span className="hidden sm:inline">SL/TP Guide</span>
            <span className="sm:hidden">SL/TP</span>
          </TabsTrigger>
          <TabsTrigger value="webhooks" className="flex-1 min-w-[70px] text-xs sm:text-sm">
            <span className="hidden sm:inline">Webhooks</span>
            <span className="sm:hidden">Hooks</span>
          </TabsTrigger>
          <TabsTrigger value="tradingview" className="flex-1 min-w-[70px] text-xs sm:text-sm">
            <span className="hidden sm:inline">TradingView</span>
            <span className="sm:hidden">TV</span>
          </TabsTrigger>
        </TabsList>

        {/* Broker Documentation Tab */}
        <TabsContent value="brokers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Book className="h-5 w-5" />
                Select Your Broker
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
              <div className="flex flex-wrap gap-2">
                {Object.entries(BROKER_DOCS).map(([key, doc]) => (
                  <Button
                    key={key}
                    variant={selectedBroker === key ? "default" : "outline"}
                    onClick={() => setSelectedBroker(key as keyof typeof BROKER_DOCS)}
                    size="sm"
                    className="text-xs sm:text-sm"
                  >
                    {doc.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Selected Broker Documentation */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">{broker.name}</CardTitle>
              <CardDescription className="text-xs sm:text-sm">{broker.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 px-3 sm:px-6">
              {/* Setup Steps */}
              <div>
                <h3 className="font-semibold mb-3">Setup Steps</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm">
                  {broker.setup.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>

              {/* Supported Order Types */}
              <div>
                <h3 className="font-semibold mb-3 text-sm sm:text-base">Supported Order Types</h3>
                <div className="grid gap-2 sm:gap-3">
                  {broker.orderTypes.map((order, i) => (
                    <div key={i} className="border rounded-lg p-2 sm:p-3">
                      <div className="flex items-center justify-between mb-2 gap-2">
                        <div className="flex items-center gap-1 sm:gap-2 min-w-0">
                          {order.supported ? (
                            <CheckCircle2 className="h-3 w-3 sm:h-4 sm:w-4 text-green-500 flex-shrink-0" />
                          ) : (
                            <XCircle className="h-3 w-3 sm:h-4 sm:w-4 text-red-500 flex-shrink-0" />
                          )}
                          <span className="font-medium text-xs sm:text-sm truncate">{order.name}</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(order.example)}
                          className="flex-shrink-0 h-7 w-7 p-0"
                        >
                          <Copy className="h-3 w-3 sm:h-4 sm:w-4" />
                        </Button>
                      </div>
                      <pre className="text-[10px] sm:text-xs bg-muted p-1.5 sm:p-2 rounded overflow-x-auto">
                        {order.example}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>

              {/* Field Descriptions */}
              <div>
                <h3 className="font-semibold mb-3 text-sm sm:text-base">Field Reference</h3>
                <div className="space-y-2">
                  {Object.entries(broker.fields).map(([field, desc]) => (
                    <div key={field} className="flex flex-col sm:flex-row gap-1 sm:gap-2 text-xs sm:text-sm">
                      <code className="bg-muted px-2 py-0.5 rounded font-mono text-[10px] sm:text-xs w-fit">
                        {field}
                      </code>
                      <span className="text-muted-foreground">{desc}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Notes */}
              <Alert>
                <Info className="h-4 w-4" />
                <AlertTitle>Important Notes</AlertTitle>
                <AlertDescription>
                  <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                    {broker.notes.map((note, i) => (
                      <li key={i}>{note}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Platform Features Tab */}
        <TabsContent value="features" className="space-y-4">
          {Object.values(PLATFORM_FEATURES).map((section) => (
            <Card key={section.title}>
              <CardHeader className="px-3 sm:px-6">
                <CardTitle className="text-base sm:text-lg">{section.title}</CardTitle>
                <CardDescription className="text-xs sm:text-sm">{section.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 sm:space-y-6 px-3 sm:px-6">
                {section.features.map((feature) => (
                  <div key={feature.name} className="border rounded-lg p-3 sm:p-4">
                    <h4 className="font-semibold mb-2 text-sm sm:text-base">{feature.name}</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground mb-3">{feature.description}</p>

                    {/* Settings */}
                    <div className="mb-3">
                      <p className="text-xs sm:text-sm font-medium mb-2">Settings:</p>
                      <div className="space-y-1">
                        {feature.settings.map((setting) => (
                          <div key={setting.name} className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-2 text-xs sm:text-sm">
                            <code className="bg-muted px-2 py-0.5 rounded text-[10px] sm:text-xs w-fit">
                              {setting.name}
                            </code>
                            <span className="text-muted-foreground">{setting.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Example */}
                    <div className="bg-muted/50 p-2 sm:p-3 rounded-lg">
                      <p className="text-xs sm:text-sm">
                        <strong>Example:</strong> {feature.example}
                      </p>
                    </div>

                    {/* Location */}
                    <p className="text-[10px] sm:text-xs text-muted-foreground mt-2">
                      <strong>Location:</strong> {feature.location}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* SL/TP Configuration Guide Tab */}
        <TabsContent value="sltp" className="space-y-4">
          {/* Overview */}
          <Alert className="text-xs sm:text-sm">
            <Info className="h-4 w-4" />
            <AlertTitle className="text-sm sm:text-base">How SL/TP Works in TradeFlow</AlertTitle>
            <AlertDescription className="mt-2">
              {SLTP_GUIDE.overview}
            </AlertDescription>
          </Alert>

          {/* Unit Types */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="text-base sm:text-lg">SL/TP Unit Types</CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                Choose the right unit type for your trading style and symbol type
              </CardDescription>
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
              <div className="grid gap-3 sm:gap-4 md:grid-cols-2">
                {SLTP_GUIDE.unitTypes.map((unit) => (
                  <div key={unit.type} className="border rounded-lg p-3 sm:p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="secondary" className="font-mono text-xs">{unit.type}</Badge>
                    </div>
                    <p className="text-xs sm:text-sm text-muted-foreground mb-2">{unit.description}</p>
                    <p className="text-xs sm:text-sm"><strong>Best for:</strong> {unit.bestFor}</p>
                    <code className="block mt-2 text-[10px] sm:text-xs bg-muted p-1.5 sm:p-2 rounded overflow-x-auto">{unit.example}</code>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Symbol-Specific Settings */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="text-base sm:text-lg">Symbol-Specific Settings</CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                Tick sizes and recommended SL/TP settings for each symbol type
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 sm:space-y-6 px-3 sm:px-6">
              {SLTP_GUIDE.symbolTypes.map((symbolType) => (
                <div key={symbolType.category} className="border rounded-lg p-3 sm:p-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                    <h4 className="font-semibold text-sm sm:text-base">{symbolType.category}</h4>
                    <Badge className="w-fit text-xs">{symbolType.recommendedUnit}</Badge>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {symbolType.symbols.map((sym) => (
                      <code key={sym} className="bg-muted px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs">{sym}</code>
                    ))}
                  </div>
                  <div className="text-xs sm:text-sm space-y-2">
                    <p><strong>Tick Size:</strong> {symbolType.tickSize}</p>
                    <p className="text-muted-foreground">{symbolType.notes}</p>
                  </div>
                  <div className="mt-3 space-y-2">
                    <p className="text-xs sm:text-sm font-medium">Examples:</p>
                    {symbolType.examples.map((ex, i) => (
                      <div key={i} className="bg-muted/50 p-1.5 sm:p-2 rounded text-xs sm:text-sm">
                        <span className="font-mono text-[10px] sm:text-xs block sm:inline">{ex.setting}</span>
                        <span className="mx-1 sm:mx-2 hidden sm:inline">→</span>
                        <span className="text-muted-foreground block sm:inline mt-1 sm:mt-0">{ex.result}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Broker-Specific Behavior */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="text-base sm:text-lg">Broker-Specific Behavior</CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                How each broker handles SL/TP and trailing stops
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 sm:space-y-4 px-3 sm:px-6">
              {SLTP_GUIDE.brokerSpecific.map((brokerInfo) => (
                <div key={brokerInfo.broker} className="border rounded-lg p-3 sm:p-4">
                  <h4 className="font-semibold mb-2 text-sm sm:text-base">{brokerInfo.broker}</h4>
                  <div className="space-y-2 text-xs sm:text-sm">
                    <p><strong>SL/TP Behavior:</strong> {brokerInfo.slTpBehavior}</p>
                    <p><strong>Trailing Stop:</strong> {brokerInfo.trailingStop}</p>
                  </div>
                  <div className="mt-3">
                    <p className="text-xs sm:text-sm font-medium mb-2">Tips:</p>
                    <ul className="list-disc list-inside space-y-1 text-xs sm:text-sm text-muted-foreground">
                      {brokerInfo.tips.map((tip, i) => (
                        <li key={i}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Common Issues */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
                Common SL/TP Issues
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
              <div className="space-y-3 sm:space-y-4">
                <div className="border-l-4 border-yellow-500 pl-3 sm:pl-4">
                  <h5 className="font-medium text-sm sm:text-base">SL/TP too close to entry</h5>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    Many brokers have minimum distance requirements. If your SL/TP is rejected,
                    try increasing the distance. Typical minimums: 5-10 pips for forex, 5-20 points for indices.
                  </p>
                </div>
                <div className="border-l-4 border-yellow-500 pl-3 sm:pl-4">
                  <h5 className="font-medium text-sm sm:text-base">Bracket order fill failures (ProjectX/TopStep)</h5>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    Bracket orders can fail if price moves during execution. The main position may fill
                    but SL/TP orders may be rejected. This is normal market behavior - monitor positions
                    and add SL/TP manually if needed.
                  </p>
                </div>
                <div className="border-l-4 border-yellow-500 pl-3 sm:pl-4">
                  <h5 className="font-medium text-sm sm:text-base">Wrong unit type selected</h5>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    If your SL/TP values seem way off, check your unit type setting. Using &quot;pips&quot; for
                    futures or &quot;points&quot; for forex without understanding the conversion can result in
                    stops that are too tight or too wide.
                  </p>
                </div>
                <div className="border-l-4 border-yellow-500 pl-3 sm:pl-4">
                  <h5 className="font-medium text-sm sm:text-base">JPY pairs have different pip values</h5>
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    USDJPY, EURJPY, etc. use 0.01 as 1 pip (not 0.0001). If your stops are 100x too
                    tight or wide on JPY pairs, this is likely the cause.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Webhook Examples Tab */}
        <TabsContent value="webhooks" className="space-y-4">
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                <Zap className="h-4 w-4 sm:h-5 sm:w-5" />
                Common Webhook Examples
              </CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                Copy and paste these examples into your TradingView alerts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 sm:space-y-4 px-3 sm:px-6">
              {COMMON_EXAMPLES.map((example, i) => (
                <div key={i} className="border rounded-lg p-3 sm:p-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div>
                      <h4 className="font-medium text-sm sm:text-base">{example.title}</h4>
                      <p className="text-xs sm:text-sm text-muted-foreground">{example.description}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(JSON.stringify(example.json, null, 2))}
                      className="w-fit text-xs"
                    >
                      <Copy className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                      Copy
                    </Button>
                  </div>
                  <pre className="text-[10px] sm:text-sm bg-slate-900 text-green-400 p-2 sm:p-3 rounded overflow-x-auto">
                    {JSON.stringify(example.json, null, 2)}
                  </pre>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* PineScript Format Support */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
                PineScript Format Support
              </CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                TradeFlow automatically translates PineScript strategy formats
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 px-3 sm:px-6">
              <Alert className="text-xs sm:text-sm">
                <Info className="h-4 w-4" />
                <AlertDescription>
                  If your TradingView strategy uses PineScript format (data=&quot;long&quot;/&quot;short&quot;),
                  TradeFlow automatically converts it to the standard format.
                </AlertDescription>
              </Alert>

              <div className="space-y-3">
                <h4 className="font-medium text-sm sm:text-base">Automatic Translations:</h4>
                <div className="grid gap-2">
                  {[
                    { from: 'data: "long"', to: 'action: "buy"', note: "Entry long position" },
                    { from: 'data: "short"', to: 'action: "sell"', note: "Entry short position" },
                    { from: 'action: "partial_close"', to: 'action: "close"', note: "Close partial position" },
                    { from: 'action: "tp1", "tp2", "tp3"', to: 'action: "close"', note: "Take profit levels" },
                    { from: 'action: "sl"', to: 'action: "close"', note: "Stop loss hit" },
                    { from: 'action: "exit"', to: 'action: "close"', note: "Exit signal" },
                  ].map((item) => (
                    <div key={item.from} className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 bg-muted/50 p-2 rounded text-xs sm:text-sm">
                      <code className="bg-red-500/10 px-1.5 sm:px-2 py-0.5 rounded text-red-600 dark:text-red-400 text-[10px] sm:text-xs w-fit">{item.from}</code>
                      <span className="hidden sm:inline">→</span>
                      <code className="bg-green-500/10 px-1.5 sm:px-2 py-0.5 rounded text-green-600 dark:text-green-400 text-[10px] sm:text-xs w-fit">{item.to}</code>
                      <span className="text-muted-foreground text-[10px] sm:text-xs sm:ml-auto">{item.note}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border rounded-lg p-3 sm:p-4">
                <h4 className="font-medium mb-2 text-sm sm:text-base">PineScript Example (auto-converted)</h4>
                <pre className="text-[10px] sm:text-sm bg-slate-900 text-green-400 p-2 sm:p-3 rounded overflow-x-auto">
{`{
  "symbol": "{{ticker}}",
  "data": "long",
  "volume": 0.01
}
// Automatically becomes: action="buy"`}
                </pre>
              </div>
            </CardContent>
          </Card>

          {/* Action Reference */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="text-base sm:text-lg">Action Reference</CardTitle>
              <CardDescription className="text-xs sm:text-sm">All supported action values</CardDescription>
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                {[
                  { action: "buy", desc: "Market buy order" },
                  { action: "sell", desc: "Market sell order" },
                  { action: "limit_buy", desc: "Limit buy order" },
                  { action: "limit_sell", desc: "Limit sell order" },
                  { action: "stop_buy", desc: "Stop buy order" },
                  { action: "stop_sell", desc: "Stop sell order" },
                  { action: "close", desc: "Close position by symbol" },
                  { action: "close_all", desc: "Close all positions" },
                  { action: "modify", desc: "Modify SL/TP/trailing" },
                ].map((item) => (
                  <div key={item.action} className="border rounded p-2 sm:p-3">
                    <code className="text-xs sm:text-sm font-mono bg-primary/10 px-1 sm:px-1.5 py-0.5 rounded">
                      {item.action}
                    </code>
                    <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">{item.desc}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TradingView Setup Tab */}
        <TabsContent value="tradingview" className="space-y-4">
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="text-base sm:text-lg">TradingView Webhook Setup</CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                Step-by-step guide to connect TradingView alerts to Tradeflow
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 sm:space-y-6 px-3 sm:px-6">
              <div className="space-y-4">
                <div className="flex gap-3 sm:gap-4">
                  <div className="flex-shrink-0 w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs sm:text-base">
                    1
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-medium text-sm sm:text-base">Get Your Webhook URL</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Find your webhook key in the dashboard Quick Actions section or Settings &gt; Webhooks.
                      Your webhook URL format is:
                    </p>
                    <code className="block mt-2 p-1.5 sm:p-2 bg-muted rounded text-[10px] sm:text-sm break-all">
                      https://api.mytradeflow.app/api/v1/webhook/YOUR_WEBHOOK_KEY
                    </code>
                  </div>
                </div>

                <div className="flex gap-3 sm:gap-4">
                  <div className="flex-shrink-0 w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs sm:text-base">
                    2
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-medium text-sm sm:text-base">Create a TradingView Alert</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Open your chart in TradingView and click the &quot;Alert&quot; button (clock icon).
                      Set your alert conditions (price cross, indicator signal, etc.).
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 sm:gap-4">
                  <div className="flex-shrink-0 w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs sm:text-base">
                    3
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-medium text-sm sm:text-base">Configure Webhook Notification</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      In the alert dialog, go to &quot;Notifications&quot; tab. Enable &quot;Webhook URL&quot;
                      and paste your Tradeflow webhook URL.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 sm:gap-4">
                  <div className="flex-shrink-0 w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs sm:text-base">
                    4
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-medium text-sm sm:text-base">Set Alert Message</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      In the &quot;Message&quot; field, paste your webhook JSON. Use FlowGuard AI to generate
                      the correct format for your broker.
                    </p>
                    <pre className="mt-2 p-2 sm:p-3 bg-slate-900 text-green-400 rounded text-[10px] sm:text-sm overflow-x-auto">
{`{
  "symbol": "{{ticker}}",
  "action": "buy",
  "volume": 0.01,
  "timestamp": "{{timenow}}"
}`}
                    </pre>
                  </div>
                </div>

                <div className="flex gap-3 sm:gap-4">
                  <div className="flex-shrink-0 w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs sm:text-base">
                    5
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-medium text-sm sm:text-base">Save and Test</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Click &quot;Create&quot; to save your alert. Check Webhook Logs in Tradeflow to verify
                      signals are being received and executed.
                    </p>
                  </div>
                </div>
              </div>

              <Alert className="text-xs sm:text-sm">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle className="text-sm sm:text-base">TradingView Plan Required</AlertTitle>
                <AlertDescription>
                  Webhook alerts require a TradingView Pro, Pro+, or Premium subscription.
                  The free plan does not support webhook notifications.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>

          {/* TradingView Variables */}
          <Card>
            <CardHeader className="px-3 sm:px-6">
              <CardTitle className="text-base sm:text-lg">TradingView Alert Variables</CardTitle>
              <CardDescription className="text-xs sm:text-sm">
                Dynamic placeholders that TradingView replaces when the alert fires
              </CardDescription>
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
              <div className="space-y-2 sm:space-y-3">
                {[
                  { var: "{{ticker}}", desc: "Symbol name (e.g., EURUSD, BTCUSD)" },
                  { var: "{{timenow}}", desc: "Current timestamp (ISO format)" },
                  { var: "{{close}}", desc: "Current closing price" },
                  { var: "{{open}}", desc: "Current opening price" },
                  { var: "{{high}}", desc: "Current high price" },
                  { var: "{{low}}", desc: "Current low price" },
                  { var: "{{volume}}", desc: "Current volume" },
                  { var: "{{interval}}", desc: "Chart timeframe (e.g., 1H, 4H, D)" },
                  { var: "{{exchange}}", desc: "Exchange name" },
                ].map((item) => (
                  <div key={item.var} className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-3">
                    <code className="bg-muted px-1.5 sm:px-2 py-0.5 sm:py-1 rounded text-[10px] sm:text-sm font-mono w-fit">
                      {item.var}
                    </code>
                    <span className="text-xs sm:text-sm text-muted-foreground">{item.desc}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Support Links */}
      <Card>
        <CardHeader className="px-3 sm:px-6">
          <CardTitle className="text-base sm:text-lg">Need More Help?</CardTitle>
        </CardHeader>
        <CardContent className="px-3 sm:px-6">
          <div className="flex flex-wrap gap-2 sm:gap-3">
            <Button variant="outline" asChild size="sm" className="text-xs sm:text-sm">
              <a href="mailto:support@mytradeflow.app">
                <HelpCircle className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                Contact Support
              </a>
            </Button>
            <Button variant="outline" asChild size="sm" className="text-xs sm:text-sm">
              <a href="https://discord.gg/tradeflow" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                Discord Community
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
