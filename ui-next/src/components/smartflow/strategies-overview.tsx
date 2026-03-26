'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, RefreshCw, CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react';

interface StrategyResponse {
  strategy_id: string;
  strategy_type: string;
  version: string;
  status: string;
  parent_strategy_id?: string;
  sharpe_ratio?: number;
  win_rate?: number;
  max_drawdown?: number;
  total_trades?: number;
  created_at?: string;
  evaluated_at?: string;
  approved_at?: string;
  approved_for_router_at?: string;
  approved_for_forward_test_at?: string;
  forward_test_gate_passed_at?: string;
}

interface StrategyListResponse {
  strategies: StrategyResponse[];
  total: number;
}

const STATUS_COLORS: Record<string, string> = {
  'built_in': 'bg-blue-500',
  'candidate': 'bg-yellow-500',
  'approved_for_router': 'bg-green-500',
  'approved_for_forward_test': 'bg-amber-500',
  'forward_testing': 'bg-purple-500',
  'active': 'bg-emerald-500',
  'rejected': 'bg-red-500',
  'retired': 'bg-gray-500',
  'archived': 'bg-gray-400',
};

const STATUS_LABELS: Record<string, string> = {
  'built_in': 'Built-In',
  'candidate': 'Candidate',
  'approved_for_router': 'Router-Approved',
  'approved_for_forward_test': 'FT-Approved',
  'forward_testing': 'Forward Testing',
  'active': 'Active',
  'rejected': 'Rejected',
  'retired': 'Retired',
  'archived': 'Archived',
};

const formatWinRate = (value?: number) => {
  if (value === null || value === undefined) {
    return '-';
  }
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
};

export function StrategiesOverview() {
  const [strategies, setStrategies] = useState<StrategyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const loadStrategies = async () => {
    try {
      const response = await fetch('/api/strategies', {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: StrategyListResponse = await response.json();
      setStrategies(data.strategies || []);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to load strategies:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStrategies();
  }, []);

  const handleRefresh = () => {
    setLoading(true);
    loadStrategies();
  };

  // Calculate status breakdown
  const statusBreakdown = strategies.reduce((acc, s) => {
    acc[s.status] = (acc[s.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Separate by categories
  const routerEligible = strategies.filter(s =>
    ['built_in', 'approved_for_router', 'active'].includes(s.status)
  );
  const candidates = strategies.filter(s => s.status === 'candidate');
  const inTesting = strategies.filter(s =>
    ['approved_for_forward_test', 'forward_testing'].includes(s.status)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Strategy Registry</h2>
          <p className="text-muted-foreground">
            Manage SmartFlow strategies, variants, and lifecycle
          </p>
        </div>
        <Button onClick={handleRefresh} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Strategies
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{strategies.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Router-Eligible
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{routerEligible.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {routerEligible.filter(s => s.parent_strategy_id).length} variants
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              In Testing
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-600">{inTesting.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Forward test pipeline
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Candidates
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">{candidates.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Pending evaluation
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Router-Eligible Strategies */}
      <Card>
        <CardHeader>
          <CardTitle>Router-Eligible Strategies</CardTitle>
          <CardDescription>
            Strategies approved for router selection (built-in, approved_for_router, active)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {routerEligible.length === 0 ? (
            <p className="text-muted-foreground text-sm">No router-eligible strategies found</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Strategy ID</TableHead>
                  <TableHead>Engine</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Sharpe</TableHead>
                  <TableHead className="text-right">Win Rate</TableHead>
                  <TableHead className="text-right">Trades</TableHead>
                  <TableHead>Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {routerEligible.map((strategy) => (
                  <TableRow key={strategy.strategy_id}>
                    <TableCell className="font-mono text-sm">
                      {strategy.strategy_id}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{strategy.strategy_type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[strategy.status]}>
                        {STATUS_LABELS[strategy.status] || strategy.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {strategy.sharpe_ratio?.toFixed(2) || '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatWinRate(strategy.win_rate)}
                    </TableCell>
                    <TableCell className="text-right">
                      {strategy.total_trades || '-'}
                    </TableCell>
                    <TableCell>
                      {strategy.parent_strategy_id ? (
                        <Badge variant="secondary" className="text-xs">
                          Variant
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          Built-In
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Candidates & Testing Pipeline */}
      {(candidates.length > 0 || inTesting.length > 0) && (
        <div className="grid md:grid-cols-2 gap-6">
          {/* Candidates */}
          {candidates.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Candidate Pipeline</CardTitle>
                <CardDescription>
                  Variants pending backtest evaluation
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {candidates.slice(0, 5).map((strategy) => (
                    <div
                      key={strategy.strategy_id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <div className="font-mono text-sm font-medium">
                          {strategy.strategy_id}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Parent: {strategy.parent_strategy_id || 'None'}
                        </div>
                      </div>
                      <Clock className="h-4 w-4 text-yellow-500" />
                    </div>
                  ))}
                  {candidates.length > 5 && (
                    <p className="text-xs text-muted-foreground text-center pt-2">
                      +{candidates.length - 5} more candidates
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* In Testing */}
          {inTesting.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Forward Test Pipeline</CardTitle>
                <CardDescription>
                  Strategies in forward testing
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {inTesting.slice(0, 5).map((strategy) => (
                    <div
                      key={strategy.strategy_id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <div className="font-mono text-sm font-medium">
                          {strategy.strategy_id}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {strategy.status === 'forward_testing' ? 'Testing...' : 'Approved for FT'}
                        </div>
                      </div>
                      {strategy.forward_test_gate_passed_at ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-purple-500" />
                      )}
                    </div>
                  ))}
                  {inTesting.length > 5 && (
                    <p className="text-xs text-muted-foreground text-center pt-2">
                      +{inTesting.length - 5} more in testing
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* All Strategies Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Strategies</CardTitle>
          <CardDescription>
            Complete strategy registry with all statuses
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Strategy ID</TableHead>
                <TableHead>Engine</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Parent</TableHead>
                <TableHead className="text-right">Sharpe</TableHead>
                <TableHead>Router</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategies.map((strategy) => {
                const isRouterEligible = ['built_in', 'approved_for_router', 'active'].includes(
                  strategy.status
                );
                return (
                  <TableRow key={strategy.strategy_id}>
                    <TableCell className="font-mono text-sm">
                      {strategy.strategy_id}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{strategy.strategy_type}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {strategy.version}
                    </TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[strategy.status]}>
                        {STATUS_LABELS[strategy.status] || strategy.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {strategy.parent_strategy_id || '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      {strategy.sharpe_ratio?.toFixed(2) || '-'}
                    </TableCell>
                    <TableCell>
                      {isRouterEligible ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-gray-400" />
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Last Update Footer */}
      {lastUpdate && (
        <p className="text-xs text-muted-foreground text-center">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
