'use client';

import { useEffect, useState, useCallback } from 'react';
import { History, RefreshCw, CheckCircle2, XCircle, AlertCircle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { formatDistanceToNow } from 'date-fns';

interface WebhookLog {
  id: number;
  webhook_id: string;
  source: string;
  source_ip: string;
  user_agent: string;
  payload: string;
  status: string;
  error_message?: string;
  created_at: string;
}

export default function WebhookLogsPage() {
  const [logs, setLogs] = useState<WebhookLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchLogs = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch('/api/webhooks/logs');
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

  const getStatusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'success':
      case 'executed':
        return (
          <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Success
          </Badge>
        );
      case 'failed':
      case 'error':
        return (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Failed
          </Badge>
        );
      case 'pending':
        return (
          <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20">
            <Clock className="h-3 w-3 mr-1" />
            Pending
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary">
            <AlertCircle className="h-3 w-3 mr-1" />
            {status || 'Unknown'}
          </Badge>
        );
    }
  };

  const parsePayload = (payload: string) => {
    try {
      const parsed = JSON.parse(payload);
      return {
        symbol: parsed.symbol || parsed.ticker || 'N/A',
        action: parsed.action || 'N/A',
        quantity: parsed.quantity || parsed.contracts || parsed.volume || 'N/A',
      };
    } catch {
      return { symbol: 'N/A', action: 'N/A', quantity: 'N/A' };
    }
  };

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
            {logs.map((log) => {
              const { symbol, action, quantity } = parsePayload(log.payload);
              return (
                <Card key={log.id} className="hover:border-primary/50 transition-colors">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-base flex items-center gap-2">
                          <Badge variant="outline">{log.source || 'unknown'}</Badge>
                          <span className="font-mono text-sm">{symbol}</span>
                          <Badge variant={action === 'buy' ? 'default' : action === 'sell' ? 'destructive' : 'secondary'}>
                            {action}
                          </Badge>
                        </CardTitle>
                        <CardDescription className="font-mono text-xs">
                          ID: {log.webhook_id}
                        </CardDescription>
                      </div>
                      {getStatusBadge(log.status)}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Quantity</p>
                        <p className="font-medium">{quantity}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Source IP</p>
                        <p className="font-mono text-xs">{log.source_ip || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Time</p>
                        <p className="text-xs">
                          {log.created_at
                            ? formatDistanceToNow(new Date(log.created_at), { addSuffix: true })
                            : 'N/A'}
                        </p>
                      </div>
                      {log.error_message && (
                        <div className="col-span-2 md:col-span-4">
                          <p className="text-muted-foreground">Error</p>
                          <p className="text-destructive text-xs">{log.error_message}</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
