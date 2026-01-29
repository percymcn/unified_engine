'use client';

import { useEffect, useState, useCallback } from 'react';
import { History, RefreshCw, CheckCircle2, XCircle, AlertCircle, Clock, Lock, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { formatDistanceToNow } from 'date-fns';
import { useUser } from '@/providers/user-provider';
import { hasFeatureAccess, FEATURES, SubscriptionTier } from '@/lib/feature-flags';
import Link from 'next/link';

interface WebhookExecution {
  account_id: number;
  broker: string;
  status: string;
  error?: string;
}

interface WebhookLog {
  id: number;
  webhook_id: string;
  source: string;
  source_ip?: string;
  user_agent?: string;
  payload?: string;
  created_at: string;
  processed: boolean;
  processing_time_ms?: number;
  response_status?: number;
  error_message?: string;
  // Enriched fields from API
  action?: string;
  symbol?: string;
  quantity?: number;
  total_accounts?: number;
  successful_accounts?: number;
  failed_accounts?: number;
  executions?: WebhookExecution[];
}

export default function WebhookLogsPage() {
  const { user } = useUser();
  const userTier = (user?.subscription_tier || 'free') as SubscriptionTier;
  const hasAccess = hasFeatureAccess(userTier, 'WEBHOOK_LOGS');

  const [logs, setLogs] = useState<WebhookLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchLogs = useCallback(async () => {
    if (!hasAccess) {
      setLoading(false);
      return;
    }
    try {
      setError(null);
      const response = await fetch('/api/webhooks/logs', { credentials: 'include' });
      if (!response.ok) {
        throw new Error('Failed to fetch webhook logs');
      }
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      console.error('Failed to load webhook logs:', err);
      setError('Unable to load webhook logs. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchLogs, 30000);
    return () => clearInterval(interval);
  }, [fetchLogs]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchLogs();
  };

  const getStatusBadge = (log: WebhookLog) => {
    if (log.processed && log.successful_accounts === log.total_accounts) {
      return (
        <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
          <CheckCircle2 className="h-3 w-3 mr-1" />
          Success
        </Badge>
      );
    }
    if (log.processed && log.successful_accounts && log.successful_accounts > 0) {
      return (
        <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20">
          <AlertCircle className="h-3 w-3 mr-1" />
          Partial
        </Badge>
      );
    }
    if (!log.processed || (log.failed_accounts && log.failed_accounts > 0)) {
      return (
        <Badge variant="destructive">
          <XCircle className="h-3 w-3 mr-1" />
          Failed
        </Badge>
      );
    }
    return (
      <Badge variant="secondary">
        <Clock className="h-3 w-3 mr-1" />
        Unknown
      </Badge>
    );
  };

  // Show upgrade prompt for users without Pro tier
  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Webhook Logs</h1>
          <p className="text-muted-foreground mt-2">
            View execution history and debug webhook signals
          </p>
        </div>

        <Card className="p-8 text-center space-y-4">
          <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Lock className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-xl font-semibold">Pro Feature</h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            {FEATURES.WEBHOOK_LOGS.description}. Upgrade to Pro or higher to view webhook execution history.
          </p>
          <div className="flex gap-3 justify-center">
            <Link href="/dashboard/settings/billing">
              <Button>
                <Sparkles className="h-4 w-4 mr-2" />
                Upgrade to Pro
              </Button>
            </Link>
          </div>
          <p className="text-xs text-muted-foreground">
            Current plan: <span className="font-medium capitalize">{userTier}</span>
          </p>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6 max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-72" />
          </div>
        </div>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <History className="h-6 w-6" />
            Webhook Logs
          </h1>
          <p className="text-muted-foreground">
            View history of all incoming webhooks and their execution status
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing} variant="outline">
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="mb-6 border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {logs.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <History className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No webhook logs yet</h3>
            <p className="text-muted-foreground">
              Webhook activity will appear here once you start receiving signals from TradingView or other sources.
            </p>
          </CardContent>
        </Card>
      ) : (
        <ScrollArea className="h-[calc(100vh-200px)]">
          <div className="space-y-4">
            {logs.map((log) => (
              <Card key={log.id} className="hover:border-primary/50 transition-colors">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Badge variant="outline">{log.source || 'unknown'}</Badge>
                        <span className="font-mono text-sm">{log.symbol || 'N/A'}</span>
                        <Badge variant={log.action?.toLowerCase() === 'buy' ? 'default' : log.action?.toLowerCase() === 'sell' ? 'destructive' : 'secondary'}>
                          {log.action || 'N/A'}
                        </Badge>
                      </CardTitle>
                      <CardDescription className="font-mono text-xs">
                        ID: {log.webhook_id}
                      </CardDescription>
                    </div>
                    {getStatusBadge(log)}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground text-xs">Quantity</p>
                      <p className="font-medium font-mono">{log.quantity ?? 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Accounts</p>
                      <p className="font-medium">
                        <span className="text-green-500">{log.successful_accounts ?? 0}</span>
                        <span className="text-muted-foreground">/</span>
                        <span>{log.total_accounts ?? 0}</span>
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Processing</p>
                      <p className="font-mono text-xs">{log.processing_time_ms ? `${log.processing_time_ms}ms` : 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Source IP</p>
                      <p className="font-mono text-xs">{log.source_ip || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Time</p>
                      <p className="text-xs">
                        {log.created_at
                          ? formatDistanceToNow(new Date(log.created_at), { addSuffix: true })
                          : 'N/A'}
                      </p>
                    </div>
                  </div>

                  {/* Execution details per account */}
                  {log.executions && log.executions.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-border">
                      <p className="text-muted-foreground text-xs mb-2">Execution Details</p>
                      <div className="space-y-1">
                        {log.executions.map((exec, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-xs">
                            <Badge variant="outline" className="text-xs py-0">{exec.broker}</Badge>
                            <span className="text-muted-foreground">Account {exec.account_id}:</span>
                            <span className={exec.status === 'success' ? 'text-green-500' : 'text-red-500'}>
                              {exec.status}
                            </span>
                            {exec.error && <span className="text-red-400 truncate max-w-[200px]">{exec.error}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {log.error_message && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <p className="text-muted-foreground text-xs">Error</p>
                      <p className="text-destructive text-xs">{log.error_message}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
