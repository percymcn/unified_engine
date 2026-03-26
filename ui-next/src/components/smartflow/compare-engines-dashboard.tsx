'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Play, AlertTriangle, TrendingUp, TrendingDown, Trophy } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface ComparisonConfig {
  ticker: string;
  days: number;
  initial_capital: number;
  engines: string[];
}

interface LeaderboardEntry {
  rank: number;
  engine: string;
  total_return_pct: number;
  net_profit: number;
  sharpe_ratio: number;
  win_rate: number;
  max_drawdown_pct: number;
  profit_factor: number;
  total_trades: number;
  avg_trade: number;
  avg_holding_time_hours: number;
}

interface EngineMetadata {
  requested_engine_type: string;
  actual_execution_mode: string;
  unified_fallback_used: boolean;
  routing_status: string;
  notes: string;
}

interface ComparisonResults {
  comparison_id: string;
  timestamp: string;
  ticker: string;
  start_date: string;
  end_date: string;
  engines_compared: string[];
  leaderboard: LeaderboardEntry[];
  engine_metadata: Record<string, EngineMetadata>;
  warnings: string[];
}

const ENGINE_OPTIONS = [
  { value: 'unified', label: 'Unified', color: 'bg-gray-500' },
  { value: 'flow', label: 'Flow Engine', color: 'bg-blue-500' },
  { value: 'ai', label: 'AI Engine', color: 'bg-purple-500' },
  { value: 'deterministic', label: 'Deterministic', color: 'bg-emerald-500' },
  { value: 'quick', label: 'Quick Mode', color: 'bg-amber-500' },
];

export function CompareEnginesDashboard() {
  const [config, setConfig] = useState<ComparisonConfig>({
    ticker: 'MES',
    days: 90,
    initial_capital: 25000,
    engines: ['unified', 'deterministic'],
  });
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ComparisonResults | null>(null);
  const { toast } = useToast();

  const toggleEngine = (engine: string) => {
    setConfig((prev) => {
      const engines = prev.engines.includes(engine)
        ? prev.engines.filter((e) => e !== engine)
        : [...prev.engines, engine];
      return { ...prev, engines };
    });
  };

  const runComparison = async () => {
    if (config.engines.length < 2) {
      toast({
        title: 'Invalid selection',
        description: 'Please select at least 2 engines to compare',
        variant: 'destructive',
      });
      return;
    }

    setRunning(true);
    try {
      const response = await fetch('/api/v1/smartflow/backtest/compare/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(config),
      });

      if (response.ok) {
        const data = await response.json();
        setResults(data);
        toast({
          title: 'Comparison complete',
          description: `Compared ${data.engines_compared.length} engines successfully`,
        });
      } else {
        const error = await response.json();
        toast({
          title: 'Comparison failed',
          description: error.detail || 'An error occurred',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Comparison error:', error);
      toast({
        title: 'Comparison failed',
        description: 'Failed to run comparison',
        variant: 'destructive',
      });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <Card className="border-2 border-indigo-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Compare Engines
          </CardTitle>
          <CardDescription>
            Run multiple engines side-by-side under identical market conditions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="comp_ticker">Ticker</Label>
              <Input
                id="comp_ticker"
                value={config.ticker}
                onChange={(e) => setConfig({ ...config, ticker: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="comp_days">Days</Label>
              <Input
                id="comp_days"
                type="number"
                value={config.days}
                onChange={(e) => setConfig({ ...config, days: parseInt(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="comp_capital">Capital ($)</Label>
              <Input
                id="comp_capital"
                type="number"
                value={config.initial_capital}
                onChange={(e) => setConfig({ ...config, initial_capital: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Select Engines (min 2, max 4)</Label>
            <div className="grid grid-cols-2 gap-3">
              {ENGINE_OPTIONS.map((engine) => (
                <div key={engine.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`engine_${engine.value}`}
                    checked={config.engines.includes(engine.value)}
                    onCheckedChange={() => toggleEngine(engine.value)}
                  />
                  <label
                    htmlFor={`engine_${engine.value}`}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
                  >
                    <div className={cn('w-3 h-3 rounded-full', engine.color)} />
                    {engine.label}
                  </label>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Selected: {config.engines.length} engine(s)
            </p>
          </div>

          <Button onClick={runComparison} disabled={running || config.engines.length < 2} className="w-full" size="lg">
            {running ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Running Comparison...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Comparison
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Warnings (Phase 2B Honesty) */}
      {results && results.warnings.length > 0 && (
        <Alert variant="default" className="border-yellow-500/50 bg-yellow-500/10">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <div className="font-semibold mb-2">Execution Honesty Notice:</div>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {results.warnings.map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Leaderboard */}
      {results && results.leaderboard.length > 0 && (
        <Card className="border-2 border-yellow-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5 text-yellow-500" />
              Performance Leaderboard
            </CardTitle>
            <CardDescription>
              {results.start_date} to {results.end_date} | {results.ticker}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {results.leaderboard.map((entry) => {
                const engineMeta = results.engine_metadata[entry.engine];
                const engineOption = ENGINE_OPTIONS.find((e) => e.value === entry.engine);

                return (
                  <div
                    key={entry.engine}
                    className={cn(
                      "flex items-center justify-between p-4 rounded-lg border",
                      entry.rank === 1 && "border-yellow-500 bg-yellow-500/5"
                    )}
                  >
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "flex items-center justify-center w-8 h-8 rounded-full font-bold",
                        entry.rank === 1 ? "bg-yellow-500 text-white" :
                        entry.rank === 2 ? "bg-gray-400 text-white" :
                        entry.rank === 3 ? "bg-orange-600 text-white" :
                        "bg-gray-200 text-gray-700"
                      )}>
                        {entry.rank}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          {engineOption && (
                            <div className={cn('w-3 h-3 rounded-full', engineOption.color)} />
                          )}
                          <span className="font-semibold">{entry.engine}</span>
                          {engineMeta?.unified_fallback_used && (
                            <Badge variant="outline" className="text-xs">Fallback</Badge>
                          )}
                        </div>
                        {engineMeta && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {engineMeta.notes}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground">Return</div>
                        <div className={cn(
                          "font-semibold",
                          entry.total_return_pct > 0 ? "text-green-500" : "text-red-500"
                        )}>
                          {entry.total_return_pct > 0 ? '+' : ''}{entry.total_return_pct.toFixed(2)}%
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground">Sharpe</div>
                        <div className="font-semibold">{entry.sharpe_ratio.toFixed(2)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground">Win Rate</div>
                        <div className="font-semibold">{entry.win_rate.toFixed(1)}%</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-muted-foreground">Max DD</div>
                        <div className="font-semibold text-red-500">-{entry.max_drawdown_pct.toFixed(2)}%</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed Comparison Table */}
      {results && results.leaderboard.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Detailed Metrics</CardTitle>
            <CardDescription>Complete performance breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Engine</th>
                    <th className="text-right p-2">P&L</th>
                    <th className="text-right p-2">PF</th>
                    <th className="text-right p-2">Trades</th>
                    <th className="text-right p-2">Avg Trade</th>
                    <th className="text-right p-2">Avg Hold</th>
                  </tr>
                </thead>
                <tbody>
                  {results.leaderboard.map((entry) => (
                    <tr key={entry.engine} className="border-b last:border-0">
                      <td className="p-2">
                        <div className="flex items-center gap-2">
                          {ENGINE_OPTIONS.find((e) => e.value === entry.engine) && (
                            <div className={cn(
                              'w-2 h-2 rounded-full',
                              ENGINE_OPTIONS.find((e) => e.value === entry.engine)!.color
                            )} />
                          )}
                          {entry.engine}
                        </div>
                      </td>
                      <td className={cn(
                        "text-right p-2 font-medium",
                        entry.net_profit > 0 ? "text-green-500" : "text-red-500"
                      )}>
                        ${entry.net_profit.toFixed(2)}
                      </td>
                      <td className="text-right p-2">{entry.profit_factor.toFixed(2)}</td>
                      <td className="text-right p-2">{entry.total_trades}</td>
                      <td className={cn(
                        "text-right p-2",
                        entry.avg_trade > 0 ? "text-green-500" : "text-red-500"
                      )}>
                        ${entry.avg_trade.toFixed(2)}
                      </td>
                      <td className="text-right p-2">{entry.avg_holding_time_hours.toFixed(1)}h</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!results && !running && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p className="mb-4">No comparison results yet.</p>
            <p className="text-sm">
              Select 2-4 engines above and click "Run Comparison" to see performance side-by-side.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
