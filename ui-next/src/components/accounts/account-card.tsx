'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  XCircle,
  RefreshCw,
  Edit,
  Trash2,
  Loader2,
  Settings,
  Zap,
  ZapOff,
  Copy,
} from 'lucide-react';
import {
  Account,
  BROKER_DISPLAY_NAMES,
  ACCOUNT_TYPE_DISPLAY_NAMES,
} from '@/types/account';
import { cn } from '@/lib/utils';
import { syncAccount, reconnectMetaApiAccount } from '@/lib/api/accounts';
import { useToast } from '@/hooks/use-toast';
import { parseAccountError, formatErrorForToast } from '@/lib/errors/account-errors';
import { useUser } from '@/providers/user-provider';

// Extended account with optional settings info
interface AccountWithSettings extends Account {
  groupId?: number | null;
  groupName?: string | null;
  groupColor?: string | null;
  isSignalEnabled?: boolean;
  signalPriority?: number;
  webhookKey?: string | null;  // Patch 1.2.1
}

interface AccountCardProps {
  account: AccountWithSettings;
  onEdit: (account: Account) => void;
  onDelete: (account: Account) => void;
  onSyncComplete?: (account: Account) => void;
  onSyncRefresh?: () => void;
}

export function AccountCard({
  account,
  onEdit,
  onDelete,
  onSyncComplete,
  onSyncRefresh,
}: AccountCardProps) {
  const [syncing, setSyncing] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const { toast } = useToast();
  const { user } = useUser();  // Patch 1.2.1 - get user_id for webhook URL

  // Check if this is a MetaApi account (MT4/MT5)
  const isMetaApiAccount = account.broker === 'mt4' || account.broker === 'mt5';

  // Handle MetaApi reconnect for MT4/MT5
  const handleReconnect = async () => {
    if (!isMetaApiAccount) return;

    setReconnecting(true);
    try {
      const result = await reconnectMetaApiAccount(account.id);
      toast({
        title: 'Reconnecting',
        description: result.message || 'MetaApi account reconnection initiated.',
      });
      onSyncRefresh?.();
    } catch (error) {
      console.error('Failed to reconnect MetaApi account:', error);
      const errorMsg = error instanceof Error ? error.message : 'Reconnection failed';
      toast({
        title: 'Reconnect Failed',
        description: errorMsg,
        variant: 'destructive',
      });
    } finally {
      setReconnecting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const updatedAccount = await syncAccount(account.id);
      onSyncComplete?.(updatedAccount);
      onSyncRefresh?.();
      toast({
        title: 'Sync Complete',
        description: 'Account data has been updated from the broker.',
      });
    } catch (error) {
      console.error('Failed to sync account:', error);
      const userError = parseAccountError(error, 'sync');
      toast(formatErrorForToast(userError));
    } finally {
      setSyncing(false);
    }
  };

  // Format currency values
  const formatCurrency = (value: number | undefined, currency: string) => {
    if (value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  // Format last sync time
  const formatLastSync = (timestamp: string | undefined) => {
    if (!timestamp) return 'Never synced';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  // Mask account ID (show first 4 and last 4 chars)
  const maskAccountId = (id: string) => {
    if (id.length <= 8) return id;
    return `${id.slice(0, 4)}...${id.slice(-4)}`;
  };

  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">
              {BROKER_DISPLAY_NAMES[account.broker]}
            </CardTitle>
            <p className="text-sm text-muted-foreground font-mono">
              {maskAccountId(account.account_id)}
            </p>
          </div>
          <div className="flex gap-2">
            {account.is_connected ? (
              <CheckCircle2 className="h-5 w-5 text-chart-2" />
            ) : (
              <XCircle className="h-5 w-5 text-destructive" />
            )}
          </div>
        </div>

        {/* Badges */}
        <div className="flex gap-2 pt-2 flex-wrap">
          <Badge variant="outline">
            {ACCOUNT_TYPE_DISPLAY_NAMES[account.account_type]}
          </Badge>
          <Badge
            variant={account.is_active ? 'default' : 'secondary'}
            className={cn(
              !account.is_active && 'bg-muted text-muted-foreground'
            )}
          >
            {account.is_active ? 'Active' : 'Inactive'}
          </Badge>
          {account.groupName && (
            <Badge
              variant="outline"
              className="gap-1"
              style={{
                borderColor: account.groupColor || undefined,
                color: account.groupColor || undefined,
              }}
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: account.groupColor || '#6366f1' }}
              />
              {account.groupName}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Balance Information */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-muted-foreground">Balance</p>
            <p className="text-sm font-semibold">
              {formatCurrency(account.balance, account.currency)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Equity</p>
            <p className="text-sm font-semibold">
              {formatCurrency(account.equity, account.currency)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Margin</p>
            <p className="text-sm font-semibold">
              {formatCurrency(account.margin, account.currency)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Free Margin</p>
            <p className="text-sm font-semibold">
              {formatCurrency(account.free_margin, account.currency)}
            </p>
          </div>
        </div>

        {/* Last Sync */}
        <div className="pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground">
            Last synced: {formatLastSync(account.last_sync)}
          </p>
        </div>

        {/* Signal Status Indicator */}
        {account.isSignalEnabled !== undefined && (
          <div className="flex items-center gap-2 text-sm">
            {account.isSignalEnabled ? (
              <>
                <Zap className="h-4 w-4 text-green-500" />
                <span>
                  Signals enabled
                  {account.signalPriority !== undefined && account.signalPriority > 0 && (
                    <span className="text-muted-foreground ml-1">
                      (priority: {account.signalPriority})
                    </span>
                  )}
                </span>
              </>
            ) : (
              <>
                <ZapOff className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Signals disabled</span>
              </>
            )}
          </div>
        )}

        {/* Webhook URL (Patch 1.2.1) */}
        {account.webhookKey && account.is_connected && (
          <div className="pt-2 border-t border-border">
            <div className="flex items-center justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted-foreground mb-1">Webhook URL</p>
                <p className="text-xs font-mono truncate" title={`${process.env.NEXT_PUBLIC_API_URL || 'https://api.tradeflow.fluxeo.net'}/api/v1/webhooks/incoming?broker=${account.broker}&user=${account.user_id || 'USER_ID'}&key=${account.webhookKey}`}>
                  .../incoming?broker={account.broker}&key=...
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.tradeflow.fluxeo.net';
                  const userId = user?.id || account.user_id || 'USER_ID';
                  const webhookUrl = `${baseUrl}/api/v1/webhooks/incoming?broker=${account.broker}&user=${userId}&key=${account.webhookKey}`;
                  navigator.clipboard.writeText(webhookUrl);
                  toast({
                    title: 'Copied!',
                    description: `Webhook URL copied. Paste this in TradingView for ${BROKER_DISPLAY_NAMES[account.broker]} only.`,
                  });
                }}
                className="shrink-0"
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Paste this only in TradingView for {BROKER_DISPLAY_NAMES[account.broker]}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          {/* Show Reconnect button for disconnected MT4/MT5 accounts */}
          {isMetaApiAccount && !account.is_connected ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleReconnect}
              disabled={reconnecting}
              className="flex-1"
            >
              {reconnecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Reconnecting...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Reconnect
                </>
              )}
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={syncing || !account.is_connected}
              className="flex-1"
            >
              {syncing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Sync
                </>
              )}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            asChild
          >
            <Link href={`/dashboard/settings/accounts/${account.id.toString()}/settings`}>
              <Settings className="h-4 w-4" />
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onEdit(account)}
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDelete(account)}
            className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
