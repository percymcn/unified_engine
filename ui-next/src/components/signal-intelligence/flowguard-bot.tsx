"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Copy, Bot } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export function FlowGuardBot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [processing, setProcessing] = useState(false);
  const { toast } = useToast();

  // Default risk settings (would come from user settings in production)
  const defaultSettings = {
    lot: 0.01,
    sl: 50, // pips
    tp: 100, // pips
    riskPercent: 1.0,
  };

  function generateAlertJSON(userInput: string): string {
    // Simple parser for PineScript or plain words
    const lowerInput = userInput.toLowerCase().trim();
    
    // Detect direction
    let action = "buy";
    if (lowerInput.includes("short") || lowerInput.includes("sell") || lowerInput.includes("short")) {
      action = "sell";
    } else if (lowerInput.includes("long") || lowerInput.includes("buy")) {
      action = "buy";
    }

    // Extract symbol if present (e.g., "EURUSD long" or "long EURUSD")
    let symbol = "EURUSD"; // default
    const symbolMatch = userInput.match(/\b[A-Z]{6,}\b/);
    if (symbolMatch) {
      symbol = symbolMatch[0];
    }

    // Generate TradingView alert JSON
    const alertJSON = {
      ticker: symbol,
      action: action,
      quantity: defaultSettings.lot,
      price: 0, // Market order
      stop_loss: defaultSettings.sl,
      take_profit: defaultSettings.tp,
      comment: `FlowGuard: ${userInput}`,
      strategy_id: "flowguard",
      strategy_name: "FlowGuard AI",
      // Momentum Guard metadata
      momentum_guard: {
        warn_at: 6,
        auto_breakeven: false,
        pause_on_chop: true,
        staleness_enabled: true,
        staleness_seconds: 5,
      },
      risk_defaults: {
        lot: defaultSettings.lot,
        sl: defaultSettings.sl,
        tp: defaultSettings.tp,
        risk_percent: defaultSettings.riskPercent,
      },
    };

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
        title: "Copied",
        description: "Alert JSON copied to clipboard",
      });
    }
  }

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
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                FlowGuard AI Signal Generator
              </DialogTitle>
              <DialogDescription>
                Enter PineScript or plain words to generate TradingView alert JSON
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Signal Input</Label>
                <Input
                  placeholder='e.g., "EURUSD long" or "short NQ"'
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  className="font-mono"
                />
              </div>
              <Button onClick={handleGenerate} disabled={processing || !input.trim()}>
                {processing ? "Generating..." : "Generate Alert JSON"}
              </Button>
              {output && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Generated Alert JSON</Label>
                    <Button variant="outline" size="sm" onClick={handleCopy}>
                      <Copy className="h-4 w-4 mr-2" />
                      Copy to TradingView
                    </Button>
                  </div>
                  <div className="p-3 bg-muted rounded-md font-mono text-xs whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {output}
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
