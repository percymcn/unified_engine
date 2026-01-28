'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  TrendingDown,
  TrendingUp,
  DollarSign,
  Target,
  Shield,
  Bell,
  RefreshCw,
  Calendar,
  Clock,
  Wallet,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface PropFirmRule {
  id: string;
  name: string;
  description: string;
  limit: number;
  current: number;
  unit: string;
  status: 'safe' | 'warning' | 'danger' | 'breached';
  category: 'drawdown' | 'profit' | 'trading' | 'time';
}

interface PayoutInfo {
  nextPayoutDate: string;
  eligibleAmount: number;
  totalPaidOut: number;
  pendingPayout: number;
  payoutHistory: Array<{
    date: string;
    amount: number;
    status: string;
  }>;
}

interface ComplianceData {
  accountId: number;
  accountName: string;
  broker: string;
  phase: string;
  startDate: string;
  rules: PropFirmRule[];
  payout: PayoutInfo;
  overallStatus: 'compliant' | 'at_risk' | 'breached';
}

export function PropFirmCompliance() {
  const [accounts, setAccounts] = useState<ComplianceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAccount, setSelectedAccount] = useState<number | null>(null);
  const [alertsEnabled, setAlertsEnabled] = useState(true);

  const fetchComplianceData = useCallback(async () => {
    try {
      const response = await fetch('/api/dashboard/prop-firm/compliance', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setAccounts(data.accounts || []);
        if (data.accounts?.length > 0 && !selectedAccount) {
          setSelectedAccount(data.accounts[0].accountId);
        }
      }
    } catch (error) {
      console.error('Error fetching compliance data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedAccount]);

  useEffect(() => {
    fetchComplianceData();
    // Poll every 30 seconds for real-time updates
    const interval = setInterval(fetchComplianceData, 30000);
    return () => clearInterval(interval);
  }, [fetchComplianceData]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'safe':
      case 'compliant':
        return 'text-emerald-500';
      case 'warning':
      case 'at_risk':
        return 'text-amber-500';
      case 'danger':
      case 'breached':
        return 'text-red-500';
      default:
        return 'text-muted-foreground';
    }
  };

  const getProgressColor = (status: string) => {
    switch (status) {
      case 'safe':
        return 'bg-emerald-500';
      case 'warning':
        return 'bg-amber-500';
      case 'danger':
      case 'breached':
        return 'bg-red-500';
      default:
        return 'bg-primary';
    }
  };

  const selectedData = accounts.find((a) => a.accountId === selectedAccount);

  if (loading) {
    return (
      <Card className="cyber-card">
        <CardContent className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (accounts.length === 0) {
    return (
      <Card className="cyber-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Prop Firm Compliance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>No Prop Firm Accounts</AlertTitle>
            <AlertDescription>
              Connect a prop firm account (FTMO, TFT, etc.) to enable compliance tracking.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with account selector */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            Prop Firm Compliance
          </h2>
          <p className="text-muted-foreground">
            Real-time drawdown monitoring and payout tracking
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAlertsEnabled(!alertsEnabled)}
            className={cn(alertsEnabled && 'border-primary text-primary')}
          >
            <Bell className={cn('h-4 w-4 mr-2', alertsEnabled && 'text-primary')} />
            {alertsEnabled ? 'Alerts On' : 'Alerts Off'}
          </Button>
          <Button variant="outline" size="sm" onClick={fetchComplianceData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Account tabs */}
      {accounts.length > 1 && (
        <Tabs value={String(selectedAccount)} onValueChange={(v) => setSelectedAccount(Number(v))}>
          <TabsList>
            {accounts.map((account) => (
              <TabsTrigger key={account.accountId} value={String(account.accountId)}>
                <span className={cn('mr-2', getStatusColor(account.overallStatus))}>
                  {account.overallStatus === 'compliant' ? (
                    <CheckCircle2 className="h-3 w-3 inline" />
                  ) : account.overallStatus === 'at_risk' ? (
                    <AlertTriangle className="h-3 w-3 inline" />
                  ) : (
                    <XCircle className="h-3 w-3 inline" />
                  )}
                </span>
                {account.accountName}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      )}

      {selectedData && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main compliance rules */}
          <div className="lg:col-span-2 space-y-4">
            {/* Overall status card */}
            <Card className={cn(
              'cyber-card border-l-4',
              selectedData.overallStatus === 'compliant' && 'border-l-emerald-500',
              selectedData.overallStatus === 'at_risk' && 'border-l-amber-500',
              selectedData.overallStatus === 'breached' && 'border-l-red-500'
            )}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">{selectedData.accountName}</CardTitle>
                    <CardDescription>
                      {selectedData.broker} - {selectedData.phase}
                    </CardDescription>
                  </div>
                  <Badge
                    variant={selectedData.overallStatus === 'compliant' ? 'default' : 'destructive'}
                    className={cn(
                      selectedData.overallStatus === 'compliant' && 'bg-emerald-500',
                      selectedData.overallStatus === 'at_risk' && 'bg-amber-500'
                    )}
                  >
                    {selectedData.overallStatus.toUpperCase()}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    Started: {new Date(selectedData.startDate).toLocaleDateString()}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Compliance rules grid */}
            <div className="grid gap-4 md:grid-cols-2">
              {selectedData.rules.map((rule) => (
                <Card key={rule.id} className="cyber-card">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium">{rule.name}</CardTitle>
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-xs',
                          rule.status === 'safe' && 'border-emerald-500 text-emerald-500',
                          rule.status === 'warning' && 'border-amber-500 text-amber-500',
                          (rule.status === 'danger' || rule.status === 'breached') &&
                            'border-red-500 text-red-500'
                        )}
                      >
                        {rule.status === 'safe' && <CheckCircle2 className="h-3 w-3 mr-1" />}
                        {rule.status === 'warning' && <AlertTriangle className="h-3 w-3 mr-1" />}
                        {(rule.status === 'danger' || rule.status === 'breached') && (
                          <XCircle className="h-3 w-3 mr-1" />
                        )}
                        {rule.status.toUpperCase()}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs">{rule.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">
                          {rule.category === 'drawdown' ? (
                            <TrendingDown className="h-4 w-4 inline mr-1" />
                          ) : rule.category === 'profit' ? (
                            <TrendingUp className="h-4 w-4 inline mr-1" />
                          ) : (
                            <Target className="h-4 w-4 inline mr-1" />
                          )}
                          Current
                        </span>
                        <span className={getStatusColor(rule.status)}>
                          {rule.current.toFixed(2)}{rule.unit}
                        </span>
                      </div>
                      <Progress
                        value={Math.min((rule.current / rule.limit) * 100, 100)}
                        className={cn('h-2', getProgressColor(rule.status))}
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>0{rule.unit}</span>
                        <span>Limit: {rule.limit}{rule.unit}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Payout tracker sidebar */}
          <div className="space-y-4">
            <Card className="cyber-card">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Wallet className="h-5 w-5 text-primary" />
                  Payout Tracker
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Next Payout</span>
                    <span className="flex items-center gap-1 text-sm">
                      <Clock className="h-4 w-4" />
                      {new Date(selectedData.payout.nextPayoutDate).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Eligible Amount</span>
                    <span className="text-lg font-bold text-emerald-500">
                      ${selectedData.payout.eligibleAmount.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Pending</span>
                    <span className="text-amber-500">
                      ${selectedData.payout.pendingPayout.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t">
                    <span className="text-sm text-muted-foreground">Total Paid Out</span>
                    <span className="font-medium">
                      ${selectedData.payout.totalPaidOut.toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Payout history */}
                {selectedData.payout.payoutHistory.length > 0 && (
                  <div className="pt-4 border-t">
                    <h4 className="text-sm font-medium mb-2">Recent Payouts</h4>
                    <div className="space-y-2">
                      {selectedData.payout.payoutHistory.slice(0, 3).map((payout, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span className="text-muted-foreground">
                            {new Date(payout.date).toLocaleDateString()}
                          </span>
                          <span className={cn(
                            payout.status === 'completed' ? 'text-emerald-500' : 'text-amber-500'
                          )}>
                            ${payout.amount.toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick alerts card */}
            {alertsEnabled && (
              <Card className="cyber-card border-amber-500/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Bell className="h-4 w-4 text-amber-500" />
                    Alert Thresholds
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Warning at</span>
                    <span>70% of limit</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Danger at</span>
                    <span>90% of limit</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Auto-flatten</span>
                    <Badge variant="outline" className="text-xs">Enabled</Badge>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
