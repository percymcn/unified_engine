"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Copy, Bot, AlertCircle, CheckCircle2, Info } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useUser } from "@/providers/user-provider";

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
  const [quantity, setQuantity] = useState("0.01");
  const [output, setOutput] = useState("");
  const [processing, setProcessing] = useState(false);
  const { toast } = useToast();
  const { user } = useUser();

  // Auto-fill webhook key from user profile
  useEffect(() => {
    if (user?.primary_webhook_key && !webhookKey) {
      setWebhookKey(user.primary_webhook_key);
    }
  }, [user?.primary_webhook_key, webhookKey]);

  function parseSignalInput(userInput: string): { symbol: string; action: string; comment: string } {
    const lowerInput = userInput.toLowerCase().trim();
    const originalInput = userInput.trim();

    // Detect action
    let action = "buy";
    if (lowerInput.includes("short") || lowerInput.includes("sell") ||
        lowerInput.includes("close short") || lowerInput.startsWith("s ")) {
      action = "sell";
    } else if (lowerInput.includes("close") || lowerInput.includes("exit") ||
               lowerInput.includes("flatten")) {
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

    // Default symbol
    if (!symbol) {
      symbol = "EURUSD";
    }

    return { symbol, action, comment: originalInput };
  }

  function generateAlertJSON(userInput: string): string {
    const { symbol, action, comment } = parseSignalInput(userInput);

    // Build the webhook payload that matches our system exactly
    const alertJSON: Record<string, unknown> = {
      webhook_key: webhookKey || "YOUR_WEBHOOK_KEY_HERE",
      action: action,
      symbol: symbol,
      quantity: parseFloat(quantity) || 0.01,
    };

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
                  placeholder='Examples:
• "EURUSD long"
• "short NQ"
• "buy BTC 0.1"
• "close XAUUSD"
• "ES short at market"'
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

              {/* Quantity */}
              <div className="space-y-2">
                <Label>Quantity (lots/contracts)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="0.01"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="font-mono w-32"
                />
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
