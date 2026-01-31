'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Code2,
  Wand2,
  Play,
  Copy,
  Download,
  Upload,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Sparkles,
  Settings,
  FileCode,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import type { PineScript, PineScriptError, PineFixRequest, WebhookPayload } from '../types';

// Pine Script syntax keywords for highlighting
const PINE_KEYWORDS = [
  'strategy', 'indicator', 'library', 'var', 'varip', 'if', 'else', 'for', 'while',
  'switch', 'case', 'break', 'continue', 'return', 'import', 'export', 'type', 'method',
  'true', 'false', 'na', 'close', 'open', 'high', 'low', 'volume', 'time', 'bar_index',
  'strategy.entry', 'strategy.exit', 'strategy.close', 'strategy.order',
  'alert', 'alertcondition', 'plot', 'plotshape', 'plotchar', 'bgcolor', 'barcolor',
  'ta.sma', 'ta.ema', 'ta.rsi', 'ta.macd', 'ta.atr', 'ta.crossover', 'ta.crossunder',
  'ta.highest', 'ta.lowest', 'ta.stoch', 'ta.bb', 'ta.supertrend',
  'math.abs', 'math.max', 'math.min', 'math.round', 'math.floor', 'math.ceil',
  'str.tostring', 'str.format', 'array.new_float', 'array.push', 'array.pop',
  'request.security', 'request.financial', 'input', 'input.int', 'input.float',
  'input.bool', 'input.string', 'input.source', 'input.timeframe',
];

// Default Pine Script template
const DEFAULT_TEMPLATE = `//@version=5
strategy("My Strategy", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100)

// Inputs
fastLength = input.int(9, "Fast MA Length", minval=1)
slowLength = input.int(21, "Slow MA Length", minval=1)
rsiLength = input.int(14, "RSI Length", minval=1)
rsiOversold = input.int(30, "RSI Oversold", minval=0, maxval=100)
rsiOverbought = input.int(70, "RSI Overbought", minval=0, maxval=100)
atrLength = input.int(14, "ATR Length", minval=1)
atrMultiplier = input.float(1.5, "ATR Stop Loss Multiplier", minval=0.1)
rrRatio = input.float(2.0, "Risk:Reward Ratio", minval=0.5)

// Calculations
fastMA = ta.sma(close, fastLength)
slowMA = ta.sma(close, slowLength)
rsi = ta.rsi(close, rsiLength)
atr = ta.atr(atrLength)

// Plot MAs
plot(fastMA, "Fast MA", color=color.blue)
plot(slowMA, "Slow MA", color=color.red)

// Conditions
longCondition = ta.crossover(fastMA, slowMA) and rsi < rsiOversold
shortCondition = ta.crossunder(fastMA, slowMA) and rsi > rsiOverbought

// Entry with SL/TP
if (longCondition)
    stopLoss = close - (atr * atrMultiplier)
    takeProfit = close + (atr * atrMultiplier * rrRatio)
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=stopLoss, limit=takeProfit)
    alert('{"symbol": "' + syminfo.ticker + '", "action": "buy", "price": ' + str.tostring(close) + ', "sl": ' + str.tostring(stopLoss) + ', "tp": ' + str.tostring(takeProfit) + '}', alert.freq_once_per_bar_close)

if (shortCondition)
    stopLoss = close + (atr * atrMultiplier)
    takeProfit = close - (atr * atrMultiplier * rrRatio)
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=stopLoss, limit=takeProfit)
    alert('{"symbol": "' + syminfo.ticker + '", "action": "sell", "price": ' + str.tostring(close) + ', "sl": ' + str.tostring(stopLoss) + ', "tp": ' + str.tostring(takeProfit) + '}', alert.freq_once_per_bar_close)
`;

interface PineScriptEditorProps {
  onCodeChange?: (code: string) => void;
  onWebhookGenerated?: (payload: WebhookPayload) => void;
  initialCode?: string;
  className?: string;
  webhookKey?: string;
}

export function PineScriptEditor({
  onCodeChange,
  onWebhookGenerated,
  initialCode,
  className,
  webhookKey: externalWebhookKey,
}: PineScriptEditorProps) {
  const [code, setCode] = useState(initialCode || DEFAULT_TEMPLATE);
  const [errors, setErrors] = useState<PineScriptError[]>([]);
  const [errorInput, setErrorInput] = useState('');
  const [isFixing, setIsFixing] = useState(false);
  const [fixedCode, setFixedCode] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'edit' | 'fixed' | 'webhook'>('edit');
  const [strategyType, setStrategyType] = useState<'long_only' | 'short_only' | 'both'>('both');
  const [stopLossType, setStopLossType] = useState<'atr' | 'percent' | 'fixed'>('atr');
  const [stopLossValue, setStopLossValue] = useState(1.5);
  const [rrRatio, setRrRatio] = useState(2.0);
  const [webhookPayload, setWebhookPayload] = useState<WebhookPayload | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  // Sync internal code state with external initialCode prop when it changes
  // Use a ref to track user modifications to avoid overwriting user's work
  const lastExternalCodeRef = useRef(initialCode);

  // Basic syntax validation - MUST be declared before useEffect that uses it
  const validateSyntax = useCallback((code: string) => {
    const errors: PineScriptError[] = [];
    const lines = code.split('\n');

    // Check for version directive
    if (!code.includes('//@version=')) {
      errors.push({
        line: 1,
        message: "Missing Pine Script version directive (e.g., //@version=5)",
        severity: 'error',
      });
    }

    // Check for strategy or indicator declaration
    if (!code.includes('strategy(') && !code.includes('indicator(')) {
      errors.push({
        line: 1,
        message: "Missing strategy() or indicator() declaration",
        severity: 'error',
      });
    }

    // Check for unclosed parentheses/brackets
    let parenCount = 0;
    let bracketCount = 0;
    lines.forEach((line, idx) => {
      for (const char of line) {
        if (char === '(') parenCount++;
        if (char === ')') parenCount--;
        if (char === '[') bracketCount++;
        if (char === ']') bracketCount--;
      }
      if (parenCount < 0) {
        errors.push({
          line: idx + 1,
          message: "Unexpected closing parenthesis",
          severity: 'error',
        });
        parenCount = 0;
      }
    });

    if (parenCount !== 0) {
      errors.push({
        line: lines.length,
        message: `Unclosed parentheses (${Math.abs(parenCount)} ${parenCount > 0 ? 'open' : 'extra close'})`,
        severity: 'error',
      });
    }

    // Check for common issues - but be smart about Pine Script patterns
    // These patterns return properly scoped values and do NOT need 'var':
    const noVarNeededPatterns = [
      /input\.(int|float|bool|string|source|timeframe|color|symbol|session|price)/,
      /ta\.(sma|ema|rsi|macd|atr|crossover|crossunder|highest|lowest|stoch|bb|supertrend|wma|vwma|tr|change|mom|roc|cci|mfi|obv|vwap|pivothigh|pivotlow|valuewhen|barssince)/,
      /math\.(abs|max|min|round|floor|ceil|sqrt|pow|log|sin|cos|tan)/,
      /str\.(tostring|format|tonumber|contains|length|replace|split|substring|upper|lower)/,
      /array\.(new_float|new_int|new_bool|new_string|new_color|get|set|push|pop|size|from)/,
      /request\.(security|financial|quandl|dividends|earnings|splits)/,
      /color\.(new|rgb|r|g|b)/,
      /syminfo\./,
      /close|open|high|low|volume|time|bar_index|hl2|hlc3|ohlc4|timenow/,  // Built-in series
      /strategy\.(position_size|position_avg_price|equity|netprofit)/,  // Strategy built-ins
      /\s+and\s+|\s+or\s+/,  // Boolean expressions
    ];

    lines.forEach((line, idx) => {
      // Skip comment lines
      if (line.trim().startsWith('//')) return;

      // Check for assignments that might need var
      const assignMatch = line.match(/^\s*([a-zA-Z_]\w*)\s*=\s*(.+)$/);
      if (assignMatch && !line.includes('var ') && !line.includes(':=')) {
        const varName = assignMatch[1];
        const rightSide = assignMatch[2];

        // Skip if it's a known keyword
        if (PINE_KEYWORDS.includes(varName)) return;

        // Skip if the right side uses a Pine Script function/pattern that doesn't need var
        const usesNoVarPattern = noVarNeededPatterns.some(pattern => pattern.test(rightSide));
        if (usesNoVarPattern) return;

        // Skip if already defined earlier in the code (re-assignment is fine)
        const codeBeforeThis = code.slice(0, code.indexOf(line));
        if (codeBeforeThis.includes(`${varName} =`) || codeBeforeThis.includes(`var ${varName}`)) return;

        // Only warn for truly naked literal assignments that might need persistence
        // e.g., "counter = 0" at global scope (might need var to persist across bars)
        const isLiteralAssignment = /^\s*(true|false|na|\d+\.?\d*|"[^"]*"|'[^']*')\s*$/.test(rightSide);
        if (isLiteralAssignment) {
          errors.push({
            line: idx + 1,
            message: `Variable '${varName}' assigned a literal value - consider 'var ${varName}' if it should persist across bars`,
            severity: 'warning',
          });
        }
      }
    });

    setErrors(errors);
    return errors.filter(e => e.severity === 'error').length === 0;
  }, []);

  // Sync with external initialCode changes (e.g., AI suggestions applied)
  useEffect(() => {
    if (initialCode !== undefined && initialCode !== lastExternalCodeRef.current) {
      lastExternalCodeRef.current = initialCode;
      setCode(initialCode);
      validateSyntax(initialCode);
    }
  }, [initialCode, validateSyntax]);

  // Handle code change
  const handleCodeChange = useCallback((newCode: string) => {
    setCode(newCode);
    validateSyntax(newCode);
    onCodeChange?.(newCode);
  }, [validateSyntax, onCodeChange]);

  // AI Fix Request
  const handleAIFix = async () => {
    setIsFixing(true);
    setFixedCode(null);

    try {
      const request: PineFixRequest = {
        code,
        errors: errorInput || errors.map(e => `Line ${e.line}: ${e.message}`).join('\n'),
        strategyType,
        riskManagement: {
          stopLossType,
          stopLossValue,
          takeProfitRatio: rrRatio,
        },
      };

      const response = await fetch('/api/ai-suite/fix-pine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error('Failed to fix Pine Script');
      }

      const data = await response.json();
      setFixedCode(data.fixedCode);
      setWebhookPayload(data.webhookPayload || null);
      setActiveTab('fixed');

      toast({
        title: 'Script Fixed!',
        description: 'AI has generated an improved version of your script.',
      });
    } catch (error) {
      console.error('AI Fix error:', error);
      toast({
        title: 'Fix Failed',
        description: 'Failed to fix the script. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsFixing(false);
    }
  };

  // Apply fixed code
  const applyFixedCode = () => {
    if (fixedCode) {
      setCode(fixedCode);
      validateSyntax(fixedCode);
      setActiveTab('edit');
      toast({
        title: 'Applied!',
        description: 'Fixed code has been applied to the editor.',
      });
    }
  };

  // Generate webhook payload
  const generateWebhook = () => {
    const payload: WebhookPayload = {
      symbol: '{{ticker}}',
      action: 'buy',
      quantity: 0.1,
      riskPercent: 1,
      stopLoss: '{{strategy.order.stop}}',
      takeProfit: '{{strategy.order.limit}}',
      comment: 'AI Strategy Suite',
    };
    setWebhookPayload(payload);
    onWebhookGenerated?.(payload);
    setActiveTab('webhook');
  };

  // Copy to clipboard
  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    toast({
      title: 'Copied!',
      description: 'Content copied to clipboard.',
    });
  };

  // Download script
  const downloadScript = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'strategy.pine';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className={cn('cyber-card', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Code2 className="h-5 w-5 text-primary" />
              Pine Script Editor
            </CardTitle>
            <CardDescription>
              Write, fix, and deploy TradingView strategies
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setCode(DEFAULT_TEMPLATE)}>
              <FileCode className="h-4 w-4 mr-1" />
              Template
            </Button>
            <Button variant="outline" size="sm" onClick={downloadScript}>
              <Download className="h-4 w-4 mr-1" />
              Download
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="edit">
              <Code2 className="h-4 w-4 mr-1" />
              Editor
            </TabsTrigger>
            <TabsTrigger value="fixed" disabled={!fixedCode}>
              <Sparkles className="h-4 w-4 mr-1" />
              AI Fixed
            </TabsTrigger>
            <TabsTrigger value="webhook">
              <Play className="h-4 w-4 mr-1" />
              Webhook
            </TabsTrigger>
          </TabsList>

          {/* Editor Tab */}
          <TabsContent value="edit" className="space-y-4">
            {/* Code Editor */}
            <div className="relative">
              <Textarea
                ref={textareaRef}
                value={code}
                onChange={(e) => handleCodeChange(e.target.value)}
                className="font-mono text-sm min-h-[400px] resize-y bg-background/50"
                placeholder="Paste your Pine Script here..."
                spellCheck={false}
              />
              <div className="absolute top-2 right-2 flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7"
                  onClick={() => copyToClipboard(code)}
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            </div>

            {/* Errors Display */}
            {errors.length > 0 && (
              <div className="space-y-2">
                {errors.map((error, idx) => (
                  <Alert
                    key={idx}
                    variant={error.severity === 'error' ? 'destructive' : 'default'}
                    className="py-2"
                  >
                    {error.severity === 'error' ? (
                      <AlertTriangle className="h-4 w-4" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" />
                    )}
                    <AlertDescription className="text-sm">
                      <span className="font-mono">Line {error.line}:</span> {error.message}
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            )}

            {/* Error Input for AI */}
            <div className="space-y-2">
              <Label>Additional Error Message (from TradingView)</Label>
              <Textarea
                value={errorInput}
                onChange={(e) => setErrorInput(e.target.value)}
                placeholder="Paste any error messages from TradingView here..."
                className="min-h-[80px] text-sm"
              />
            </div>

            {/* AI Fix Options */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>Strategy Type</Label>
                <Select value={strategyType} onValueChange={(v: any) => setStrategyType(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="long_only">Long Only</SelectItem>
                    <SelectItem value="short_only">Short Only</SelectItem>
                    <SelectItem value="both">Long & Short</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Stop Loss Type</Label>
                <Select value={stopLossType} onValueChange={(v: any) => setStopLossType(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="atr">ATR Multiple</SelectItem>
                    <SelectItem value="percent">Percent</SelectItem>
                    <SelectItem value="fixed">Fixed Pips</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>SL Value</Label>
                <Input
                  type="number"
                  value={stopLossValue}
                  onChange={(e) => setStopLossValue(parseFloat(e.target.value))}
                  step={0.1}
                  min={0.1}
                />
              </div>

              <div className="space-y-2">
                <Label>R:R Ratio</Label>
                <Input
                  type="number"
                  value={rrRatio}
                  onChange={(e) => setRrRatio(parseFloat(e.target.value))}
                  step={0.5}
                  min={0.5}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                onClick={handleAIFix}
                disabled={isFixing}
                className="flex-1"
              >
                {isFixing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    AI is fixing...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4 mr-2" />
                    Fix with AI
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={generateWebhook}>
                <Play className="h-4 w-4 mr-2" />
                Generate Webhook
              </Button>
            </div>
          </TabsContent>

          {/* AI Fixed Tab */}
          <TabsContent value="fixed" className="space-y-4">
            {fixedCode && (
              <>
                <div className="relative">
                  <Textarea
                    value={fixedCode}
                    readOnly
                    className="font-mono text-sm min-h-[400px] bg-emerald-500/5 border-emerald-500/30"
                  />
                  <Badge className="absolute top-2 left-2 bg-emerald-500">
                    AI Fixed
                  </Badge>
                </div>

                <div className="flex gap-2">
                  <Button onClick={applyFixedCode} className="flex-1">
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Apply to Editor
                  </Button>
                  <Button variant="outline" onClick={() => copyToClipboard(fixedCode)}>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </Button>
                </div>
              </>
            )}
          </TabsContent>

          {/* Webhook Tab */}
          <TabsContent value="webhook" className="space-y-4">
            <WebhookGenerator
              payload={webhookPayload}
              onPayloadChange={setWebhookPayload}
              onCopy={copyToClipboard}
              externalWebhookKey={externalWebhookKey}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// Webhook Generator Sub-component
interface WebhookGeneratorProps {
  payload: WebhookPayload | null;
  onPayloadChange: (payload: WebhookPayload) => void;
  onCopy: (text: string) => void;
  externalWebhookKey?: string;
}

function WebhookGenerator({ payload, onPayloadChange, onCopy, externalWebhookKey }: WebhookGeneratorProps) {
  const [webhookKey, setWebhookKey] = useState(externalWebhookKey || '');

  useEffect(() => {
    // Use external key if provided
    if (externalWebhookKey) {
      setWebhookKey(externalWebhookKey);
      return;
    }
    // Otherwise fetch user's webhook key
    fetch('/api/webhooks/primary-key', { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => {
        if (data.webhook_key) {
          setWebhookKey(data.webhook_key);
        }
      })
      .catch(console.error);
  }, [externalWebhookKey]);

  const defaultPayload: WebhookPayload = payload || {
    webhook_key: webhookKey,
    symbol: '{{ticker}}',
    action: 'buy',
    quantity: 0.1,
    riskPercent: 1,
    stopLoss: '{{strategy.order.stop}}',
    takeProfit: '{{strategy.order.limit}}',
  };

  const webhookUrl = `${typeof window !== 'undefined' ? window.location.origin : ''}/api/v1/webhook/signal`;

  const alertMessage = JSON.stringify(
    { ...defaultPayload, webhook_key: webhookKey || 'YOUR_WEBHOOK_KEY' },
    null,
    2
  );

  return (
    <div className="space-y-4">
      <Alert>
        <Play className="h-4 w-4" />
        <AlertTitle>TradingView Alert Setup</AlertTitle>
        <AlertDescription>
          Copy the webhook URL and message below into your TradingView alert settings.
        </AlertDescription>
      </Alert>

      {/* Webhook URL */}
      <div className="space-y-2">
        <Label>Webhook URL</Label>
        <div className="flex gap-2">
          <Input value={webhookUrl} readOnly className="font-mono text-sm" />
          <Button variant="outline" onClick={() => onCopy(webhookUrl)}>
            <Copy className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Alert Message */}
      <div className="space-y-2">
        <Label>Alert Message (JSON)</Label>
        <div className="relative">
          <Textarea
            value={alertMessage}
            readOnly
            className="font-mono text-sm min-h-[200px] bg-muted/50"
          />
          <Button
            variant="outline"
            size="sm"
            className="absolute top-2 right-2"
            onClick={() => onCopy(alertMessage)}
          >
            <Copy className="h-4 w-4 mr-1" />
            Copy
          </Button>
        </div>
      </div>

      {/* Instructions */}
      <div className="p-4 rounded-lg bg-muted/50 text-sm space-y-2">
        <p className="font-medium">Quick Setup:</p>
        <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
          <li>Add the strategy to your TradingView chart</li>
          <li>Create a new alert (right-click chart → Add Alert)</li>
          <li>Set condition to your strategy's alert</li>
          <li>Enable "Webhook URL" and paste the URL above</li>
          <li>Paste the JSON message in "Message" field</li>
          <li>Save and your signals will auto-execute on TradeFlow!</li>
        </ol>
      </div>

      {/* Webhook Key Display */}
      {webhookKey && (
        <div className="space-y-2">
          <Label>Your Webhook Key</Label>
          <div className="flex gap-2">
            <Input
              value={webhookKey}
              readOnly
              className="font-mono text-sm"
              type="password"
            />
            <Button variant="outline" onClick={() => onCopy(webhookKey)}>
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
