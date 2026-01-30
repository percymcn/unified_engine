'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Wand2,
  Copy,
  Check,
  Code2,
  Webhook,
  Loader2,
  Info,
  ArrowRight,
  Sparkles,
  FileCode,
  Link2,
  Settings2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface ScriptConverterProps {
  className?: string;
}

interface ConversionConfig {
  strategyName: string;
  includeStopLoss: boolean;
  includeTakeProfit: boolean;
  includeTimestamp: boolean;
  includeQuantity: boolean;
  defaultQuantity: string;
  useSymbolFromChart: boolean;
}

interface ConversionResult {
  success: boolean;
  convertedCode: string;
  webhookTemplate: string;
  alertMessage: string;
  warnings: string[];
  summary: string;
}

// TradeFlow Webhook JSON format documentation
const TRADEFLOW_WEBHOOK_FORMAT = `
TradeFlow Webhook JSON Format:
{
  "webhook_key": "YOUR_WEBHOOK_KEY",     // REQUIRED - Your unique webhook key
  "action": "buy" | "sell" | "close",    // REQUIRED - Trade action
  "symbol": "{{ticker}}",                // REQUIRED - Trading symbol
  "quantity": 0.1,                       // Optional - Position size (default: 0.01)
  "sl": 1.0800,                          // Optional - Stop loss price
  "tp": 1.0900,                          // Optional - Take profit price
  "timestamp": "{{timenow}}",            // Optional - For staleness check
  "strategy_id": "my_strategy",          // Optional - Strategy identifier
  "comment": "Strategy Alert",           // Optional - Trade comment
  "target_account_ids": [1, 2, 3]        // Optional - Route to specific accounts
}
`.trim();

export function ScriptConverter({ className }: ScriptConverterProps) {
  const [inputCode, setInputCode] = useState('');
  const [outputCode, setOutputCode] = useState('');
  const [webhookTemplate, setWebhookTemplate] = useState('');
  const [alertMessage, setAlertMessage] = useState('');
  const [isConverting, setIsConverting] = useState(false);
  const [copied, setCopied] = useState<'code' | 'webhook' | 'alert' | null>(null);
  const [activeOutputTab, setActiveOutputTab] = useState<'code' | 'webhook' | 'alert'>('code');
  const [conversionResult, setConversionResult] = useState<ConversionResult | null>(null);
  const [config, setConfig] = useState<ConversionConfig>({
    strategyName: 'MyStrategy',
    includeStopLoss: true,
    includeTakeProfit: true,
    includeTimestamp: true,
    includeQuantity: true,
    defaultQuantity: '0.01',
    useSymbolFromChart: true,
  });
  const { toast } = useToast();

  // Copy to clipboard handler
  const handleCopy = useCallback(async (text: string, type: 'code' | 'webhook' | 'alert') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(type);
      setTimeout(() => setCopied(null), 2000);
      toast({
        title: 'Copied!',
        description: `${type === 'code' ? 'Pine Script' : type === 'webhook' ? 'Webhook template' : 'Alert message'} copied to clipboard.`,
      });
    } catch {
      toast({
        title: 'Copy Failed',
        description: 'Could not copy to clipboard.',
        variant: 'destructive',
      });
    }
  }, [toast]);

  // Convert script to TradeFlow format
  const convertScript = useCallback(async () => {
    if (!inputCode.trim()) {
      toast({
        title: 'No Code',
        description: 'Please paste your Pine Script or indicator code.',
        variant: 'destructive',
      });
      return;
    }

    setIsConverting(true);
    setConversionResult(null);

    try {
      // Call the backend API for AI-powered conversion
      const response = await fetch('/api/ai-suite/convert-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          code: inputCode,
          config: config,
        }),
      });

      if (!response.ok) {
        throw new Error('Conversion failed');
      }

      const data = await response.json();

      if (data.success) {
        setOutputCode(data.convertedCode);
        setWebhookTemplate(data.webhookTemplate);
        setAlertMessage(data.alertMessage);
        setConversionResult(data);

        toast({
          title: 'Conversion Complete!',
          description: 'Your script has been converted to work with TradeFlow.',
        });
      } else {
        // Fallback to local conversion
        const localResult = convertScriptLocally(inputCode, config);
        setOutputCode(localResult.convertedCode);
        setWebhookTemplate(localResult.webhookTemplate);
        setAlertMessage(localResult.alertMessage);
        setConversionResult(localResult);

        toast({
          title: 'Conversion Complete',
          description: 'Script converted using local rules.',
        });
      }
    } catch (error) {
      console.error('Conversion error:', error);
      // Fallback to local conversion
      const localResult = convertScriptLocally(inputCode, config);
      setOutputCode(localResult.convertedCode);
      setWebhookTemplate(localResult.webhookTemplate);
      setAlertMessage(localResult.alertMessage);
      setConversionResult(localResult);

      toast({
        title: 'Conversion Complete',
        description: 'Script converted using local rules.',
      });
    } finally {
      setIsConverting(false);
    }
  }, [inputCode, config, toast]);

  return (
    <div className={cn('grid grid-cols-1 lg:grid-cols-2 gap-6', className)}>
      {/* Left Panel - Input */}
      <Card className="cyber-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileCode className="h-5 w-5 text-primary" />
                Input Script
              </CardTitle>
              <CardDescription>
                Paste any Pine Script, indicator, or strategy code
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">
              Step 1
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Code Input */}
          <div className="space-y-2">
            <Textarea
              value={inputCode}
              onChange={(e) => setInputCode(e.target.value)}
              placeholder={`// Paste your Pine Script code here...
//@version=5
indicator("My Indicator", overlay=true)

// Your strategy logic...
longCondition = ta.crossover(ta.sma(close, 14), ta.sma(close, 28))
shortCondition = ta.crossunder(ta.sma(close, 14), ta.sma(close, 28))

if longCondition
    strategy.entry("Long", strategy.long)
if shortCondition
    strategy.entry("Short", strategy.short)`}
              className="min-h-[300px] font-mono text-sm bg-muted/30"
            />
          </div>

          {/* Configuration */}
          <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-muted/20">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Settings2 className="h-4 w-4" />
              Conversion Settings
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="strategyName" className="text-xs">Strategy Name</Label>
                <Input
                  id="strategyName"
                  value={config.strategyName}
                  onChange={(e) => setConfig({ ...config, strategyName: e.target.value })}
                  placeholder="MyStrategy"
                  className="h-8 text-sm"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultQuantity" className="text-xs">Default Quantity</Label>
                <Input
                  id="defaultQuantity"
                  value={config.defaultQuantity}
                  onChange={(e) => setConfig({ ...config, defaultQuantity: e.target.value })}
                  placeholder="0.01"
                  className="h-8 text-sm"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant={config.includeStopLoss ? 'default' : 'outline'}
                size="sm"
                onClick={() => setConfig({ ...config, includeStopLoss: !config.includeStopLoss })}
                className="text-xs"
              >
                {config.includeStopLoss && <Check className="h-3 w-3 mr-1" />}
                Stop Loss
              </Button>
              <Button
                variant={config.includeTakeProfit ? 'default' : 'outline'}
                size="sm"
                onClick={() => setConfig({ ...config, includeTakeProfit: !config.includeTakeProfit })}
                className="text-xs"
              >
                {config.includeTakeProfit && <Check className="h-3 w-3 mr-1" />}
                Take Profit
              </Button>
              <Button
                variant={config.includeTimestamp ? 'default' : 'outline'}
                size="sm"
                onClick={() => setConfig({ ...config, includeTimestamp: !config.includeTimestamp })}
                className="text-xs"
              >
                {config.includeTimestamp && <Check className="h-3 w-3 mr-1" />}
                Timestamp
              </Button>
              <Button
                variant={config.useSymbolFromChart ? 'default' : 'outline'}
                size="sm"
                onClick={() => setConfig({ ...config, useSymbolFromChart: !config.useSymbolFromChart })}
                className="text-xs"
              >
                {config.useSymbolFromChart && <Check className="h-3 w-3 mr-1" />}
                Auto Symbol
              </Button>
            </div>
          </div>

          {/* Convert Button */}
          <Button
            onClick={convertScript}
            disabled={isConverting || !inputCode.trim()}
            className="w-full"
            size="lg"
          >
            {isConverting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Converting with AI...
              </>
            ) : (
              <>
                <Wand2 className="h-4 w-4 mr-2" />
                Convert to TradeFlow
                <ArrowRight className="h-4 w-4 ml-2" />
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Right Panel - Output */}
      <Card className="cyber-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                TradeFlow Ready
              </CardTitle>
              <CardDescription>
                Converted code with webhook integration
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">
              Step 2
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {conversionResult ? (
            <>
              {/* Summary Alert */}
              <Alert className={cn(
                'border',
                conversionResult.warnings.length === 0
                  ? 'border-emerald-400/30 bg-emerald-400/10'
                  : 'border-yellow-400/30 bg-yellow-400/10'
              )}>
                <CheckCircle2 className="h-4 w-4" />
                <AlertTitle>Conversion Summary</AlertTitle>
                <AlertDescription className="text-sm">
                  {conversionResult.summary}
                </AlertDescription>
              </Alert>

              {/* Warnings */}
              {conversionResult.warnings.length > 0 && (
                <div className="space-y-2">
                  {conversionResult.warnings.map((warning, idx) => (
                    <Alert key={idx} variant="default" className="border-yellow-400/30 bg-yellow-400/10">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription className="text-xs">{warning}</AlertDescription>
                    </Alert>
                  ))}
                </div>
              )}

              {/* Output Tabs */}
              <Tabs value={activeOutputTab} onValueChange={(v) => setActiveOutputTab(v as any)}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="code" className="text-xs">
                    <Code2 className="h-3 w-3 mr-1" />
                    Pine Script
                  </TabsTrigger>
                  <TabsTrigger value="webhook" className="text-xs">
                    <Webhook className="h-3 w-3 mr-1" />
                    Webhook
                  </TabsTrigger>
                  <TabsTrigger value="alert" className="text-xs">
                    <Link2 className="h-3 w-3 mr-1" />
                    Alert
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="code" className="mt-4">
                  <div className="relative">
                    <ScrollArea className="h-[300px] w-full rounded-md border bg-muted/30 p-4">
                      <pre className="text-sm font-mono whitespace-pre-wrap">{outputCode}</pre>
                    </ScrollArea>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2"
                      onClick={() => handleCopy(outputCode, 'code')}
                    >
                      {copied === 'code' ? (
                        <Check className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Copy this code and paste it into TradingView Pine Script Editor
                  </p>
                </TabsContent>

                <TabsContent value="webhook" className="mt-4">
                  <div className="relative">
                    <ScrollArea className="h-[300px] w-full rounded-md border bg-muted/30 p-4">
                      <pre className="text-sm font-mono whitespace-pre-wrap">{webhookTemplate}</pre>
                    </ScrollArea>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2"
                      onClick={() => handleCopy(webhookTemplate, 'webhook')}
                    >
                      {copied === 'webhook' ? (
                        <Check className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    This is your webhook URL configuration for TradeFlow
                  </p>
                </TabsContent>

                <TabsContent value="alert" className="mt-4">
                  <div className="relative">
                    <ScrollArea className="h-[300px] w-full rounded-md border bg-muted/30 p-4">
                      <pre className="text-sm font-mono whitespace-pre-wrap">{alertMessage}</pre>
                    </ScrollArea>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2"
                      onClick={() => handleCopy(alertMessage, 'alert')}
                    >
                      {copied === 'alert' ? (
                        <Check className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Use this as your TradingView Alert Message (JSON format)
                  </p>
                </TabsContent>
              </Tabs>

              {/* Quick Setup Guide */}
              <div className="p-4 rounded-lg border border-border/50 bg-muted/20 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Info className="h-4 w-4 text-primary" />
                  Quick Setup Guide
                </div>
                <ol className="text-xs text-muted-foreground space-y-2 list-decimal list-inside">
                  <li>Copy the <strong>Pine Script</strong> code and paste it in TradingView Editor</li>
                  <li>Save and add the indicator/strategy to your chart</li>
                  <li>Create a new Alert on your desired condition</li>
                  <li>Enable &quot;Webhook URL&quot; and paste your TradeFlow webhook URL</li>
                  <li>In the Alert Message field, paste the <strong>Alert</strong> JSON (replace YOUR_WEBHOOK_KEY)</li>
                  <li>Your trades will now auto-execute through TradeFlow!</li>
                </ol>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <Wand2 className="h-16 w-16 mb-4 opacity-30" />
              <p className="text-center">
                Paste your code and click &quot;Convert to TradeFlow&quot;
                <br />
                <span className="text-xs">
                  The AI will analyze and modify your script to work with TradeFlow webhooks
                </span>
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bottom Panel - Webhook Format Reference */}
      <Card className="lg:col-span-2 cyber-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Webhook className="h-4 w-4 text-primary" />
            TradeFlow Webhook Format Reference
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-xs font-mono p-4 rounded-lg bg-muted/30 overflow-x-auto whitespace-pre-wrap">
            {TRADEFLOW_WEBHOOK_FORMAT}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}

// Local conversion function (fallback when API is unavailable)
function convertScriptLocally(code: string, config: ConversionConfig): ConversionResult {
  const warnings: string[] = [];
  let convertedCode = code;

  // Detect script type
  const isIndicator = code.includes('indicator(') || code.includes('study(');
  const isStrategy = code.includes('strategy(');

  // Detect existing alert conditions
  const hasAlertCondition = code.includes('alertcondition(') || code.includes('alert(');
  const hasStrategyEntry = code.includes('strategy.entry(') || code.includes('strategy.order(');
  const hasStrategyExit = code.includes('strategy.exit(') || code.includes('strategy.close(');

  // Build webhook JSON
  const webhookJson = {
    webhook_key: 'YOUR_WEBHOOK_KEY',
    action: '{{strategy.order.action}}',
    symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
    ...(config.includeQuantity && { quantity: parseFloat(config.defaultQuantity) || 0.01 }),
    ...(config.includeStopLoss && { sl: '{{strategy.order.stop}}' }),
    ...(config.includeTakeProfit && { tp: '{{strategy.order.take_profit}}' }),
    ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
    strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
    comment: `${config.strategyName} Alert`,
  };

  // Generate alert message for different scenarios
  let alertMessage = '';

  if (isStrategy || hasStrategyEntry) {
    // Strategy - use strategy placeholders
    alertMessage = JSON.stringify({
      webhook_key: 'YOUR_WEBHOOK_KEY',
      action: '{{strategy.order.action}}',
      symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
      quantity: parseFloat(config.defaultQuantity) || 0.01,
      ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
      strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
      comment: '{{strategy.order.comment}}',
    }, null, 2);
  } else {
    // Indicator - generate buy/sell JSON templates
    alertMessage = `// For BUY alerts:
${JSON.stringify({
  webhook_key: 'YOUR_WEBHOOK_KEY',
  action: 'buy',
  symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
  quantity: parseFloat(config.defaultQuantity) || 0.01,
  ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
  strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
  comment: `${config.strategyName} Buy Signal`,
}, null, 2)}

// For SELL alerts:
${JSON.stringify({
  webhook_key: 'YOUR_WEBHOOK_KEY',
  action: 'sell',
  symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
  quantity: parseFloat(config.defaultQuantity) || 0.01,
  ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
  strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
  comment: `${config.strategyName} Sell Signal`,
}, null, 2)}

// For CLOSE alerts:
${JSON.stringify({
  webhook_key: 'YOUR_WEBHOOK_KEY',
  action: 'close',
  symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
  ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
  strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
  comment: `${config.strategyName} Close Position`,
}, null, 2)}`;
  }

  // Modify code to add alert functions if needed
  if (isIndicator && !hasAlertCondition) {
    // Find entry/exit conditions in the code
    const longConditionMatch = code.match(/(\w+)\s*=.*?(crossover|crossunder|>|<).*?(long|buy|entry)/i) ||
                               code.match(/(longCondition|buyCondition|entryLong)\s*=/i);
    const shortConditionMatch = code.match(/(\w+)\s*=.*?(crossover|crossunder|>|<).*?(short|sell|entry)/i) ||
                                code.match(/(shortCondition|sellCondition|entryShort)\s*=/i);

    // Add alert conditions
    const alertCode = `
// ============ TradeFlow Alert Integration ============
// Add these alert conditions to enable webhook signals

// Long/Buy Alert
alertcondition(${longConditionMatch ? longConditionMatch[1] : 'longCondition'},
    title="${config.strategyName} - Buy Signal",
    message='{"webhook_key":"YOUR_WEBHOOK_KEY","action":"buy","symbol":"{{ticker}}","quantity":${config.defaultQuantity}${config.includeTimestamp ? ',"timestamp":"{{timenow}}"' : ''},"strategy_id":"${config.strategyName.toLowerCase().replace(/\s+/g, '_')}","comment":"${config.strategyName} Buy"}')

// Short/Sell Alert
alertcondition(${shortConditionMatch ? shortConditionMatch[1] : 'shortCondition'},
    title="${config.strategyName} - Sell Signal",
    message='{"webhook_key":"YOUR_WEBHOOK_KEY","action":"sell","symbol":"{{ticker}}","quantity":${config.defaultQuantity}${config.includeTimestamp ? ',"timestamp":"{{timenow}}"' : ''},"strategy_id":"${config.strategyName.toLowerCase().replace(/\s+/g, '_')}","comment":"${config.strategyName} Sell"}')

// Close Position Alert (optional - use with exit condition)
// alertcondition(exitCondition,
//     title="${config.strategyName} - Close Position",
//     message='{"webhook_key":"YOUR_WEBHOOK_KEY","action":"close","symbol":"{{ticker}}"${config.includeTimestamp ? ',"timestamp":"{{timenow}}"' : ''},"strategy_id":"${config.strategyName.toLowerCase().replace(/\s+/g, '_')}","comment":"${config.strategyName} Close"}')

// ============ End TradeFlow Integration ============
`;

    convertedCode = code + '\n' + alertCode;
    warnings.push('Added alert conditions at the end of the script. Make sure longCondition and shortCondition variables exist.');
  } else if (isStrategy) {
    // For strategies, add the webhook URL instruction as a comment
    const webhookComment = `
// ============ TradeFlow Webhook Integration ============
// To connect this strategy to TradeFlow:
//
// 1. Add this strategy to your chart
// 2. Create an alert: Right-click chart > Add Alert
// 3. In Condition, select this strategy
// 4. Enable "Webhook URL" and enter your TradeFlow webhook URL:
//    https://app.mytradeflow.com/api/webhook/execute
//
// 5. In the Message field, use this JSON format:
//    {
//      "webhook_key": "YOUR_WEBHOOK_KEY",
//      "action": "{{strategy.order.action}}",
//      "symbol": "{{ticker}}",
//      "quantity": ${config.defaultQuantity},
//      "timestamp": "{{timenow}}",
//      "strategy_id": "${config.strategyName.toLowerCase().replace(/\s+/g, '_')}",
//      "comment": "{{strategy.order.comment}}"
//    }
//
// Replace YOUR_WEBHOOK_KEY with your actual webhook key from TradeFlow
// ============ End TradeFlow Integration ============

`;

    // Insert the comment after the version declaration
    const versionMatch = code.match(/\/\/@version=\d+\n/);
    if (versionMatch) {
      const insertPos = versionMatch.index! + versionMatch[0].length;
      convertedCode = code.slice(0, insertPos) + webhookComment + code.slice(insertPos);
    } else {
      convertedCode = webhookComment + code;
    }

    warnings.push('Strategy detected. Make sure to enable webhook alerts and use the provided JSON template.');
  }

  // Check for common issues
  if (!code.includes('strategy.') && !code.includes('alertcondition')) {
    warnings.push('No strategy entries or alert conditions found. You may need to manually add entry/exit logic.');
  }

  if (!code.includes('stop') && !code.includes('sl')) {
    warnings.push('No stop loss detected. Consider adding risk management for live trading.');
  }

  const webhookTemplate = `Webhook URL:
https://app.mytradeflow.com/api/webhook/execute

Your Webhook Key:
Get this from TradeFlow Dashboard > Settings > API Keys

Payload Format:
${JSON.stringify(webhookJson, null, 2)}`;

  const summary = isStrategy
    ? `Strategy converted! Added webhook integration comments and generated alert JSON template. Use with TradingView strategy alerts.`
    : `Indicator modified! Added ${hasAlertCondition ? 'enhanced' : 'new'} alert conditions for TradeFlow webhook integration.`;

  return {
    success: true,
    convertedCode,
    webhookTemplate,
    alertMessage,
    warnings,
    summary,
  };
}
