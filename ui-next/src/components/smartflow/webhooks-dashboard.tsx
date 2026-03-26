'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { Copy, RefreshCw, Trash2, Plus, CheckCircle, XCircle, Link as LinkIcon } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

interface WebhookConfig {
  id: number;
  name: string;
  webhook_key: string;
  source: string;
  routing_strategy: string;
  default_account_id?: number;
  specific_account_ids?: number[];
  is_active: boolean;
  total_signals: number;
  successful_signals: number;
  failed_signals: number;
  last_signal_at?: string;
  created_at: string;
}

interface TradingAccount {
  id: number;
  account_name: string;
  broker: string;
}

export function WebhooksDashboard() {
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>([]);
  const [accounts, setAccounts] = useState<TradingAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const { toast } = useToast();

  // Form state for creating new webhook
  const [newWebhook, setNewWebhook] = useState({
    name: '',
    source: 'tradingview',
    routing_strategy: 'default_only',
    default_account_id: undefined as number | undefined,
    specific_account_ids: [] as number[],
    is_active: true,
  });

  useEffect(() => {
    loadWebhooks();
    loadAccounts();
  }, []);

  const loadWebhooks = async () => {
    try {
      const response = await fetch('/api/webhook-configs/', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setWebhooks(data);
      }
    } catch (error) {
      console.error('Failed to load webhooks:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAccounts = async () => {
    try {
      const response = await fetch('/api/accounts', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        // Backend returns {accounts: [...], total: N} - extract the array
        setAccounts(Array.isArray(data) ? data : (data.accounts || []));
      }
    } catch (error) {
      console.error('Failed to load accounts:', error);
    }
  };

  const createWebhook = async () => {
    try {
      const response = await fetch('/api/webhook-configs/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(newWebhook),
      });

      if (response.ok) {
        const created = await response.json();
        setWebhooks([...webhooks, created]);
        setCreateDialogOpen(false);
        setNewWebhook({
          name: '',
          source: 'tradingview',
          routing_strategy: 'default_only',
          default_account_id: undefined,
          specific_account_ids: [],
          is_active: true,
        });
        toast({
          title: 'Webhook created',
          description: 'New webhook configuration has been created successfully.',
        });
      } else {
        toast({
          title: 'Creation failed',
          description: 'Failed to create webhook. Please try again.',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Failed to create webhook:', error);
      toast({
        title: 'Error',
        description: 'An error occurred while creating webhook.',
        variant: 'destructive',
      });
    }
  };

  const copyWebhookUrl = (webhookKey: string) => {
    const baseUrl = window.location.origin;
    const url = `${baseUrl}/api/v1/webhooks/signal/${webhookKey}`;
    navigator.clipboard.writeText(url);
    toast({
      title: 'Copied',
      description: 'Webhook URL copied to clipboard.',
    });
  };

  const regenerateKey = async (webhookId: number) => {
    try {
      const response = await fetch(`/api/webhook-configs/${webhookId}/generate-key`, {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        const updated = await response.json();
        setWebhooks(webhooks.map(w => w.id === webhookId ? updated : w));
        toast({
          title: 'Key regenerated',
          description: 'Webhook key has been regenerated. Update your external services with the new URL.',
        });
      }
    } catch (error) {
      console.error('Failed to regenerate key:', error);
      toast({
        title: 'Error',
        description: 'Failed to regenerate webhook key.',
        variant: 'destructive',
      });
    }
  };

  const toggleActive = async (webhookId: number, currentStatus: boolean) => {
    try {
      const response = await fetch(`/api/webhook-configs/${webhookId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      if (response.ok) {
        const updated = await response.json();
        setWebhooks(webhooks.map(w => w.id === webhookId ? updated : w));
        toast({
          title: 'Status updated',
          description: `Webhook ${!currentStatus ? 'activated' : 'deactivated'}.`,
        });
      }
    } catch (error) {
      console.error('Failed to toggle webhook:', error);
      toast({
        title: 'Error',
        description: 'Failed to update webhook status.',
        variant: 'destructive',
      });
    }
  };

  const deleteWebhook = async (webhookId: number) => {
    if (!confirm('Are you sure you want to delete this webhook? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`/api/webhook-configs/${webhookId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (response.ok) {
        setWebhooks(webhooks.filter(w => w.id !== webhookId));
        toast({
          title: 'Webhook deleted',
          description: 'Webhook configuration has been deleted.',
        });
      }
    } catch (error) {
      console.error('Failed to delete webhook:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete webhook.',
        variant: 'destructive',
      });
    }
  };

  const getAccountNames = (accountIds: number[] | undefined) => {
    if (!accountIds || accountIds.length === 0) return 'None';
    const names = accountIds.map(id => {
      const account = accounts.find(a => a.id === id);
      return account ? `#${id}` : `#${id}`;
    });
    return names.join(', ');
  };

  const getSuccessRate = (webhook: WebhookConfig) => {
    if (webhook.total_signals === 0) return '0%';
    return ((webhook.successful_signals / webhook.total_signals) * 100).toFixed(1) + '%';
  };

  const formatLastSignal = (timestamp: string | undefined) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">Loading webhooks...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Webhook Configurations</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Configure webhooks to receive signals from TradingView, TrailHacker, or custom sources
          </p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Webhook
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Webhook</DialogTitle>
              <DialogDescription>
                Create a new webhook configuration to receive trading signals
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="My TradingView Strategy"
                  value={newWebhook.name}
                  onChange={(e) => setNewWebhook({ ...newWebhook, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="source">Source</Label>
                <Select
                  value={newWebhook.source}
                  onValueChange={(value) => setNewWebhook({ ...newWebhook, source: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tradingview">TradingView</SelectItem>
                    <SelectItem value="trailhacker">TrailHacker</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="routing">Routing Strategy</Label>
                <Select
                  value={newWebhook.routing_strategy}
                  onValueChange={(value) => setNewWebhook({ ...newWebhook, routing_strategy: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default_only">Default Account Only</SelectItem>
                    <SelectItem value="specific_accounts">Specific Accounts</SelectItem>
                    <SelectItem value="all_accounts">All Accounts</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {newWebhook.routing_strategy === 'default_only' && (
                <div className="space-y-2">
                  <Label htmlFor="default_account">Default Account</Label>
                  <Select
                    value={newWebhook.default_account_id?.toString()}
                    onValueChange={(value) => setNewWebhook({ ...newWebhook, default_account_id: parseInt(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select account" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map(account => (
                        <SelectItem key={account.id} value={account.id.toString()}>
                          {account.account_name} ({account.broker})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={createWebhook} disabled={!newWebhook.name}>
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {webhooks.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <LinkIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No webhooks configured</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create your first webhook to start receiving trading signals
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Webhook
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {webhooks.map((webhook) => (
            <Card key={webhook.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <CardTitle>{webhook.name}</CardTitle>
                      <Badge variant={webhook.is_active ? 'default' : 'secondary'}>
                        {webhook.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                      <Badge variant="outline">{webhook.source}</Badge>
                    </div>
                    <CardDescription>
                      Strategy: {webhook.routing_strategy.replace(/_/g, ' ')}
                      {webhook.default_account_id && ` • Account: #${webhook.default_account_id}`}
                      {webhook.specific_account_ids && webhook.specific_account_ids.length > 0 &&
                        ` • Accounts: ${getAccountNames(webhook.specific_account_ids)}`}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={webhook.is_active}
                      onCheckedChange={() => toggleActive(webhook.id, webhook.is_active)}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deleteWebhook(webhook.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Webhook URL */}
                <div className="space-y-2">
                  <Label className="text-xs font-semibold">Webhook URL</Label>
                  <div className="flex gap-2">
                    <Input
                      value={`${window.location.origin}/api/v1/webhooks/signal/${webhook.webhook_key}`}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => copyWebhookUrl(webhook.webhook_key)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => regenerateKey(webhook.id)}
                      title="Regenerate Key"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* Statistics */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Signals</p>
                    <p className="text-2xl font-bold">{webhook.total_signals}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Success</p>
                    <div className="flex items-center gap-1">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <p className="text-2xl font-bold">{webhook.successful_signals}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Failed</p>
                    <div className="flex items-center gap-1">
                      <XCircle className="h-4 w-4 text-red-500" />
                      <p className="text-2xl font-bold">{webhook.failed_signals}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Success Rate</p>
                    <p className="text-2xl font-bold">{getSuccessRate(webhook)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Last Signal</p>
                    <p className="text-sm font-semibold">{formatLastSignal(webhook.last_signal_at)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
