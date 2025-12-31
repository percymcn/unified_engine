import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Key, Eye, EyeOff, Copy, RotateCcw, Trash2, Plus, Check, Activity, CheckCircle, XCircle, AlertCircle as AlertCircleIcon } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Alert, AlertDescription } from './ui/alert';
import { ScrollArea } from './ui/scroll-area';

interface ApiKeyManagerProps {
  broker: 'tradelocker' | 'topstep' | 'truforex';
}

export function ApiKeyManager({ broker }: ApiKeyManagerProps) {
  const [showNewKeyDialog, setShowNewKeyDialog] = useState(false);
  const [copiedItem, setCopiedItem] = useState<string | null>(null);
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
  const [viewEventsDialog, setViewEventsDialog] = useState<string | null>(null);

  const apiKeys = [
    {
      id: 'key_1',
      name: 'Production API Key',
      key: 'sk_live_abc123xyz789...',
      created: '2025-10-01',
      lastUsed: '2025-10-14 14:30',
      permissions: ['orders:write', 'positions:read', 'account:read'],
      enabled: true
    },
    {
      id: 'key_2',
      name: 'Staging API Key',
      key: 'sk_test_def456uvw012...',
      created: '2025-09-15',
      lastUsed: '2025-10-13 10:15',
      permissions: ['orders:write', 'positions:read'],
      enabled: true
    },
    {
      id: 'key_3',
      name: 'Read-Only Key',
      key: 'sk_live_ghi789rst345...',
      created: '2025-08-20',
      lastUsed: '2025-10-14 08:00',
      permissions: ['positions:read', 'account:read'],
      enabled: false
    }
  ];

  const webhooks = [
    {
      id: 'wh_1',
      name: 'TradingView Webhook',
      url: 'https://api.empiretrading.io/api/unify/v1/webhook/wks_abc123xyz',
      secret: 'whsec_abc123xyz789...',
      created: '2025-10-01',
      lastEvent: '2025-10-14 14:30',
      eventsReceived: 1247,
      enabled: true
    }
  ];

  // Mock webhook events data
  const webhookEvents = [
    {
      id: 'evt_1',
      timestamp: '2025-10-14 14:30:15',
      type: 'order.created',
      status: 'success',
      symbol: 'EURUSD',
      action: 'BUY',
      qty: 1.0,
      responseTime: '45ms'
    },
    {
      id: 'evt_2',
      timestamp: '2025-10-14 14:18:32',
      type: 'position.closed',
      status: 'success',
      symbol: 'GBPUSD',
      action: 'CLOSE',
      pnl: '+$425.00',
      responseTime: '38ms'
    },
    {
      id: 'evt_3',
      timestamp: '2025-10-14 14:15:08',
      type: 'order.created',
      status: 'success',
      symbol: 'ES',
      action: 'SELL',
      qty: 2.0,
      responseTime: '52ms'
    },
    {
      id: 'evt_4',
      timestamp: '2025-10-14 14:12:45',
      type: 'order.rejected',
      status: 'error',
      symbol: 'NQ',
      action: 'BUY',
      error: 'Insufficient margin',
      responseTime: '28ms'
    },
    {
      id: 'evt_5',
      timestamp: '2025-10-14 13:58:22',
      type: 'position.modified',
      status: 'success',
      symbol: 'XAUUSD',
      action: 'UPDATE_SL',
      responseTime: '41ms'
    },
  ];

  const handleCopy = (text: string, item: string) => {
    navigator.clipboard.writeText(text);
    setCopiedItem(item);
    setTimeout(() => setCopiedItem(null), 2000);
  };

  const toggleVisibility = (keyId: string) => {
    const newVisible = new Set(visibleKeys);
    if (newVisible.has(keyId)) {
      newVisible.delete(keyId);
    } else {
      newVisible.add(keyId);
    }
    setVisibleKeys(newVisible);
  };

  const handleRotateKey = (keyId: string) => {
    console.log('Rotating key:', keyId);
  };

  const handleDeleteKey = (keyId: string) => {
    console.log('Deleting key:', keyId);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-white mb-1">API Keys & Webhooks</h2>
        <p className="text-sm text-gray-400">Manage authentication and webhook secrets for {broker}</p>
      </div>

      <Alert className="bg-yellow-950 border-yellow-800">
        <Key className="w-4 h-4 text-yellow-400" />
        <AlertDescription className="text-yellow-200">
          Keep your API keys secure. Never share them publicly or commit them to version control.
        </AlertDescription>
      </Alert>

      {/* API Keys Section */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">API Keys</CardTitle>
              <CardDescription className="text-gray-400">
                API keys for programmatic access to your account
              </CardDescription>
            </div>
            <Dialog open={showNewKeyDialog} onOpenChange={setShowNewKeyDialog}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad]">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Key
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#001f29] border-gray-800 text-white">
                <DialogHeader>
                  <DialogTitle className="text-white">Create New API Key</DialogTitle>
                  <DialogDescription className="text-gray-400">
                    Generate a new API key with specific permissions
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="keyName" className="text-gray-300">Key Name</Label>
                    <Input
                      id="keyName"
                      placeholder="My API Key"
                      className="bg-[#002b36] border-gray-700 text-white mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-300 mb-2 block">Permissions</Label>
                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" defaultChecked className="rounded" />
                        <span className="text-white">orders:write - Place and modify orders</span>
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" defaultChecked className="rounded" />
                        <span className="text-white">positions:read - View positions</span>
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" defaultChecked className="rounded" />
                        <span className="text-white">account:read - View account details</span>
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        <span className="text-white">admin:* - Full admin access</span>
                      </label>
                    </div>
                  </div>
                  <div className="flex gap-2 pt-4">
                    <Button
                      onClick={() => setShowNewKeyDialog(false)}
                      variant="outline"
                      className="flex-1 border-gray-700 text-white"
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={() => setShowNewKeyDialog(false)}
                      className="flex-1 bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad]"
                    >
                      Create Key
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {apiKeys.map((apiKey) => (
            <div key={apiKey.id} className="p-4 bg-[#002b36] rounded-lg border border-gray-800">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-white">{apiKey.name}</h4>
                    <Badge
                      variant="outline"
                      className={
                        apiKey.enabled
                          ? 'border-[#00ffc2] text-[#00ffc2]'
                          : 'border-gray-500 text-gray-500'
                      }
                    >
                      {apiKey.enabled ? 'Active' : 'Disabled'}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-400">
                    Created: {apiKey.created} • Last used: {apiKey.lastUsed}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRotateKey(apiKey.id)}
                    className="text-blue-400 hover:text-blue-300"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDeleteKey(apiKey.id)}
                    className="text-red-400 hover:text-red-300"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div className="flex items-center gap-2 mb-3">
                <div className="flex-1 p-2 bg-[#001f29] rounded border border-gray-800 font-mono text-sm">
                  <code className="text-white">
                    {visibleKeys.has(apiKey.id) ? apiKey.key : '••••••••••••••••'}
                  </code>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleVisibility(apiKey.id)}
                  className="text-gray-400 hover:text-white"
                >
                  {visibleKeys.has(apiKey.id) ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleCopy(apiKey.key, apiKey.id)}
                  className="text-[#00ffc2] hover:text-[#00ffc2]"
                >
                  {copiedItem === apiKey.id ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>

              <div className="flex flex-wrap gap-2">
                {apiKey.permissions.map((perm) => (
                  <Badge key={perm} variant="secondary" className="bg-[#001f29] text-gray-300 text-xs">
                    {perm}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Webhooks Section */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">Webhook Endpoints</CardTitle>
              <CardDescription className="text-gray-400">
                Receive alerts from TradingView and other services
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="p-4 bg-[#002b36] rounded-lg border border-gray-800">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-white">{webhook.name}</h4>
                    <Badge
                      variant="outline"
                      className="border-[#00ffc2] text-[#00ffc2]"
                    >
                      Active
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-400">
                    Created: {webhook.created} • Last event: {webhook.lastEvent}
                  </p>
                  <p className="text-xs text-gray-400">
                    Events received: {webhook.eventsReceived.toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Label className="text-gray-400 text-xs">Webhook URL</Label>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCopy(webhook.url, `${webhook.id}_url`)}
                      className="text-[#00ffc2] hover:text-[#00ffc2] h-6"
                    >
                      {copiedItem === `${webhook.id}_url` ? (
                        <>
                          <Check className="w-3 h-3 mr-1" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 mr-1" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="p-2 bg-[#001f29] rounded border border-gray-800 font-mono text-xs overflow-x-auto">
                    <code className="text-white">{webhook.url}</code>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Label className="text-gray-400 text-xs">Signing Secret (HMAC SHA-256)</Label>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCopy(webhook.secret, `${webhook.id}_secret`)}
                      className="text-[#00ffc2] hover:text-[#00ffc2] h-6"
                    >
                      {copiedItem === `${webhook.id}_secret` ? (
                        <>
                          <Check className="w-3 h-3 mr-1" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 mr-1" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="p-2 bg-[#001f29] rounded border border-gray-800 font-mono text-xs">
                    <code className="text-white">
                      {visibleKeys.has(`${webhook.id}_secret`)
                        ? webhook.secret
                        : '••••••••••••••••'}
                    </code>
                  </div>
                </div>
              </div>

              <div className="flex gap-2 mt-3">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setViewEventsDialog(webhook.id)}
                  className="flex-1 border-gray-700 text-white hover:bg-[#002b36]"
                >
                  <Activity className="w-4 h-4 mr-1" />
                  View Events
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleRotateKey(webhook.id)}
                  className="border-gray-700 text-blue-400 hover:bg-[#002b36]"
                >
                  <RotateCcw className="w-4 h-4 mr-1" />
                  Rotate Secret
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Security Best Practices */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Security Best Practices</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-start gap-2">
            <div className="w-1 h-1 rounded-full bg-[#00ffc2] mt-2" />
            <p className="text-sm text-gray-300">
              Rotate your API keys regularly (every 90 days recommended)
            </p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1 h-1 rounded-full bg-[#00ffc2] mt-2" />
            <p className="text-sm text-gray-300">
              Use read-only keys when write access is not required
            </p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1 h-1 rounded-full bg-[#00ffc2] mt-2" />
            <p className="text-sm text-gray-300">
              Enable HMAC signature verification for webhooks to prevent spoofing
            </p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1 h-1 rounded-full bg-[#00ffc2] mt-2" />
            <p className="text-sm text-gray-300">
              Monitor your API key usage and deactivate unused keys
            </p>
          </div>
        </CardContent>
      </Card>

      {/* View Events Dialog */}
      <Dialog open={viewEventsDialog !== null} onOpenChange={(open) => !open && setViewEventsDialog(null)}>
        <DialogContent className="sm:max-w-[700px] bg-[#001f29] border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-[#0EA5E9]" />
              Webhook Events
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              Recent webhook events received from TradingView and other services
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="h-[500px] pr-4">
            <div className="space-y-3">
              {webhookEvents.map((event) => (
                <div
                  key={event.id}
                  className="p-4 bg-[#002b36] border border-gray-800 rounded-lg hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {event.status === 'success' ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-400" />
                      )}
                      <div>
                        <p className="text-white font-medium">{event.type}</p>
                        <p className="text-xs text-gray-400">{event.timestamp}</p>
                      </div>
                    </div>
                    <Badge 
                      variant="outline"
                      className={
                        event.status === 'success'
                          ? 'border-green-500 text-green-400'
                          : 'border-red-500 text-red-400'
                      }
                    >
                      {event.status}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-400">Symbol:</span>
                      <span className="ml-2 text-white">{event.symbol}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Action:</span>
                      <span className="ml-2 text-white">{event.action}</span>
                    </div>
                    {event.qty && (
                      <div>
                        <span className="text-gray-400">Quantity:</span>
                        <span className="ml-2 text-white">{event.qty}</span>
                      </div>
                    )}
                    {event.pnl && (
                      <div>
                        <span className="text-gray-400">P&L:</span>
                        <span className={`ml-2 ${event.pnl.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
                          {event.pnl}
                        </span>
                      </div>
                    )}
                    {event.error && (
                      <div className="col-span-2">
                        <span className="text-gray-400">Error:</span>
                        <span className="ml-2 text-red-400">{event.error}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-gray-400">Response Time:</span>
                      <span className="ml-2 text-[#0EA5E9]">{event.responseTime}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <div className="flex justify-between items-center pt-4 border-t border-gray-800">
            <p className="text-sm text-gray-400">
              Showing {webhookEvents.length} recent events
            </p>
            <Button 
              onClick={() => setViewEventsDialog(null)}
              className="bg-[#0EA5E9] text-white hover:bg-[#0284c7]"
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
