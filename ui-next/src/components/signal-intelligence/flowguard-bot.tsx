"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Copy, Bot, AlertCircle, CheckCircle2, Info, Shield } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useUser } from "@/providers/user-provider";

// Broker-specific configurations
type BrokerType = "projectx" | "tradelocker" | "mt4" | "mt5" | "tradovate";

interface BrokerConfig {
  name: string;
  symbolField: "ticker" | "symbol";
  quantityField: "contracts" | "quantity" | "volume";
  supportsSL: boolean;
  supportsTP: boolean;
  supportsTrailingStop: boolean;
  defaultQuantity: string;
  quantityStep: string;
  commonSymbols: string[];
}

const BROKER_CONFIGS: Record<BrokerType, BrokerConfig> = {
  projectx: {
    name: "ProjectX/TopStep",
    symbolField: "ticker",
    quantityField: "contracts",
    supportsSL: true,
    supportsTP: true,
    supportsTrailingStop: true,
    defaultQuantity: "1",
    quantityStep: "1",
    commonSymbols: ["MNQ", "MES", "MYM", "M2K", "MCL", "MGC", "ES", "NQ"],
  },
  tradelocker: {
    name: "TradeLocker",
    symbolField: "ticker",
    quantityField: "quantity",
    supportsSL: true,
    supportsTP: true,
    supportsTrailingStop: true,
    defaultQuantity: "0.01",
    quantityStep: "0.01",
    commonSymbols: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"],
  },
  mt4: {
    name: "MetaTrader 4",
    symbolField: "symbol",
    quantityField: "volume",
    supportsSL: true,
    supportsTP: true,
    supportsTrailingStop: false,
    defaultQuantity: "0.01",
    quantityStep: "0.01",
    commonSymbols: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"],
  },
  mt5: {
    name: "MetaTrader 5",
    symbolField: "symbol",
    quantityField: "volume",
    supportsSL: true,
    supportsTP: true,
    supportsTrailingStop: false,
    defaultQuantity: "0.01",
    quantityStep: "0.01",
    commonSymbols: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"],
  },
  tradovate: {
    name: "Tradovate",
    symbolField: "ticker",
    quantityField: "contracts",
    supportsSL: true,
    supportsTP: true,
    supportsTrailingStop: false,
    defaultQuantity: "1",
    quantityStep: "1",
    commonSymbols: ["MNQ", "MES", "ES", "NQ", "CL", "GC"],
  },
};

// Common symbol patterns for different markets
const SYMBOL_PATTERNS = {
  forex: /\b(EUR|GBP|USD|JPY|AUD|NZD|CAD|CHF)(EUR|GBP|USD|JPY|AUD|NZD|CAD|CHF)\b/i,
  crypto: /\b(BTC|ETH|XRP|SOL|ADA|DOGE|LTC)(USD|USDT|BTC|EUR)?\b/i,
  futures: /\b(NQ|ES|YM|RTY|CL|GC|SI|ZB|ZN|MNQ|MES|MCL|MGC)\b/i,
  indices: /\b(SPX|NDX|DJI|VIX|US500|US100|US30|NAS100|SPX500)\b/i,
  metals: /\b(XAU|XAG)(USD|EUR)?\b/i,
};

// Normalize symbol for different brokers
function normalizeSymbol(input: string): string {
  const upper = input.toUpperCase().trim();

  // Handle crypto with implicit USD
  if (/^(BTC|ETH|XRP|SOL|ADA|DOGE|LTC)$/i.test(upper)) {
    return upper + "USD";
  }

  // Handle metals with implicit USD
  if (/^(XAU|XAG)$/i.test(upper)) {
    return upper + "USD";
  }

  return upper;
}

export function FlowGuardBot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [webhookKey, setWebhookKey] = useState("");
  const [broker, setBroker] = useState<BrokerType>("projectx");
  const [quantity, setQuantity] = useState("1");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [trailingStop, setTrailingStop] = useState("");
  const [output, setOutput] = useState("");
  const [processing, setProcessing] = useState(false);
  const { toast } = useToast();
  const { user } = useUser();

  const brokerConfig = BROKER_CONFIGS[broker];

  // Auto-fill webhook key from user profile
  useEffect(() => {
    if (user?.primary_webhook_key && !webhookKey) {
      setWebhookKey(user.primary_webhook_key);
    }
  }, [user?.primary_webhook_key, webhookKey]);

  // Update quantity default when broker changes
  useEffect(() => {
    setQuantity(brokerConfig.defaultQuantity);
    // Clear SL/TP/trailing if not supported
    if (!brokerConfig.supportsTrailingStop) {
      setTrailingStop("");
    }
  }, [broker, brokerConfig.defaultQuantity, brokerConfig.supportsTrailingStop]);

  function parseSignalInput(userInput: string): { symbol: string; action: string; comment: string } {
    const lowerInput = userInput.toLowerCase().trim();
    const originalInput = userInput.trim();

    // Detect action
    let action = "buy";
    if (lowerInput.includes("short") || lowerInput.includes("sell") ||
        lowerInput.includes("close short") || lowerInput.startsWith("s ")) {
      action = "sell";
    } else if (lowerInput.includes("close") || lowerInput.includes("exit") ||
               lowerInput.includes("flatten") || lowerInput.includes("close_all")) {
      action = "close";
    } else if (lowerInput.includes("long") || lowerInput.includes("buy") ||
               lowerInput.startsWith("l ") || lowerInput.startsWith("b ")) {
      action = "buy";
    }

    // Extract symbol from input
    let symbol = "";

    // Try each pattern
    for (const [, pattern] of Object.entries(SYMBOL_PATTERNS)) {
      const match = originalInput.match(pattern);
      if (match) {
        symbol = normalizeSymbol(match[0]);
        break;
      }
    }

    // Fallback: look for any 3-8 letter uppercase word that could be a symbol
    if (!symbol) {
      const genericMatch = originalInput.match(/\b[A-Z]{3,8}\b/);
      if (genericMatch) {
        symbol = normalizeSymbol(genericMatch[0]);
      }
    }

    // Default symbol based on broker
    if (!symbol) {
      symbol = brokerConfig.commonSymbols[0] || "EURUSD";
    }

    return { symbol, action, comment: originalInput };
  }

  function generateAlertJSON(userInput: string): string {
    const { symbol, action, comment } = parseSignalInput(userInput);

    // Build the webhook payload based on broker configuration
    const alertJSON: Record<string, unknown> = {
      // Use broker-specific field names
      [brokerConfig.symbolField]: symbol,
      action: action,
      [brokerConfig.quantityField]: parseFloat(quantity) || parseFloat(brokerConfig.defaultQuantity),
    };

    // Add SL/TP if provided and supported
    if (stopLoss && brokerConfig.supportsSL) {
      alertJSON.sl = parseFloat(stopLoss);
    }
    if (takeProfit && brokerConfig.supportsTP) {
      alertJSON.tp = parseFloat(takeProfit);
    }
    if (trailingStop && brokerConfig.supportsTrailingStop) {
      alertJSON.trailing_stop = parseFloat(trailingStop);
    }

    // Only add comment if meaningful
    if (comment && comment !== symbol) {
      alertJSON.comment = comment;
    }

    // Add timestamp for staleness protection
    alertJSON.timestamp = "{{timenow}}";

    return JSON.stringify(alertJSON, null, 2);
  }

  function handleGenerate() {
    if (!input.trim()) {
      toast({
        title: "Error",
        description: "Please enter a signal description",
        variant: "destructive",
      });
      return;
    }

    setProcessing(true);
    try {
      const json = generateAlertJSON(input);
      setOutput(json);
      toast({
        title: "JSON Generated",
        description: "Copy and paste into TradingView alert message",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to generate alert JSON",
        variant: "destructive",
      });
    } finally {
      setProcessing(false);
    }
  }

  function handleCopy() {
    if (output) {
      navigator.clipboard.writeText(output);
      toast({
        title: "Copied!",
        description: "Paste this into your TradingView alert message field",
      });
    }
  }

  const hasWebhookKey = webhookKey && webhookKey !== "YOUR_WEBHOOK_KEY_HERE";

  return (
    <>
      {/* Floating bubble */}
      <div className="fixed bottom-6 right-6 z-50">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button
              size="lg"
              className="rounded-full h-14 w-14 shadow-lg"
              variant="default"
            >
              <Bot className="h-6 w-6" />
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                FlowGuard AI Signal Generator
              </DialogTitle>
              <DialogDescription>
                Generate TradingView-compatible webhook JSON in seconds
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              {/* Broker Selection */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Target Broker
                </Label>
                <Select value={broker} onValueChange={(v) => setBroker(v as BrokerType)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select broker" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(BROKER_CONFIGS).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        {config.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  JSON format adapts to {brokerConfig.name} requirements
                </p>
              </div>

              {/* Webhook Key */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  Webhook Key
                  {hasWebhookKey ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                  )}
                </Label>
                <Input
                  placeholder="Your webhook key (from dashboard)"
                  value={webhookKey}
                  onChange={(e) => setWebhookKey(e.target.value)}
                  className="font-mono text-sm"
                />
                {!hasWebhookKey && (
                  <p className="text-xs text-muted-foreground">
                    Get your webhook key from the dashboard Quick Actions section
                  </p>
                )}
              </div>

              {/* Signal Input */}
              <div className="space-y-2">
                <Label>Signal Description</Label>
                <Textarea
                  placeholder={`Examples for ${brokerConfig.name}:
• "${brokerConfig.commonSymbols[0]} long"
• "short ${brokerConfig.commonSymbols[1] || brokerConfig.commonSymbols[0]}"
• "close ${brokerConfig.commonSymbols[0]}"
• "close_all" (emergency close all)`}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  className="font-mono text-sm min-h-[100px]"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleGenerate();
                    }
                  }}
                />
              </div>

              {/* Quantity and Risk Management Row */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Quantity ({broker === 'projectx' || broker === 'tradovate' ? 'contracts' : 'lots'})</Label>
                  <Input
                    type="number"
                    step={brokerConfig.quantityStep}
                    min={brokerConfig.quantityStep}
                    placeholder={brokerConfig.defaultQuantity}
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className="font-mono"
                  />
                </div>
                {brokerConfig.supportsSL && (
                  <div className="space-y-2">
                    <Label>Stop Loss (optional)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="e.g., 21500"
                      value={stopLoss}
                      onChange={(e) => setStopLoss(e.target.value)}
                      className="font-mono"
                    />
                  </div>
                )}
              </div>

              {/* Take Profit and Trailing Stop Row */}
              <div className="grid grid-cols-2 gap-4">
                {brokerConfig.supportsTP && (
                  <div className="space-y-2">
                    <Label>Take Profit (optional)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="e.g., 21600"
                      value={takeProfit}
                      onChange={(e) => setTakeProfit(e.target.value)}
                      className="font-mono"
                    />
                  </div>
                )}
                {brokerConfig.supportsTrailingStop && (
                  <div className="space-y-2">
                    <Label>Trailing Stop (optional)</Label>
                    <Input
                      type="number"
                      step="1"
                      placeholder="e.g., 10 ticks"
                      value={trailingStop}
                      onChange={(e) => setTrailingStop(e.target.value)}
                      className="font-mono"
                    />
                  </div>
                )}
              </div>

              <Button
                onClick={handleGenerate}
                disabled={processing || !input.trim()}
                className="w-full"
              >
                {processing ? "Generating..." : "Generate Alert JSON"}
              </Button>

              {output && (
                <div className="space-y-3 border-t pt-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-base font-semibold">Generated Webhook JSON</Label>
                    <Button variant="default" size="sm" onClick={handleCopy}>
                      <Copy className="h-4 w-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="p-4 bg-slate-900 dark:bg-slate-950 rounded-lg font-mono text-sm text-green-400 whitespace-pre-wrap overflow-x-auto">
                    {output}
                  </div>

                  {/* Instructions */}
                  <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 space-y-2">
                    <div className="flex items-start gap-2">
                      <Info className="h-5 w-5 text-blue-500 mt-0.5" />
                      <div className="space-y-2 text-sm">
                        <p className="font-medium text-blue-700 dark:text-blue-300">How to use in TradingView:</p>
                        <ol className="list-decimal list-inside space-y-1 text-blue-600 dark:text-blue-400">
                          <li>Open your TradingView chart and create/edit an alert</li>
                          <li>Set your alert conditions (price cross, indicator signal, etc.)</li>
                          <li>In &quot;Notifications&quot;, enable &quot;Webhook URL&quot;</li>
                          <li>Enter: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">https://tradeflow.fluxeo.net/api/webhook/execute</code></li>
                          <li>Paste this JSON in the &quot;Message&quot; field</li>
                          <li>Click &quot;Create&quot; to save your alert</li>
                        </ol>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}
