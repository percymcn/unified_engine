'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  RefreshCw,
  Settings,
  Zap,
  AlertCircle,
  CheckCircle2,
  Router as RouterIcon,
  TrendingUp,
  Activity
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface RouterStatus {
  routing_mode: string;
  manual_override_engine: string | null;
  auto_eligible_engines: string[];
  manual_only_engines: string[];
  all_engines: string[];
  comparison_rankings_available: string[];
  fallback_rules_available: string[];
  timestamp: string;
}

interface RouterDecision {
  routing_mode: string;
  current_regime: string;
  selected_engine: string;
  eligible_engines: string[];
  ranking: string[];
  decision_source: string;
  decision_reason: string;
  fallback_used: boolean;
  timestamp: string;
  manual_override: string | null;
  regime_confidence: number;
}

interface RegimeMapping {
  [regime: string]: {
    preferred_engine: string;
    ranking: string[];
    source: string;
    confidence: number;
    notes: string;
    is_data_backed: boolean;
    sample_size?: number;
  };
}

const ENGINE_COLORS: Record<string, string> = {
  unified: 'bg-gray-500',
  deterministic: 'bg-emerald-500',
  quick: 'bg-amber-500',
  flow: 'bg-blue-500',
  ai: 'bg-purple-500',
};

const ENGINE_LABELS: Record<string, string> = {
  unified: 'Unified',
  deterministic: 'Deterministic',
  quick: 'Quick',
  flow: 'Flow',
  ai: 'AI',
};

const DECISION_SOURCE_ICONS: Record<string, { icon: any; color: string; label: string }> = {
  manual_override: { icon: Settings, color: 'text-blue-500', label: 'Manual Override' },
  comparison_results: { icon: Activity, color: 'text-green-500', label: 'Data-Backed' },
  fallback_rule: { icon: AlertCircle, color: 'text-yellow-500', label: 'Rule-Based' },
  default: { icon: AlertCircle, color: 'text-gray-500', label: 'Default' },
};

export function AdaptiveRouterDashboard() {
  const [status, setStatus] = useState<RouterStatus | null>(null);
  const [decision, setDecision] = useState<RouterDecision | null>(null);
  const [mapping, setMapping] = useState<RegimeMapping | null>(null);
  const [loading, setLoading] = useState(false);
  const [testRegime, setTestRegime] = useState('trending_up');
  const { toast } = useToast();

  useEffect(() => {
    loadRouterStatus();
    loadRegimeMapping();
  }, []);

  const loadRouterStatus = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/router/status');
      if (!response.ok) throw new Error('Failed to load router status');
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load router status',
        variant: 'destructive',
      });
    }
  };

  const loadRegimeMapping = async () => {
    try {
      const response = await fetch('/api/v1/smartflow/router/mapping');
      if (!response.ok) throw new Error('Failed to load regime mapping');
      const data = await response.json();
      // Backend returns { mappings: {...} }, extract the mappings object
      setMapping(data.mappings || data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load regime mapping',
        variant: 'destructive',
      });
    }
  };

  const setRoutingMode = async (mode: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/smartflow/router/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      if (!response.ok) throw new Error('Failed to set routing mode');

      toast({
        title: 'Routing mode updated',
        description: `Router set to ${mode} mode`,
      });

      await loadRouterStatus();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update routing mode',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const setManualOverride = async (engine: string | null) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/smartflow/router/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine }),
      });
      if (!response.ok) throw new Error('Failed to set override');

      toast({
        title: engine ? 'Override set' : 'Override cleared',
        description: engine
          ? `All requests will use ${ENGINE_LABELS[engine]}`
          : 'Router will use normal routing logic',
      });

      await loadRouterStatus();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to set override',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const testRoutingDecision = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/smartflow/router/decision?regime=${testRegime}`);
      if (!response.ok) throw new Error('Failed to test routing');
      const data = await response.json();
      setDecision(data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to test routing decision',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  if (!status) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  const DecisionSourceIcon = decision
    ? DECISION_SOURCE_ICONS[decision.decision_source]?.icon || AlertCircle
    : AlertCircle;

  const decisionSourceInfo = decision
    ? DECISION_SOURCE_ICONS[decision.decision_source]
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <RouterIcon className="h-8 w-8 text-blue-500" />
            Adaptive Engine Router
          </h2>
          <p className="text-muted-foreground mt-1">
            Regime-aware engine selection with transparent routing logic
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            loadRouterStatus();
            loadRegimeMapping();
          }}
          disabled={loading}
        >
          <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Routing Mode Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Routing Mode Controls
          </CardTitle>
          <CardDescription>
            Configure how the router selects engines for signal requests
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Button
              variant={status.routing_mode === 'manual' ? 'default' : 'outline'}
              onClick={() => setRoutingMode('manual')}
              disabled={loading}
              className="h-20 flex-col"
            >
              <Settings className="h-6 w-6 mb-2" />
              <span className="font-semibold">Manual Mode</span>
              <span className="text-xs text-muted-foreground">User selects engine</span>
            </Button>

            <Button
              variant={status.routing_mode === 'auto_by_regime' ? 'default' : 'outline'}
              onClick={() => setRoutingMode('auto_by_regime')}
              disabled={loading}
              className="h-20 flex-col"
            >
              <Zap className="h-6 w-6 mb-2" />
              <span className="font-semibold">Auto-by-Regime</span>
              <span className="text-xs text-muted-foreground">Router selects based on regime</span>
            </Button>
          </div>

          {/* Manual Override Controls */}
          <div className="border-t pt-4">
            <Label className="text-sm font-medium mb-3 block">Manual Override</Label>
            <div className="grid grid-cols-3 gap-2">
              {status.all_engines.map((engine) => {
                const isOverride = status.manual_override_engine === engine;
                const isManualOnly = status.manual_only_engines.includes(engine);

                return (
                  <Button
                    key={engine}
                    variant={isOverride ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setManualOverride(isOverride ? null : engine)}
                    disabled={loading}
                    className="relative"
                  >
                    <div className={cn(
                      "w-2 h-2 rounded-full mr-2",
                      ENGINE_COLORS[engine] || 'bg-gray-400'
                    )} />
                    {ENGINE_LABELS[engine] || engine}
                    {isManualOnly && (
                      <Badge variant="secondary" className="ml-2 text-xs">M</Badge>
                    )}
                  </Button>
                );
              })}
              {status.manual_override_engine && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setManualOverride(null)}
                  disabled={loading}
                  className="col-span-3"
                >
                  Clear Override
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Badge "M" = Manual-only engine (not auto-preferred)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Current Router Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Current Router Status
          </CardTitle>
          <CardDescription>
            Real-time routing configuration and recent decision
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-sm text-muted-foreground">Routing Mode</Label>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={status.routing_mode === 'auto_by_regime' ? 'default' : 'secondary'}>
                  {status.routing_mode === 'auto_by_regime' ? 'Auto-by-Regime' : 'Manual'}
                </Badge>
              </div>
            </div>

            <div>
              <Label className="text-sm text-muted-foreground">Manual Override</Label>
              <div className="mt-1">
                {status.manual_override_engine ? (
                  <Badge className={cn("text-white", ENGINE_COLORS[status.manual_override_engine])}>
                    {ENGINE_LABELS[status.manual_override_engine]}
                  </Badge>
                ) : (
                  <span className="text-sm text-muted-foreground">None</span>
                )}
              </div>
            </div>

            <div>
              <Label className="text-sm text-muted-foreground">Auto-Eligible Engines</Label>
              <div className="flex gap-1 mt-1 flex-wrap">
                {status.auto_eligible_engines.map((engine) => (
                  <Badge key={engine} variant="outline" className="text-xs">
                    {ENGINE_LABELS[engine]}
                  </Badge>
                ))}
              </div>
            </div>

            <div>
              <Label className="text-sm text-muted-foreground">Manual-Only Engines</Label>
              <div className="flex gap-1 mt-1 flex-wrap">
                {status.manual_only_engines.map((engine) => (
                  <Badge key={engine} variant="secondary" className="text-xs">
                    {ENGINE_LABELS[engine]}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {/* Test Routing Decision */}
          <div className="border-t pt-4">
            <Label className="text-sm font-medium mb-2 block">Test Routing Decision</Label>
            <div className="flex gap-2">
              <select
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                value={testRegime}
                onChange={(e) => setTestRegime(e.target.value)}
              >
                {mapping && Object.keys(mapping).map((regime) => (
                  <option key={regime} value={regime}>
                    {regime}
                  </option>
                ))}
              </select>
              <Button onClick={testRoutingDecision} disabled={loading}>
                <Zap className="h-4 w-4 mr-2" />
                Test
              </Button>
            </div>
          </div>

          {/* Decision Result */}
          {decision && (
            <Alert className="mt-4">
              <DecisionSourceIcon className={cn("h-4 w-4", decisionSourceInfo?.color)} />
              <AlertDescription>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">Selected Engine:</span>
                    <Badge className={cn("text-white", ENGINE_COLORS[decision.selected_engine])}>
                      {ENGINE_LABELS[decision.selected_engine]}
                    </Badge>
                    <Badge variant="outline">
                      {decisionSourceInfo?.label}
                    </Badge>
                    {decision.fallback_used && (
                      <Badge variant="secondary">Fallback Rule</Badge>
                    )}
                  </div>
                  <div>
                    <span className="text-sm font-medium">Reason: </span>
                    <span className="text-sm text-muted-foreground">{decision.decision_reason}</span>
                  </div>
                  <div>
                    <span className="text-sm font-medium">Ranking: </span>
                    <span className="text-sm text-muted-foreground">
                      {decision.ranking.map(e => ENGINE_LABELS[e]).join(' → ')}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Last updated: {formatTimestamp(decision.timestamp)}
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Regime-to-Engine Mapping */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Regime-to-Engine Mapping
          </CardTitle>
          <CardDescription>
            Which engine is preferred for each market regime
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mapping ? (
            <div className="space-y-2">
              {Object.entries(mapping)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([regime, info]) => (
                  <div
                    key={regime}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="font-medium">{regime}</div>
                      <div className="text-xs text-muted-foreground mt-1">{info.notes}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={cn("text-white", ENGINE_COLORS[info.preferred_engine])}>
                        {ENGINE_LABELS[info.preferred_engine]}
                      </Badge>
                      <Badge variant={
                        info.source === 'comparison_results' ? 'default' :
                        info.source === 'low_confidence_data' ? 'destructive' :
                        'secondary'
                      }>
                        {info.source === 'comparison_results' ? '📊 DATA' :
                         info.source === 'low_confidence_data' ? '⚠ LOW DATA' :
                         '📋 RULE'}
                      </Badge>
                      <span className="text-xs text-muted-foreground min-w-[90px] text-right">
                        {(info.sample_size || 0) > 0 ? `${info.sample_size} samples` : 'no data'}
                      </span>
                      <span className="text-xs text-muted-foreground min-w-[60px] text-right">
                        {(info.confidence * 100).toFixed(0)}% conf
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Alert */}
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <div className="space-y-1">
            <p className="font-semibold">Routing Logic (Phase 4.5 - Statistical Confidence)</p>
            <p className="text-sm text-muted-foreground">
              Router uses comparison data when statistically sufficient (≥20 samples),
              warns on low-confidence data (&lt;20 samples), and falls back to rules when no data exists.
            </p>
            <ul className="text-xs text-muted-foreground list-disc list-inside mt-2">
              <li>📊 DATA: Statistically sufficient backtest comparisons (high confidence)</li>
              <li>⚠ LOW DATA: Comparison data exists but insufficient samples (use with caution)</li>
              <li>📋 RULE: No comparison data, using regime-based fallback rules</li>
            </ul>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
}
