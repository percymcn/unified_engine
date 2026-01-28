'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Activity,
  Wifi,
  WifiOff,
  AlertTriangle,
  RefreshCw,
  Clock,
  Zap,
  Ghost,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface BrokerHeartbeat {
  accountId: number;
  accountName: string;
  broker: string;
  status: 'connected' | 'degraded' | 'disconnected' | 'reconnecting';
  latencyMs: number;
  lastPing: string;
  uptime: number; // percentage
  reconnectAttempts: number;
  ghostModeActive: boolean;
}

interface HeartbeatSummary {
  totalAccounts: number;
  connectedCount: number;
  degradedCount: number;
  disconnectedCount: number;
  averageLatency: number;
  ghostModeAccounts: number;
}

export function BrokerHeartbeat() {
  const [heartbeats, setHeartbeats] = useState<BrokerHeartbeat[]>([]);
  const [summary, setSummary] = useState<HeartbeatSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoReconnect, setAutoReconnect] = useState(true);

  const fetchHeartbeats = useCallback(async () => {
    try {
      const response = await fetch('/api/dashboard/heartbeat', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setHeartbeats(data.heartbeats || []);
        setSummary(data.summary || null);
      }
    } catch (error) {
      console.error('Error fetching heartbeats:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHeartbeats();
    // Poll every 5 seconds for real-time heartbeat
    const interval = setInterval(fetchHeartbeats, 5000);
    return () => clearInterval(interval);
  }, [fetchHeartbeats]);

  const handleReconnect = async (accountId: number) => {
    try {
      await fetch(`/api/accounts/${accountId}/reconnect`, {
        method: 'POST',
        credentials: 'include',
      });
      fetchHeartbeats();
    } catch (error) {
      console.error('Reconnect failed:', error);
    }
  };

  const handleReconnectAll = async () => {
    try {
      await fetch('/api/accounts/reconnect-all', {
        method: 'POST',
        credentials: 'include',
      });
      fetchHeartbeats();
    } catch (error) {
      console.error('Reconnect all failed:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-emerald-500" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      case 'reconnecting':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <WifiOff className="h-4 w-4 text-red-500" />;
    }
  };

  const getLatencyColor = (ms: number) => {
    if (ms < 50) return 'text-emerald-500';
    if (ms < 100) return 'text-amber-500';
    return 'text-red-500';
  };

  const getLatencyBadge = (ms: number) => {
    if (ms < 5) return { label: 'Ultra-Low', color: 'bg-emerald-500' };
    if (ms < 50) return { label: 'Fast', color: 'bg-emerald-400' };
    if (ms < 100) return { label: 'Normal', color: 'bg-amber-500' };
    return { label: 'Slow', color: 'bg-red-500' };
  };

  if (loading) {
    return (
      <Card className="cyber-card">
        <CardContent className="flex items-center justify-center h-32">
          <Activity className="h-6 w-6 animate-pulse text-primary" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="cyber-card">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Broker Heartbeat
          </CardTitle>
          <div className="flex items-center gap-2">
            {summary && summary.ghostModeAccounts > 0 && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Badge variant="outline" className="gap-1">
                      <Ghost className="h-3 w-3" />
                      {summary.ghostModeAccounts}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    {summary.ghostModeAccounts} accounts in Ghost Mode
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            <Button variant="ghost" size="sm" onClick={fetchHeartbeats}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary bar */}
        {summary && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
            <div className="flex items-center gap-4 text-sm">
              <span className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                {summary.connectedCount} Connected
              </span>
              {summary.degradedCount > 0 && (
                <span className="flex items-center gap-1">
                  <div className="h-2 w-2 rounded-full bg-amber-500" />
                  {summary.degradedCount} Degraded
                </span>
              )}
              {summary.disconnectedCount > 0 && (
                <span className="flex items-center gap-1">
                  <div className="h-2 w-2 rounded-full bg-red-500" />
                  {summary.disconnectedCount} Disconnected
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Zap className={cn('h-4 w-4', getLatencyColor(summary.averageLatency))} />
              <span className={getLatencyColor(summary.averageLatency)}>
                {summary.averageLatency.toFixed(0)}ms avg
              </span>
            </div>
          </div>
        )}

        {/* Heartbeat list */}
        <div className="space-y-2">
          {heartbeats.map((hb) => {
            const latencyInfo = getLatencyBadge(hb.latencyMs);
            return (
              <div
                key={hb.accountId}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg border transition-all',
                  hb.status === 'connected' && 'border-emerald-500/30 bg-emerald-500/5',
                  hb.status === 'degraded' && 'border-amber-500/30 bg-amber-500/5',
                  hb.status === 'disconnected' && 'border-red-500/30 bg-red-500/5',
                  hb.status === 'reconnecting' && 'border-blue-500/30 bg-blue-500/5'
                )}
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(hb.status)}
                  <div>
                    <p className="text-sm font-medium">{hb.accountName}</p>
                    <p className="text-xs text-muted-foreground">{hb.broker}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {hb.ghostModeActive && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <Ghost className="h-4 w-4 text-primary" />
                        </TooltipTrigger>
                        <TooltipContent>Ghost Mode Active</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}

                  <div className="text-right">
                    <Badge className={cn('text-xs', latencyInfo.color)}>
                      {hb.latencyMs}ms
                    </Badge>
                    <p className="text-xs text-muted-foreground mt-1">
                      <Clock className="h-3 w-3 inline mr-1" />
                      {new Date(hb.lastPing).toLocaleTimeString()}
                    </p>
                  </div>

                  {hb.status === 'disconnected' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReconnect(hb.accountId)}
                    >
                      Reconnect
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Reconnect all button */}
        {summary && summary.disconnectedCount > 0 && (
          <Button
            variant="outline"
            className="w-full"
            onClick={handleReconnectAll}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Reconnect All ({summary.disconnectedCount})
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
