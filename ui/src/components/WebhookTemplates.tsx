import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Copy, Check, Play, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { useBroker, BrokerType, getBrokerDisplayName } from '../contexts/BrokerContext';
import { ApiKeyDisplay } from './ApiKeyDisplay';

interface WebhookTemplatesProps {
  broker: BrokerType;
}

export function WebhookTemplates({ broker }: WebhookTemplatesProps) {
  const { connectedBrokers } = useBroker();
  const [copiedItem, setCopiedItem] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  
  // Filter accounts for current broker
  const brokerAccounts = connectedBrokers.filter(acc => acc.broker === broker);
  
  // Selected account state
  const [selectedAccountId, setSelectedAccountId] = useState<string>(
    brokerAccounts[0]?.accountId || ''
  );

  const selectedAccount = brokerAccounts.find(acc => acc.accountId === selectedAccountId);
  
  // Generate API key for selected account (in production, this comes from backend)
  const userApiKey = selectedAccount 
    ? `${broker}_${selectedAccount.accountId.slice(0, 8)}_${Math.random().toString(36).substring(2, 15)}`
    : '';
  
  // Backend webhook endpoint - this is your unified.fluxeo.net endpoint
  const webhookUrl = `https://unified.fluxeo.net/api/unify/v1/webhook/${broker}`;
  const authHeader = `Bearer ${userApiKey}`;

  const handleCopy = (text: string, item: string) => {
    navigator.clipboard.writeText(text);
    setCopiedItem(item);
    setTimeout(() => setCopiedItem(null), 2000);
  };

  const handleTest = (template: any) => {
    // Mock test - in real app, send to backend
    setTestResult({
      success: true,
      message: `Template validated: ${template.type} order for ${template.symbol || 'SYMBOL'}`
    });
    setTimeout(() => setTestResult(null), 5000);
  };

  const brokerSymbolHints = {
    tradelocker: 'Use standard symbols (e.g., EURUSD, GBPUSD, US30)',
    topstep: 'Use contract codes (e.g., ESH5, NQH5, MESU5) - check Topstep dashboard for exact codes',
    truforex: 'MT4/5 symbols (e.g., EURUSD, XAUUSD) - may have broker suffix like .a or .pro'
  };

  const templates = {
    marketBuy: {
      type: 'Market Buy',
      description: 'Open a market buy position',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          side: 'buy',
          type: 'market',
          symbol: '{{ticker}}',
          qty_mode: 'risk_pct',
          qty: 1.0,
          sl: { mode: 'price', value: '{{strategy.position_avg_price}} * 0.98' },
          tp: { mode: 'rr', value: 2.0 },
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    marketSell: {
      type: 'Market Sell',
      description: 'Open a market sell position',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          side: 'sell',
          type: 'market',
          symbol: '{{ticker}}',
          qty_mode: 'risk_pct',
          qty: 1.0,
          sl: { mode: 'price', value: '{{strategy.position_avg_price}} * 1.02' },
          tp: { mode: 'rr', value: 2.0 },
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    limitEntry: {
      type: 'Limit Entry',
      description: 'Place a limit entry order',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          side: '{{strategy.order.action}}',
          type: 'limit',
          symbol: '{{ticker}}',
          price: '{{close}}',
          qty_mode: 'fixed_qty',
          qty: 1,
          sl: { mode: 'offset', value: 0.005 },
          tp: { mode: 'price', value: '{{close}} * 1.01' },
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    stopEntry: {
      type: 'Stop Entry',
      description: 'Place a stop entry order',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          side: '{{strategy.order.action}}',
          type: 'stop',
          symbol: '{{ticker}}',
          price: '{{high}}',
          qty_mode: 'risk_usd',
          qty: 100,
          sl: { mode: 'atr', value: 1.5 },
          tp: { mode: 'rr', value: 3.0 },
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    trailingStop: {
      type: 'Trailing Stop',
      description: 'Add trailing stop to position',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          action: 'modify',
          symbol: '{{ticker}}',
          trail: { mode: 'offset', value: 0.002 },
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    partialClose: {
      type: 'Partial Close',
      description: 'Close percentage of position',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          action: 'close_partial',
          symbol: '{{ticker}}',
          close_pct: 50,
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    closeAll: {
      type: 'Close All Positions',
      description: 'Close all positions for symbol',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          action: 'close_all',
          symbol: '{{ticker}}',
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    slOnly: {
      type: 'Set Stop Loss',
      description: 'Update stop loss only',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          action: 'modify',
          symbol: '{{ticker}}',
          sl: { mode: 'price', value: '{{low}}' },
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    },
    tpOnly: {
      type: 'Set Take Profit',
      description: 'Update take profit only',
      json: {
        version: 'unify.v1',
        source: 'tradingview',
        intent: {
          broker,
          action: 'modify',
          symbol: '{{ticker}}',
          tp: { mode: 'price', value: '{{high}}' },
          tag: '{{strategy.order.comment}}'
        },
        user_context: {
          account: selectedAccount?.accountName || 'default',
          workspace: '{{alert_name}}'
        },
        ts: '{{time}}'
      }
    }
  };

  if (brokerAccounts.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-white mb-1">TradingView Webhook Templates</h2>
          <p className="text-sm text-gray-400">Connect a {getBrokerDisplayName(broker)} account first</p>
        </div>
        <Alert className="bg-yellow-950 border-yellow-800">
          <AlertCircle className="w-4 h-4 text-yellow-400" />
          <AlertDescription className="text-yellow-200">
            No {getBrokerDisplayName(broker)} accounts connected. Please connect an account first to generate webhook templates and API keys.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-white mb-1">TradingView Webhook Templates</h2>
        <p className="text-sm text-gray-400">Copy-paste ready alert configurations for {getBrokerDisplayName(broker)}</p>
      </div>

      {/* Account Selector */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Select Account</CardTitle>
          <CardDescription className="text-gray-400">
            Choose which {getBrokerDisplayName(broker)} account to configure webhooks for
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
            <SelectTrigger className="w-full bg-[#002b36] border-gray-700 text-white">
              <SelectValue placeholder="Select an account" />
            </SelectTrigger>
            <SelectContent>
              {brokerAccounts.map((account) => (
                <SelectItem key={account.accountId} value={account.accountId}>
                  {account.accountName} ({account.accountId})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* API Key & Connection Details */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Connection Details</CardTitle>
          <CardDescription className="text-gray-400">
            Use these credentials in your TradingView alert webhook
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Alert className="bg-blue-950 border-blue-800">
            <AlertCircle className="w-4 h-4 text-blue-400" />
            <AlertDescription className="text-blue-200 text-sm">
              Your API Key was automatically generated when you connected "{selectedAccount?.accountName}". 
              This ensures your trades are routed to the correct {getBrokerDisplayName(broker)} account.
            </AlertDescription>
          </Alert>

          {/* API Key Display */}
          {selectedAccount && (
            <ApiKeyDisplay
              apiKey={userApiKey}
              accountId={selectedAccount.accountId}
              accountName={selectedAccount.accountName}
              broker={getBrokerDisplayName(broker)}
              showLabel={true}
              compact={false}
            />
          )}

          {/* Webhook URL */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-white">Webhook URL</label>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleCopy(webhookUrl, 'url')}
                className="text-[#00ffc2] hover:text-[#00ffc2]"
              >
                {copiedItem === 'url' ? (
                  <>
                    <Check className="w-4 h-4 mr-1" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-1" />
                    Copy
                  </>
                )}
              </Button>
            </div>
            <div className="p-3 bg-[#002b36] rounded-lg border border-gray-700">
              <code className="text-sm text-white break-all">{webhookUrl}</code>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Paste this URL in TradingView Alert → Notifications → Webhook URL
            </p>
          </div>

          {/* Authorization Header */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-white">Authorization Header</label>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleCopy(authHeader, 'auth')}
                className="text-[#00ffc2] hover:text-[#00ffc2]"
              >
                {copiedItem === 'auth' ? (
                  <>
                    <Check className="w-4 h-4 mr-1" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-1" />
                    Copy
                  </>
                )}
              </Button>
            </div>
            <div className="p-3 bg-[#002b36] rounded-lg border border-gray-700">
              <code className="text-sm text-white break-all">{authHeader}</code>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Include this in the webhook request headers (most TradingView setups auto-include it from the JSON payload)
            </p>
          </div>

          <Alert className="bg-blue-950 border-blue-800">
            <AlertCircle className="w-4 h-4 text-blue-400" />
            <AlertDescription className="text-blue-200 text-sm">
              {brokerSymbolHints[broker as keyof typeof brokerSymbolHints]}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Test Result */}
      {testResult && (
        <Alert className={testResult.success ? 'bg-green-950 border-green-800' : 'bg-red-950 border-red-800'}>
          <AlertCircle className={`w-4 h-4 ${testResult.success ? 'text-green-400' : 'text-red-400'}`} />
          <AlertDescription className={testResult.success ? 'text-green-200' : 'text-red-200'}>
            {testResult.message}
          </AlertDescription>
        </Alert>
      )}

      {/* Template Library */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Alert Templates</CardTitle>
          <CardDescription className="text-gray-400">
            Copy the JSON payload and paste into TradingView alert message
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="entries" className="w-full">
            <TabsList className="bg-[#002b36] border border-gray-800">
              <TabsTrigger value="entries">Entries</TabsTrigger>
              <TabsTrigger value="exits">Exits</TabsTrigger>
              <TabsTrigger value="modifications">Modifications</TabsTrigger>
            </TabsList>

            <TabsContent value="entries" className="space-y-4 mt-4">
              {Object.entries(templates)
                .filter(([key]) => ['marketBuy', 'marketSell', 'limitEntry', 'stopEntry'].includes(key))
                .map(([key, template]) => (
                  <TemplateCard
                    key={key}
                    template={template}
                    copiedItem={copiedItem}
                    onCopy={(text) => handleCopy(text, key)}
                    onTest={() => handleTest(template)}
                  />
                ))}
            </TabsContent>

            <TabsContent value="exits" className="space-y-4 mt-4">
              {Object.entries(templates)
                .filter(([key]) => ['partialClose', 'closeAll'].includes(key))
                .map(([key, template]) => (
                  <TemplateCard
                    key={key}
                    template={template}
                    copiedItem={copiedItem}
                    onCopy={(text) => handleCopy(text, key)}
                    onTest={() => handleTest(template)}
                  />
                ))}
            </TabsContent>

            <TabsContent value="modifications" className="space-y-4 mt-4">
              {Object.entries(templates)
                .filter(([key]) => ['slOnly', 'tpOnly', 'trailingStop'].includes(key))
                .map(([key, template]) => (
                  <TemplateCard
                    key={key}
                    template={template}
                    copiedItem={copiedItem}
                    onCopy={(text) => handleCopy(text, key)}
                    onTest={() => handleTest(template)}
                  />
                ))}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* How to Use Guide */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">How to Use in TradingView</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="p-3 bg-[#002b36] rounded-lg border-l-4 border-[#00ffc2]">
            <p className="text-sm text-white mb-2">Step 1: Copy Your API Key</p>
            <p className="text-xs text-gray-400">
              Your API key is shown above. It was automatically generated when you connected "{selectedAccount?.accountName}".
            </p>
          </div>
          
          <div className="p-3 bg-[#002b36] rounded-lg border-l-4 border-blue-400">
            <p className="text-sm text-white mb-2">Step 2: Create TradingView Alert</p>
            <p className="text-xs text-gray-400">
              In TradingView: Chart → Alert → Set conditions → Notifications tab → Webhook URL (paste webhook URL from above)
            </p>
          </div>
          
          <div className="p-3 bg-[#002b36] rounded-lg border-l-4 border-purple-400">
            <p className="text-sm text-white mb-2">Step 3: Copy Alert Template</p>
            <p className="text-xs text-gray-400">
              Choose a template below, click "Copy", and paste the JSON into the TradingView alert message field.
            </p>
          </div>
          
          <div className="p-3 bg-[#002b36] rounded-lg border-l-4 border-yellow-400">
            <p className="text-sm text-white mb-2">Step 4: Test Your Alert</p>
            <p className="text-xs text-gray-400">
              Use the "Test" button to validate your template before going live. Check the Events tab to see webhook logs.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Position Sizing Guide */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Position Sizing Modes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="p-3 bg-[#002b36] rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="border-[#00ffc2] text-[#00ffc2]">fixed_qty</Badge>
              <span className="text-sm text-white">Fixed Quantity</span>
            </div>
            <p className="text-xs text-gray-400">Exact number of units/lots/contracts (e.g., qty: 2)</p>
          </div>

          <div className="p-3 bg-[#002b36] rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="border-[#00ffc2] text-[#00ffc2]">risk_usd</Badge>
              <span className="text-sm text-white">Risk in Dollars</span>
            </div>
            <p className="text-xs text-gray-400">Qty = risk_usd / |entry - SL| (e.g., qty: 100 risks $100)</p>
          </div>

          <div className="p-3 bg-[#002b36] rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="border-[#00ffc2] text-[#00ffc2]">risk_pct</Badge>
              <span className="text-sm text-white">Risk Percentage</span>
            </div>
            <p className="text-xs text-gray-400">Qty = (equity * pct) / |entry - SL| (e.g., qty: 1.0 = 1% risk)</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TemplateCard({ template, copiedItem, onCopy, onTest }: any) {
  const jsonString = JSON.stringify(template.json, null, 2);
  const isCopied = copiedItem === jsonString;

  return (
    <div className="p-4 bg-[#002b36] rounded-lg border border-gray-800">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-white mb-1">{template.type}</h4>
          <p className="text-sm text-gray-400">{template.description}</p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onTest()}
            className="text-blue-400 hover:text-blue-300"
          >
            <Play className="w-4 h-4 mr-1" />
            Test
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onCopy(jsonString)}
            className="text-[#00ffc2] hover:text-[#00ffc2]"
          >
            {isCopied ? (
              <>
                <Check className="w-4 h-4 mr-1" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 mr-1" />
                Copy
              </>
            )}
          </Button>
        </div>
      </div>
      <div className="p-3 bg-[#001f29] rounded border border-gray-800 overflow-x-auto">
        <pre className="text-xs text-gray-300">
          <code>{jsonString}</code>
        </pre>
      </div>
    </div>
  );
}
