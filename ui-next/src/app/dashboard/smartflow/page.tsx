'use client';

import { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Zap,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  RefreshCw,
  Settings,
  Webhook,
  Activity,
  Brain,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MLDashboard } from '@/components/smartflow/ml-dashboard';
import { Lock, Crown, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface SentimentScore {
  score: number;
  bullish_flows: number;
  bearish_flows: number;
  total_premium: number;
  timestamp: string;
}

interface FlowSignal {
  ticker: string;
  action: string;
  score: number;
  confidence?: number;
  reason?: string;
  timestamp: string;
}

interface SmartFlowConfig {
  id?: number;
  enabled: boolean;
  webhook_urls: string[];
  buy_threshold: number;
  sell_threshold: number;
  close_threshold: number;
  score_window_minutes: number;
  update_interval_seconds: number;
  // Enhanced toggles
  enable_vix_inverse?: boolean;
  enable_golden_sweeps?: boolean;
  enable_leveraged_etfs?: boolean;
  vix_golden_threshold?: number;
  min_premium?: number;
  // Confirmation filter toggles
  enable_price_confirmation?: boolean;
  enable_rsi_filter?: boolean;
  enable_volume_filter?: boolean;
  enable_time_filter?: boolean;
  enable_fib_confluence?: boolean;
  min_confidence_score?: number;
  // AI Strategy Suite integration
  enable_ai_enhancement?: boolean;
  ai_analysis_types?: string[];
  // AI-Only Mode (24/7 trading)
  enable_ai_only_mode?: boolean;
  ai_only_scan_interval?: number;
  ai_only_confidence_threshold?: number;
  ai_only_instruments?: string[];
  // Confirmation filter parameters
  rsi_overbought?: number;
  rsi_oversold?: number;
  volume_spike_multiplier?: number;
  time_filter_start_hour?: number;
  time_filter_end_hour?: number;
}

interface SmartFlowStatus {
  enabled: boolean;
  latest_scores: {
    SPY?: SentimentScore;
    QQQ?: SentimentScore;
    GLD?: SentimentScore;
    IWM?: SentimentScore;
    DIA?: SentimentScore;
  };
  last_signals: Record<string, FlowSignal>;
  recent_signals: FlowSignal[];
  webhook_count: number;
  update_interval: number;
}

export default function SmartFlowPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);
  const [requiredTier, setRequiredTier] = useState<string>('Pro');
  const [config, setConfig] = useState<SmartFlowConfig>({
    enabled: false,
    webhook_urls: [''],
    buy_threshold: 4.0,
    sell_threshold: -4.0,
    close_threshold: 1.0,
    score_window_minutes: 5,
    update_interval_seconds: 45,
    // Enhanced toggles
    enable_vix_inverse: false,
    enable_golden_sweeps: false,
    enable_leveraged_etfs: false,
    vix_golden_threshold: 100000,
    min_premium: 50000,
    // Confirmation filters
    enable_price_confirmation: false,
    enable_rsi_filter: false,
    enable_volume_filter: false,
    enable_time_filter: false,
    enable_fib_confluence: false,
    min_confidence_score: 70,
    // AI Strategy Suite
    enable_ai_enhancement: false,
    ai_analysis_types: ['technical', 'patterns'],
    // AI-Only Mode (24/7)
    enable_ai_only_mode: false,
    ai_only_scan_interval: 300,
    ai_only_confidence_threshold: 70,
    ai_only_instruments: ['MES', 'NQ', 'RTY', 'USDJPY', 'GBPJPY', 'BTCUSD', 'ETHUSD'],
    // Filter parameters
    rsi_overbought: 70,
    rsi_oversold: 30,
    volume_spike_multiplier: 1.5,
    time_filter_start_hour: 10,
    time_filter_end_hour: 15,
  });
  const [status, setStatus] = useState<SmartFlowStatus | null>(null);

  useEffect(() => {
    loadConfig();
    const interval = setInterval(loadStatus, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/config', {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(data);
        setAccessDenied(false);
        await loadStatus();
      } else if (response.status === 402) {
        // User doesn't have required tier
        const errorData = await response.json();
        setAccessDenied(true);
        if (errorData.detail?.required_tiers) {
          setRequiredTier(errorData.detail.required_tiers.join(' or '));
        }
      } else if (response.status === 404) {
        // Config doesn't exist yet, use defaults
        setConfig({
          enabled: false,
          webhook_urls: [''],
          buy_threshold: 4.0,
          sell_threshold: -4.0,
          close_threshold: 1.0,
          score_window_minutes: 5,
          update_interval_seconds: 45,
          enable_vix_inverse: false,
          enable_golden_sweeps: false,
          enable_leveraged_etfs: false,
          vix_golden_threshold: 100000,
          min_premium: 50000,
          enable_price_confirmation: false,
          enable_rsi_filter: false,
          enable_volume_filter: false,
          enable_time_filter: false,
          enable_fib_confluence: false,
          min_confidence_score: 70,
          rsi_overbought: 70,
          rsi_oversold: 30,
          volume_spike_multiplier: 1.5,
          time_filter_start_hour: 10,
          time_filter_end_hour: 15,
        });
      }
    } catch (error) {
      console.error('Failed to load config:', error);
      toast({
        title: 'Error',
        description: 'Failed to load SmartFlow configuration',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/status', {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/v1/smartflow/config', {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(data);
        await loadStatus();
        toast({
          title: 'Success',
          description: config.enabled
            ? 'SmartFlow enabled and running'
            : 'SmartFlow configuration saved',
        });
      } else {
        throw new Error('Failed to save configuration');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save configuration',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadStatus();
    setTimeout(() => setRefreshing(false), 500);
  };

  const handleToggle = async (checked: boolean) => {
    const newConfig = { ...config, enabled: checked };
    setConfig(newConfig);

    // Save immediately with the new config value
    setSaving(true);
    try {
      const response = await fetch('/api/v1/smartflow/config', {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newConfig),
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(data);
        await loadStatus();
        toast({
          title: 'Success',
          description: checked
            ? 'SmartFlow enabled and running'
            : 'SmartFlow disabled',
        });
      } else {
        // Revert on error
        setConfig(config);
        throw new Error('Failed to update SmartFlow status');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update SmartFlow status',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const addWebhook = () => {
    setConfig({
      ...config,
      webhook_urls: [...config.webhook_urls, ''],
    });
  };

  const removeWebhook = (index: number) => {
    setConfig({
      ...config,
      webhook_urls: config.webhook_urls.filter((_, i) => i !== index),
    });
  };

  const updateWebhook = (index: number, value: string) => {
    const newWebhooks = [...config.webhook_urls];
    newWebhooks[index] = value;
    setConfig({
      ...config,
      webhook_urls: newWebhooks,
    });
  };

  const getScoreBadge = (score: number) => {
    if (score > 4) {
      return <Badge className="bg-green-500"><TrendingUp className="h-3 w-3 mr-1" /> Strong Buy</Badge>;
    } else if (score > 2) {
      return <Badge className="bg-green-600/70"><TrendingUp className="h-3 w-3 mr-1" /> Bullish</Badge>;
    } else if (score < -4) {
      return <Badge className="bg-red-500"><TrendingDown className="h-3 w-3 mr-1" /> Strong Sell</Badge>;
    } else if (score < -2) {
      return <Badge className="bg-red-600/70"><TrendingDown className="h-3 w-3 mr-1" /> Bearish</Badge>;
    } else {
      return <Badge variant="outline"><Minus className="h-3 w-3 mr-1" /> Neutral</Badge>;
    }
  };

  const getActionBadge = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy':
        return <Badge className="bg-green-500">BUY</Badge>;
      case 'sell':
        return <Badge className="bg-red-500">SELL</Badge>;
      case 'close':
        return <Badge variant="outline">CLOSE</Badge>;
      default:
        return <Badge>{action}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Show upgrade prompt if user doesn't have required tier
  if (accessDenied) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <Card className="max-w-lg w-full border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-purple-500/5">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 flex items-center justify-center mb-4">
              <Crown className="h-8 w-8 text-white" />
            </div>
            <CardTitle className="text-2xl">Upgrade to Unlock SmartFlow</CardTitle>
            <CardDescription className="text-base">
              SmartFlow AI Signals is a premium feature available on {requiredTier} plans
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <h4 className="font-semibold text-center">What you'll get:</h4>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-sm">
                  <Zap className="h-4 w-4 text-yellow-500" />
                  Real-time institutional options flow analysis
                </li>
                <li className="flex items-center gap-2 text-sm">
                  <Brain className="h-4 w-4 text-violet-500" />
                  AI-powered sentiment scoring for SPY, QQQ, GLD
                </li>
                <li className="flex items-center gap-2 text-sm">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  Automated BUY/SELL signals to your webhooks
                </li>
                <li className="flex items-center gap-2 text-sm">
                  <Activity className="h-4 w-4 text-blue-500" />
                  ML learning engine that improves over time
                </li>
              </ul>
            </div>

            <div className="flex flex-col gap-3">
              <Link href="/pricing" className="w-full">
                <Button className="w-full gap-2 bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-600/90">
                  View Pricing
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/dashboard/upgrade" className="w-full">
                <Button variant="outline" className="w-full gap-2">
                  <Crown className="h-4 w-4" />
                  Upgrade Now
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Zap className="h-8 w-8 text-yellow-500" />
            SmartFlow Indicator
          </h1>
          <p className="text-muted-foreground mt-1">
            AI-driven signals from institutional options flow data
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
            Refresh
          </Button>
          <div className="flex items-center gap-2">
            <Label htmlFor="enabled-toggle">Enable SmartFlow</Label>
            <Switch
              id="enabled-toggle"
              checked={config.enabled}
              onCheckedChange={handleToggle}
            />
          </div>
        </div>
      </div>

      {/* Live Sentiment Scores */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {['SPY', 'QQQ', 'IWM', 'DIA', 'GLD'].map((ticker) => {
          const scoreData = status?.latest_scores[ticker as keyof typeof status.latest_scores];
          const score = scoreData?.score || 0;
          const bullish = scoreData?.bullish_flows || 0;
          const bearish = scoreData?.bearish_flows || 0;
          const premium = scoreData?.total_premium || 0;

          return (
            <Card key={ticker}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-2xl font-bold">{ticker}</CardTitle>
                  {config.enabled && (
                    <Activity className="h-5 w-5 text-green-500 animate-pulse" />
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Sentiment Score</span>
                    <span className={cn(
                      "text-2xl font-bold",
                      score > 0 ? "text-green-500" : score < 0 ? "text-red-500" : "text-gray-500"
                    )}>
                      {score > 0 ? '+' : ''}{score.toFixed(1)}
                    </span>
                  </div>
                  <div>{getScoreBadge(score)}</div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <div className="text-muted-foreground">Bullish</div>
                      <div className="font-semibold text-green-500">{bullish}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Bearish</div>
                      <div className="font-semibold text-red-500">{bearish}</div>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Premium: ${(premium / 1000000).toFixed(2)}M
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* ML Learning Dashboard */}
      <Card className="border-2 border-violet-500/20 bg-gradient-to-br from-violet-500/5 to-purple-500/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-violet-400" />
            AI Learning Engine
            <Badge className="bg-gradient-to-r from-violet-500 to-purple-600 text-white">
              NEW
            </Badge>
          </CardTitle>
          <CardDescription>
            SmartFlow learns from your trade outcomes to improve win rate over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MLDashboard />
        </CardContent>
      </Card>

      {/* Recent Signals */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Signals</CardTitle>
          <CardDescription>
            Generated when sentiment scores exceed thresholds
          </CardDescription>
        </CardHeader>
        <CardContent>
          {status?.recent_signals && status.recent_signals.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {status.recent_signals.slice(0, 10).map((signal, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(signal.timestamp).toLocaleTimeString()}
                    </TableCell>
                    <TableCell className="font-semibold">{signal.ticker}</TableCell>
                    <TableCell>{getActionBadge(signal.action)}</TableCell>
                    <TableCell className={cn(
                      "font-semibold",
                      signal.score > 0 ? "text-green-500" : "text-red-500"
                    )}>
                      {signal.score > 0 ? '+' : ''}{signal.score != null ? signal.score.toFixed(1) : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {signal.confidence != null ? (
                        <Badge className={cn(
                          signal.confidence >= 80 ? "bg-green-500" :
                          signal.confidence >= 70 ? "bg-blue-500" :
                          signal.confidence >= 60 ? "bg-yellow-500" :
                          "bg-gray-500"
                        )}>
                          {signal.confidence.toFixed(0)}%
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">N/A</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-md truncate">
                      {signal.reason || 'No details'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {config.enabled
                ? 'No signals generated yet. Waiting for sentiment thresholds...'
                : 'Enable SmartFlow to start generating signals'}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enhanced Features */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            Enhanced Features
          </CardTitle>
          <CardDescription>
            Advanced SmartFlow Ultimate features for institutional-grade signals
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Quick Presets */}
          <div className="space-y-2">
            <Label>Quick Presets</Label>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setConfig({
                    ...config,
                    enable_golden_sweeps: true,
                    enable_time_filter: true,
                    enable_price_confirmation: true,
                    enable_rsi_filter: true,
                    min_confidence_score: 70,
                  });
                }}
              >
                Conservative
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setConfig({
                    ...config,
                    enable_vix_inverse: true,
                    enable_golden_sweeps: true,
                    enable_price_confirmation: true,
                    enable_rsi_filter: true,
                    enable_fib_confluence: true,
                    min_confidence_score: 70,
                  });
                }}
              >
                Moderate
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setConfig({
                    ...config,
                    enable_vix_inverse: true,
                    enable_golden_sweeps: true,
                    enable_price_confirmation: true,
                    enable_rsi_filter: true,
                    enable_volume_filter: true,
                    enable_time_filter: true,
                    enable_fib_confluence: true,
                    min_confidence_score: 80,
                  });
                }}
              >
                Maximum Quality
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setConfig({
                    ...config,
                    enable_vix_inverse: false,
                    enable_golden_sweeps: false,
                    enable_leveraged_etfs: false,
                    enable_price_confirmation: false,
                    enable_rsi_filter: false,
                    enable_volume_filter: false,
                    enable_time_filter: false,
                    enable_fib_confluence: false,
                  });
                }}
              >
                Disable All
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Conservative: 60-70% win rate, 2-5 signals/day | Moderate: Balanced | Maximum: 70%+ win rate
            </p>
          </div>

          {/* Enhanced Toggles */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="vix-inverse">VIX/UVXY Inverse Logic</Label>
                  <p className="text-xs text-muted-foreground">
                    Bullish VIX calls → Bearish market signals
                  </p>
                </div>
                <Switch
                  id="vix-inverse"
                  checked={config.enable_vix_inverse || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_vix_inverse: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="golden-sweeps">Golden Sweeps ($1M+)</Label>
                  <p className="text-xs text-muted-foreground">
                    Prioritize whale trades with +3/+4 bonuses
                  </p>
                </div>
                <Switch
                  id="golden-sweeps"
                  checked={config.enable_golden_sweeps || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_golden_sweeps: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="leveraged-etfs">Leveraged ETFs (3x)</Label>
                  <p className="text-xs text-muted-foreground">
                    Trade SPXL/TQQQ/TNA instead of futures
                  </p>
                </div>
                <Switch
                  id="leveraged-etfs"
                  checked={config.enable_leveraged_etfs || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_leveraged_etfs: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="ai-enhancement" className="flex items-center gap-2">
                    AI Strategy Enhancement
                    <span className="text-xs bg-primary text-primary-foreground px-1.5 py-0.5 rounded">NEW</span>
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Boost confidence when Claude AI agrees with signal direction
                  </p>
                </div>
                <Switch
                  id="ai-enhancement"
                  checked={config.enable_ai_enhancement || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_ai_enhancement: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="ai-only-mode" className="flex items-center gap-2">
                    AI-Only 24/7 Mode
                    <span className="text-xs bg-green-500 text-white px-1.5 py-0.5 rounded">24/7</span>
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Trade overnight using AI analysis when no FlowAlgo data (futures, forex, crypto)
                  </p>
                </div>
                <Switch
                  id="ai-only-mode"
                  checked={config.enable_ai_only_mode || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_ai_only_mode: checked })
                  }
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI-Only Mode Settings */}
      {config.enable_ai_only_mode && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI-Only Mode Settings
            </CardTitle>
            <CardDescription>
              Configure 24/7 AI-driven trading for overnight sessions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Scan Interval (seconds)</Label>
                <Input
                  type="number"
                  value={config.ai_only_scan_interval || 300}
                  onChange={(e) => setConfig({ ...config, ai_only_scan_interval: parseInt(e.target.value) })}
                  min={60}
                  max={900}
                />
                <p className="text-xs text-muted-foreground">How often to analyze instruments (60-900s)</p>
              </div>
              <div className="space-y-2">
                <Label>Min Confidence Threshold (%)</Label>
                <Input
                  type="number"
                  value={config.ai_only_confidence_threshold || 70}
                  onChange={(e) => setConfig({ ...config, ai_only_confidence_threshold: parseFloat(e.target.value) })}
                  min={50}
                  max={95}
                />
                <p className="text-xs text-muted-foreground">Minimum AI confidence to generate signal</p>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Instruments to Trade</Label>
              <Input
                value={(config.ai_only_instruments || []).join(', ')}
                onChange={(e) => setConfig({ ...config, ai_only_instruments: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                placeholder="MES, NQ, RTY, USDJPY, BTCUSD"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list: futures (MES, NQ, RTY), forex (USDJPY, GBPJPY), crypto (BTCUSD, ETHUSD)
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Confirmation Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Confirmation Filters
          </CardTitle>
          <CardDescription>
            Multi-factor confirmation for higher win rates (requires Polygon API key)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="price-confirm">Price Confirmation (EMA)</Label>
                  <p className="text-xs text-muted-foreground">
                    Require EMA 9/20 alignment
                  </p>
                </div>
                <Switch
                  id="price-confirm"
                  checked={config.enable_price_confirmation || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_price_confirmation: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="rsi-filter">RSI Filter</Label>
                  <p className="text-xs text-muted-foreground">
                    Avoid overbought/oversold conditions
                  </p>
                </div>
                <Switch
                  id="rsi-filter"
                  checked={config.enable_rsi_filter || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_rsi_filter: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="volume-filter">Volume Spike Detection</Label>
                  <p className="text-xs text-muted-foreground">
                    Require {config.volume_spike_multiplier || 1.5}x average volume
                  </p>
                </div>
                <Switch
                  id="volume-filter"
                  checked={config.enable_volume_filter || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_volume_filter: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="time-filter">Time-of-Day Guard</Label>
                  <p className="text-xs text-muted-foreground">
                    Trade only {config.time_filter_start_hour || 10}am-{config.time_filter_end_hour || 3}pm EST
                  </p>
                </div>
                <Switch
                  id="time-filter"
                  checked={config.enable_time_filter || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_time_filter: checked })
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="fib-confluence">Fibonacci Confluence</Label>
                  <p className="text-xs text-muted-foreground">
                    Detect key level bounces (61.8%, 50%, etc.)
                  </p>
                </div>
                <Switch
                  id="fib-confluence"
                  checked={config.enable_fib_confluence || false}
                  onCheckedChange={(checked) =>
                    setConfig({ ...config, enable_fib_confluence: checked })
                  }
                />
              </div>
            </div>
          </div>

          {/* Confidence Score Threshold */}
          <div className="space-y-2">
            <Label htmlFor="min-confidence">Minimum Confidence Score (%)</Label>
            <Input
              id="min-confidence"
              type="number"
              min="0"
              max="100"
              step="5"
              value={config.min_confidence_score || 70}
              onChange={(e) =>
                setConfig({ ...config, min_confidence_score: parseFloat(e.target.value) })
              }
            />
            <p className="text-xs text-muted-foreground">
              Only send signals with confidence ≥ {config.min_confidence_score || 70}%. Higher = fewer but better quality signals.
            </p>
          </div>

          {/* Advanced Parameters */}
          <details className="space-y-2">
            <summary className="cursor-pointer font-medium text-sm">Advanced Parameters</summary>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="rsi-ob">RSI Overbought Threshold</Label>
                <Input
                  id="rsi-ob"
                  type="number"
                  value={config.rsi_overbought || 70}
                  onChange={(e) =>
                    setConfig({ ...config, rsi_overbought: parseFloat(e.target.value) })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rsi-os">RSI Oversold Threshold</Label>
                <Input
                  id="rsi-os"
                  type="number"
                  value={config.rsi_oversold || 30}
                  onChange={(e) =>
                    setConfig({ ...config, rsi_oversold: parseFloat(e.target.value) })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vol-mult">Volume Spike Multiplier</Label>
                <Input
                  id="vol-mult"
                  type="number"
                  step="0.1"
                  value={config.volume_spike_multiplier || 1.5}
                  onChange={(e) =>
                    setConfig({ ...config, volume_spike_multiplier: parseFloat(e.target.value) })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="time-start">Trading Window Start (hour)</Label>
                <Input
                  id="time-start"
                  type="number"
                  min="0"
                  max="23"
                  value={config.time_filter_start_hour || 10}
                  onChange={(e) =>
                    setConfig({ ...config, time_filter_start_hour: parseInt(e.target.value) })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="time-end">Trading Window End (hour)</Label>
                <Input
                  id="time-end"
                  type="number"
                  min="0"
                  max="23"
                  value={config.time_filter_end_hour || 15}
                  onChange={(e) =>
                    setConfig({ ...config, time_filter_end_hour: parseInt(e.target.value) })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="min-prem">Minimum Flow Premium ($)</Label>
                <Input
                  id="min-prem"
                  type="number"
                  step="10000"
                  value={config.min_premium || 50000}
                  onChange={(e) =>
                    setConfig({ ...config, min_premium: parseFloat(e.target.value) })
                  }
                />
              </div>
            </div>
          </details>
        </CardContent>
      </Card>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Webhook className="h-5 w-5" />
            <CardTitle>Basic Configuration</CardTitle>
          </div>
          <CardDescription>
            Configure SmartFlow thresholds and webhooks
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Webhooks */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Webhook className="h-4 w-4" />
              <Label>Webhook URLs</Label>
            </div>
            {config.webhook_urls.map((url, idx) => (
              <div key={idx} className="flex gap-2">
                <Input
                  value={url}
                  onChange={(e) => updateWebhook(idx, e.target.value)}
                  placeholder="https://api.mytradeflow.app/webhooks/..."
                />
                {config.webhook_urls.length > 1 && (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => removeWebhook(idx)}
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={addWebhook}>
              Add Webhook
            </Button>
          </div>

          {/* Thresholds */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="buy-threshold">Buy Threshold</Label>
              <Input
                id="buy-threshold"
                type="number"
                step="0.5"
                value={config.buy_threshold}
                onChange={(e) => setConfig({ ...config, buy_threshold: parseFloat(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Generate BUY signal when score exceeds this value
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="sell-threshold">Sell Threshold</Label>
              <Input
                id="sell-threshold"
                type="number"
                step="0.5"
                value={config.sell_threshold}
                onChange={(e) => setConfig({ ...config, sell_threshold: parseFloat(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Generate SELL signal when score falls below this value
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="close-threshold">Close Threshold</Label>
              <Input
                id="close-threshold"
                type="number"
                step="0.5"
                value={config.close_threshold}
                onChange={(e) => setConfig({ ...config, close_threshold: parseFloat(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Generate CLOSE signal when score returns near zero
              </p>
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="window">Score Window (minutes)</Label>
              <Input
                id="window"
                type="number"
                value={config.score_window_minutes}
                onChange={(e) => setConfig({ ...config, score_window_minutes: parseInt(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Rolling window for score calculation
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="interval">Update Interval (seconds)</Label>
              <Input
                id="interval"
                type="number"
                value={config.update_interval_seconds}
                onChange={(e) => setConfig({ ...config, update_interval_seconds: parseInt(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                How often to fetch flows and compute scores
              </p>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Configuration
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* How It Works */}
      <Card>
        <CardHeader>
          <CardTitle>How SmartFlow Works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <div>
            <strong className="text-foreground">1. Data Collection:</strong> Every {config.update_interval_seconds} seconds, SmartFlow fetches live options flow data (sweeps and blocks) from FlowAlgo for SPY, QQQ, and GLD.
          </div>
          <div>
            <strong className="text-foreground">2. Sentiment Scoring:</strong> Each flow is scored based on premium size (±1 for &gt;$50k, ±2 for &gt;$100k, ±3 for &gt;$500k) with a +0.5 bonus for sweeps. Bullish calls add to the score, bearish puts subtract.
          </div>
          <div>
            <strong className="text-foreground">3. Signal Generation:</strong> When the net score over a {config.score_window_minutes}-minute window exceeds your thresholds, SmartFlow generates BUY/SELL/CLOSE signals.
          </div>
          <div>
            <strong className="text-foreground">4. Webhook Delivery:</strong> Signals are posted to your webhook URLs in TradingView-compatible JSON format with mapped tickers (SPY→MES, QQQ→NQ, GLD→GC).
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
