'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, TrendingDown, AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface Signal {
  id: string;
  ticker: string;
  action: 'BUY' | 'SELL' | 'CLOSE';
  price: number;
  score?: number;
  strategy?: string;
  confidence?: number;
  reason?: string;
  timestamp: string;
  webhook_status: 'pending' | 'sent' | 'failed';
  source: string;
  bullish_flows?: number;
  bearish_flows?: number;
  total_premium?: number;
}

interface LiveSignalsDashboardProps {
  className?: string;
}

export function LiveSignalsDashboard({ className }: LiveSignalsDashboardProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSignals = useCallback(async () => {
    try {
      // Try to fetch from forward test status endpoint
      const response = await fetch('/api/v1/smartflow/forward-test/status', {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        if (data.recent_signals) {
          setSignals(data.recent_signals);
        }
        setLastUpdate(new Date());
        setError(null);
      } else {
        // Try alternative signals endpoint
        const altResponse = await fetch('/api/v1/smartflow/signals?limit=20', {
          credentials: 'include',
        });

        if (altResponse.ok) {
          const altData = await altResponse.json();
          // Transform to match signal format
          const transformed = (Array.isArray(altData) ? altData : []).map((s: any) => ({
            id: s.id?.toString() || Math.random().toString(),
            ticker: s.ticker,
            action: s.action?.toUpperCase() || 'BUY',
            price: s.price || 0,
            score: s.score,
            strategy: s.engine_type || 'SmartFlow',
            confidence: s.confidence,
            reason: s.reason,
            timestamp: s.created_at || new Date().toISOString(),
            webhook_status: s.post_successful ? 'sent' : 'pending',
            source: 'database',
            bullish_flows: s.bullish_flows,
            bearish_flows: s.bearish_flows,
            total_premium: s.total_premium,
          }));
          setSignals(transformed);
          setLastUpdate(new Date());
          setError(null);
        }
      }
    } catch (err) {
      console.error('Failed to load signals:', err);
      setError('Unable to fetch live signals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSignals();

    // Auto-refresh every 10 seconds
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(loadSignals, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loadSignals, autoRefresh]);

  const formatPrice = (price: number, ticker: string) => {
    if (['BTCUSD', 'ETHUSD'].includes(ticker)) {
      return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (['USDJPY', 'GBPJPY'].includes(ticker)) {
      return price.toFixed(3);
    }
    if (['XAUUSD'].includes(ticker)) {
      return `$${price.toFixed(2)}`;
    }
    return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZone: 'America/New_York',
    });
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'BUY':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'SELL':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getWebhookStatusBadge = (status: string) => {
    switch (status) {
      case 'sent':
        return (
          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
            <CheckCircle className="h-3 w-3 mr-1" /> Sent
          </Badge>
        );
      case 'pending':
        return (
          <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
            <Clock className="h-3 w-3 mr-1" /> Pending
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
            <AlertCircle className="h-3 w-3 mr-1" /> Failed
          </Badge>
        );
      default:
        return null;
    }
  };

  const getTickerBadge = (ticker: string) => {
    const colors: Record<string, string> = {
      'US30': 'bg-blue-500/10 text-blue-500 border-blue-500/20',
      'NAS100': 'bg-purple-500/10 text-purple-500 border-purple-500/20',
      'SPX500': 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
      'US500': 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
      'XAUUSD': 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
      'BTCUSD': 'bg-orange-500/10 text-orange-500 border-orange-500/20',
      'ETHUSD': 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20',
      'USDJPY': 'bg-pink-500/10 text-pink-500 border-pink-500/20',
      'GBPJPY': 'bg-rose-500/10 text-rose-500 border-rose-500/20',
    };

    return (
      <Badge variant="outline" className={colors[ticker] || 'bg-gray-500/10 text-gray-500 border-gray-500/20'}>
        {ticker}
      </Badge>
    );
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Live Trading Signals</CardTitle>
            <CardDescription>
              Real-time signals sent to webhook
              {lastUpdate && (
                <span className="ml-2 text-xs">
                  Last update: {lastUpdate.toLocaleTimeString()}
                </span>
              )}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={autoRefresh ? 'bg-green-500/10' : ''}
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? 'Live' : 'Paused'}
            </Button>
            <Button variant="outline" size="sm" onClick={loadSignals} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="text-center py-4 text-yellow-500">
            <AlertCircle className="h-6 w-6 mx-auto mb-2" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {!error && signals.length === 0 && !loading && (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No signals yet. Waiting for market activity...</p>
            <p className="text-xs mt-1">Signals appear here when generated by SmartFlow</p>
          </div>
        )}

        {signals.length > 0 && (
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {signals.map((signal) => (
              <div
                key={signal.id}
                className="flex items-center justify-between p-3 rounded-lg bg-card border hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {getActionIcon(signal.action)}
                  <div>
                    <div className="flex items-center gap-2">
                      {getTickerBadge(signal.ticker)}
                      <span className={`font-semibold ${signal.action === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                        {signal.action}
                      </span>
                      <span className="text-sm font-mono">
                        @ {formatPrice(signal.price, signal.ticker)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      <span>{formatTime(signal.timestamp)} EST</span>
                      {signal.bullish_flows !== undefined && signal.bearish_flows !== undefined && (
                        <span className="text-blue-400">
                          Flow: +{signal.bullish_flows}/-{signal.bearish_flows}
                        </span>
                      )}
                      {signal.total_premium !== undefined && signal.total_premium > 0 && (
                        <span className="text-purple-400">
                          ${(signal.total_premium / 1000).toFixed(0)}K
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {signal.confidence && (
                    <Badge variant="secondary" className="text-xs">
                      {signal.confidence.toFixed(0)}%
                    </Badge>
                  )}
                  {signal.score && (
                    <Badge variant="outline" className={`text-xs ${signal.score > 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {signal.score > 0 ? '+' : ''}{signal.score.toFixed(1)}
                    </Badge>
                  )}
                  {getWebhookStatusBadge(signal.webhook_status)}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Signal Stats Summary */}
        {signals.length > 0 && (
          <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-500">
                {signals.filter((s) => s.action === 'BUY').length}
              </div>
              <div className="text-xs text-muted-foreground">Buy Signals</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-500">
                {signals.filter((s) => s.action === 'SELL').length}
              </div>
              <div className="text-xs text-muted-foreground">Sell Signals</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-500">
                {signals.filter((s) => s.webhook_status === 'sent').length}
              </div>
              <div className="text-xs text-muted-foreground">Sent OK</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-500">
                {signals.filter((s) => s.webhook_status === 'failed').length}
              </div>
              <div className="text-xs text-muted-foreground">Failed</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
