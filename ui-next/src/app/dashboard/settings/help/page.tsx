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
    description: "Connect your ProjectX or TopStep futures trading account",
    setup: [
      "Go to Settings > Accounts and click 'Add Account'",
      "Select 'ProjectX' as the broker",
      "Enter your ProjectX API credentials",
      "Select the trading account from discovered accounts",
      "Save the account",
    ],
    orderTypes: [
      { name: "Market Buy", supported: true, example: '{"ticker": "MNQ", "action": "buy", "contracts": 1}' },
      { name: "Market Sell", supported: true, example: '{"ticker": "MNQ", "action": "sell", "contracts": 1}' },
      { name: "Limit Buy", supported: true, example: '{"ticker": "MNQ", "action": "limit_buy", "contracts": 1, "price": 21500}' },
      { name: "Limit Sell", supported: true, example: '{"ticker": "MNQ", "action": "limit_sell", "contracts": 1, "price": 21600}' },
      { name: "Stop Buy", supported: true, example: '{"ticker": "MNQ", "action": "stop_buy", "contracts": 1, "price": 21600}' },
      { name: "Stop Sell", supported: true, example: '{"ticker": "MNQ", "action": "stop_sell", "contracts": 1, "price": 21400}' },
      { name: "Close Position", supported: true, example: '{"ticker": "MNQ", "action": "close"}' },
      { name: "Close All", supported: true, example: '{"action": "close_all"}' },
      { name: "Modify SL/TP", supported: true, example: '{"ticker": "MNQ", "action": "modify", "sl": 21400, "tp": 21700}' },
      { name: "Trailing Stop", supported: true, example: '{"ticker": "MNQ", "action": "modify", "trailing_stop": 10}' },
    ],
    fields: {
      ticker: "Futures contract symbol (e.g., MNQ, MES, ES, NQ)",
      contracts: "Number of contracts (whole numbers only)",
      sl: "Stop loss price level",
      tp: "Take profit price level",
      trailing_stop: "Trailing stop distance in ticks",
      price: "Entry price for limit/stop orders",
    },
    notes: [
      "Use micro contracts for smaller position sizes (MNQ, MES, etc.)",
      "Contracts must be whole numbers",
      "Prices are in index points",
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <HelpCircle className="h-6 w-6" />
          Help & Support
        </h1>
        <p className="text-muted-foreground">
          Complete documentation for webhook signals and broker integrations
        </p>
      </div>

      <Tabs defaultValue="brokers" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="brokers">Broker Guides</TabsTrigger>
          <TabsTrigger value="webhooks">Webhook Examples</TabsTrigger>
          <TabsTrigger value="tradingview">TradingView Setup</TabsTrigger>
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
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {Object.entries(BROKER_DOCS).map(([key, doc]) => (
                  <Button
                    key={key}
                    variant={selectedBroker === key ? "default" : "outline"}
                    onClick={() => setSelectedBroker(key as keyof typeof BROKER_DOCS)}
                  >
                    {doc.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Selected Broker Documentation */}
          <Card>
            <CardHeader>
              <CardTitle>{broker.name}</CardTitle>
              <CardDescription>{broker.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
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
                <h3 className="font-semibold mb-3">Supported Order Types</h3>
                <div className="grid gap-3">
                  {broker.orderTypes.map((order, i) => (
                    <div key={i} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {order.supported ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                          <span className="font-medium">{order.name}</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(order.example)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                        {order.example}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>

              {/* Field Descriptions */}
              <div>
                <h3 className="font-semibold mb-3">Field Reference</h3>
                <div className="space-y-2">
                  {Object.entries(broker.fields).map(([field, desc]) => (
                    <div key={field} className="flex gap-2 text-sm">
                      <code className="bg-muted px-2 py-0.5 rounded font-mono text-xs">
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

        {/* Webhook Examples Tab */}
        <TabsContent value="webhooks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Common Webhook Examples
              </CardTitle>
              <CardDescription>
                Copy and paste these examples into your TradingView alerts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {COMMON_EXAMPLES.map((example, i) => (
                <div key={i} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h4 className="font-medium">{example.title}</h4>
                      <p className="text-sm text-muted-foreground">{example.description}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(JSON.stringify(example.json, null, 2))}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <pre className="text-sm bg-slate-900 text-green-400 p-3 rounded overflow-x-auto">
                    {JSON.stringify(example.json, null, 2)}
                  </pre>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Action Reference */}
          <Card>
            <CardHeader>
              <CardTitle>Action Reference</CardTitle>
              <CardDescription>All supported action values</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
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
                  <div key={item.action} className="border rounded p-3">
                    <code className="text-sm font-mono bg-primary/10 px-1.5 py-0.5 rounded">
                      {item.action}
                    </code>
                    <p className="text-xs text-muted-foreground mt-1">{item.desc}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TradingView Setup Tab */}
        <TabsContent value="tradingview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>TradingView Webhook Setup</CardTitle>
              <CardDescription>
                Step-by-step guide to connect TradingView alerts to Tradeflow
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    1
                  </div>
                  <div>
                    <h4 className="font-medium">Get Your Webhook URL</h4>
                    <p className="text-sm text-muted-foreground">
                      Find your webhook key in the dashboard Quick Actions section or Settings &gt; Webhooks.
                      Your webhook URL format is:
                    </p>
                    <code className="block mt-2 p-2 bg-muted rounded text-sm break-all">
                      https://api.mytradeflow.app/api/v1/webhook/YOUR_WEBHOOK_KEY
                    </code>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    2
                  </div>
                  <div>
                    <h4 className="font-medium">Create a TradingView Alert</h4>
                    <p className="text-sm text-muted-foreground">
                      Open your chart in TradingView and click the &quot;Alert&quot; button (clock icon).
                      Set your alert conditions (price cross, indicator signal, etc.).
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    3
                  </div>
                  <div>
                    <h4 className="font-medium">Configure Webhook Notification</h4>
                    <p className="text-sm text-muted-foreground">
                      In the alert dialog, go to &quot;Notifications&quot; tab. Enable &quot;Webhook URL&quot;
                      and paste your Tradeflow webhook URL.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    4
                  </div>
                  <div>
                    <h4 className="font-medium">Set Alert Message</h4>
                    <p className="text-sm text-muted-foreground">
                      In the &quot;Message&quot; field, paste your webhook JSON. Use FlowGuard AI to generate
                      the correct format for your broker.
                    </p>
                    <pre className="mt-2 p-3 bg-slate-900 text-green-400 rounded text-sm overflow-x-auto">
{`{
  "symbol": "{{ticker}}",
  "action": "buy",
  "volume": 0.01,
  "timestamp": "{{timenow}}"
}`}
                    </pre>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    5
                  </div>
                  <div>
                    <h4 className="font-medium">Save and Test</h4>
                    <p className="text-sm text-muted-foreground">
                      Click &quot;Create&quot; to save your alert. Check Webhook Logs in Tradeflow to verify
                      signals are being received and executed.
                    </p>
                  </div>
                </div>
              </div>

              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>TradingView Plan Required</AlertTitle>
                <AlertDescription>
                  Webhook alerts require a TradingView Pro, Pro+, or Premium subscription.
                  The free plan does not support webhook notifications.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>

          {/* TradingView Variables */}
          <Card>
            <CardHeader>
              <CardTitle>TradingView Alert Variables</CardTitle>
              <CardDescription>
                Dynamic placeholders that TradingView replaces when the alert fires
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
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
                  <div key={item.var} className="flex items-start gap-3">
                    <code className="bg-muted px-2 py-1 rounded text-sm font-mono whitespace-nowrap">
                      {item.var}
                    </code>
                    <span className="text-sm text-muted-foreground">{item.desc}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Support Links */}
      <Card>
        <CardHeader>
          <CardTitle>Need More Help?</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" asChild>
              <a href="mailto:support@mytradeflow.app">
                <HelpCircle className="h-4 w-4 mr-2" />
                Contact Support
              </a>
            </Button>
            <Button variant="outline" asChild>
              <a href="https://discord.gg/tradeflow" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                Discord Community
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
