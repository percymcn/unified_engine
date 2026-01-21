'use client';

import { useEffect, useState, useCallback } from 'react';
import { ArrowRightLeft, Plus, RefreshCw, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { SymbolAliasList } from '@/components/settings/symbol-alias-list';
import { SymbolAliasForm } from '@/components/settings/symbol-alias-form';
import { SymbolAlias, SymbolAliasGroup } from '@/types/symbol-alias';
import { getSymbolAliases } from '@/lib/api/symbol-aliases';
import { getAccounts } from '@/lib/api/accounts';

export default function SymbolMappingPage() {
  const [groups, setGroups] = useState<SymbolAliasGroup[]>([]);
  const [connectedBrokers, setConnectedBrokers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingAlias, setEditingAlias] = useState<SymbolAlias | undefined>();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch both aliases and accounts in parallel
      const [aliasesResponse, accountsResponse] = await Promise.all([
        getSymbolAliases(),
        getAccounts(),
      ]);

      setGroups(aliasesResponse);

      // Extract unique broker types from accounts
      const brokers = new Set<string>();
      if (accountsResponse && accountsResponse.accounts) {
        accountsResponse.accounts.forEach((acc: { broker: string }) => {
          brokers.add(acc.broker);
        });
      }
      setConnectedBrokers(Array.from(brokers).sort());
    } catch (err) {
      console.error('Failed to load symbol mappings:', err);
      setError(err instanceof Error ? err.message : 'Failed to load symbol mappings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleEdit = (alias: SymbolAlias) => {
    setEditingAlias(alias);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingAlias(undefined);
  };

  const handleFormSuccess = () => {
    fetchData();
  };

  const handleAddNew = () => {
    setEditingAlias(undefined);
    setShowForm(true);
  };

  // Calculate total aliases
  const totalAliases = groups.reduce((sum, g) => sum + g.aliases.length, 0);
  const autoDetectedCount = groups.reduce(
    (sum, g) => sum + g.aliases.filter((a) => a.isAutoDetected).length,
    0
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Symbol Mapping</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <ArrowRightLeft className="h-7 w-7 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Symbol Mapping</h1>
          </div>
          <p className="text-muted-foreground mt-1">
            Configure how TradingView symbols map to your broker&apos;s format
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={fetchData} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={handleAddNew} disabled={connectedBrokers.length === 0}>
            <Plus className="h-4 w-4 mr-2" />
            Add Mapping
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={fetchData} className="ml-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Explanation Card */}
      <Card className="bg-muted/50">
        <CardContent className="py-4">
          <div className="flex gap-3">
            <Info className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
            <div className="space-y-1 text-sm">
              <p>
                <strong>Symbol mapping</strong> translates TradingView symbols to your broker&apos;s format.
              </p>
              <p className="text-muted-foreground">
                For example, when you send a signal for &quot;US30&quot; from TradingView, your broker might
                expect &quot;US30.pro&quot; (TradeLocker) or &quot;YM&quot; (Tradovate). Auto-detected mappings are
                discovered when you test your broker connection.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Summary */}
      {totalAliases > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold">{totalAliases}</div>
              <div className="text-sm text-muted-foreground">Total Mappings</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold">{groups.length}</div>
              <div className="text-sm text-muted-foreground">Brokers</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold">{autoDetectedCount}</div>
              <div className="text-sm text-muted-foreground">Auto-detected</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold">{totalAliases - autoDetectedCount}</div>
              <div className="text-sm text-muted-foreground">Custom</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* No Brokers Warning */}
      {connectedBrokers.length === 0 && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>No broker accounts connected</AlertTitle>
          <AlertDescription>
            Connect a broker account in{' '}
            <a href="/dashboard/settings/accounts" className="underline font-medium">
              Settings &rarr; Accounts
            </a>{' '}
            to start configuring symbol mappings.
          </AlertDescription>
        </Alert>
      )}

      {/* Alias List */}
      <SymbolAliasList groups={groups} onEdit={handleEdit} onRefresh={fetchData} />

      {/* Add/Edit Form Dialog */}
      <SymbolAliasForm
        open={showForm}
        onClose={handleCloseForm}
        onSuccess={handleFormSuccess}
        alias={editingAlias}
        connectedBrokers={connectedBrokers}
      />
    </div>
  );
}
