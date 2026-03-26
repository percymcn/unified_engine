'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Zap, Clock, Target, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

interface QuickModeStatus {
  enabled: boolean;
  scan_interval: number;
  min_confidence: number;
  min_rr: number;
  require_15m_confirmation: boolean;
  instruments?: string[];
}

interface QuickSignal {
  id: number;
  ticker: string;
  action: string;
  score: number;
  price: number | null;
  created_at: string;
  engine_type?: string;
}

export function QuickModeDashboard() {
  const [status, setStatus] = useState<QuickModeStatus | null>(null);
  const [recentSignals, setRecentSignals] = useState<QuickSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuickStatus();
    fetchRecentSignals();
  }, []);

  const fetchQuickStatus = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/status', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setStatus({
          enabled: data.enable_quick_mode || false,
          scan_interval: data.quick_scan_interval || 60,
          min_confidence: data.quick_min_confidence || 60,
          min_rr: data.quick_min_rr || 1.5,
          require_15m_confirmation: data.quick_require_15m_confirmation !== false,
          instruments: data.quick_instruments || [],
        });
      }
    } catch (error) {
      console.error('Failed to fetch quick mode status:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentSignals = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/signals?limit=20', {
        credentials: 'include',
      });
      if (response.ok) {
        const signals = await response.json();
        // Filter for quick signals only
        const quickSignals = signals.filter((s: QuickSignal) => s.engine_type === 'quick');
        setRecentSignals(quickSignals.slice(0, 5));
      }
    } catch (error) {
      console.error('Failed to fetch recent signals:', error);
    }
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading Quick Mode status...</div>;
  }

  if (!status) {
    return <div className="text-sm text-muted-foreground">Quick Mode status unavailable</div>;
  }

  return (
    <div className="space-y-4">
      {/* Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Quick Mode Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Scan Interval</Label>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-500" />
                <span className="text-lg font-bold">{status.scan_interval}s</span>
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Min Confidence</Label>
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-amber-500" />
                <span className="text-lg font-bold">{status.min_confidence}%</span>
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Min R:R</Label>
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-amber-500" />
                <span className="text-lg font-bold">{status.min_rr}:1</span>
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">15m Confirmation</Label>
              <div className="flex items-center gap-2">
                <Badge variant={status.require_15m_confirmation ? 'default' : 'outline'} className="bg-amber-500">
                  {status.require_15m_confirmation ? 'Required' : 'Optional'}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Signals */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Recent Quick Signals
          </CardTitle>
          <CardDescription className="text-xs">
            5-minute momentum scalping signals
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recentSignals.length === 0 ? (
            <div className="text-sm text-muted-foreground py-4 text-center">
              No quick signals generated yet.
              <br />
              <span className="text-xs">Quick Mode scans for 5m momentum setups every {status.scan_interval}s</span>
            </div>
          ) : (
            <div className="space-y-2">
              {recentSignals.map((signal) => (
                <div key={signal.id} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <div className="flex items-center gap-2">
                    {signal.action === 'buy' ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                    <div>
                      <div className="font-medium text-sm">{signal.ticker}</div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(signal.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={cn(
                      signal.action === 'buy' ? 'bg-green-500' : 'bg-red-500',
                      'text-xs'
                    )}>
                      {signal.action.toUpperCase()}
                    </Badge>
                    <span className="text-sm font-medium">{signal.score.toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Mode Info */}
      <Card className="bg-amber-500/5 border-amber-500/20">
        <CardContent className="pt-4">
          <div className="text-xs text-muted-foreground">
            <div className="font-medium mb-2">Quick Mode Strategy:</div>
            <ul className="space-y-1 list-disc list-inside">
              <li>Scans 5m timeframe for momentum setups</li>
              <li>Minimum {status.min_rr}:1 risk-reward ratio</li>
              <li>Requires {status.min_confidence}% confidence threshold</li>
              {status.require_15m_confirmation && <li>Requires 15m trend confirmation</li>}
              <li>Fast execution for scalping opportunities</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
