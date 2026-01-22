'use client';

import { useEffect, useState, useCallback } from 'react';
import { Loader2, RefreshCw, CheckCircle2, AlertCircle, Zap, ZapOff } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { BrokerType, BROKER_DISPLAY_NAMES } from '@/types/account';

/**
 * Available broker account info from API
 */
interface BrokerAccountInfo {
  id: string;
  name: string;
  account_type: string;
  balance: number | null;
  equity: number | null;
  currency: string | null;
  server: string | null;
  login: string | null;
  broker_type: string;
  is_active: boolean;
  is_stored: boolean;
  is_selected: boolean;
  stored_account_id: number | null;
}

interface AvailableAccountsResponse {
  broker_type: string;
  accounts: BrokerAccountInfo[];
  total: number;
  message?: string;
}

interface AccountSelectorProps {
  /** Broker type to fetch accounts for */
  brokerType: BrokerType;
  /** Optional callback when selection changes */
  onSelectionChange?: (accountId: number, selected: boolean) => void;
  /** Show header with title */
  showHeader?: boolean;
  /** Compact mode for embedding */
  compact?: boolean;
}

/**
 * Account selector component with checkbox list.
 * Allows users to select which broker accounts should receive trading signals.
 */
export function AccountSelector({
  brokerType,
  onSelectionChange,
  showHeader = true,
  compact = false,
}: AccountSelectorProps) {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<BrokerAccountInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<Record<number, boolean>>({});
  const [syncing, setSyncing] = useState(false);

  // Fetch available accounts
  const fetchAccounts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/accounts/available/${brokerType}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to fetch accounts');
      }

      const data: AvailableAccountsResponse = await response.json();
      setAccounts(data.accounts || []);

      // Show message if no accounts or special message from backend
      if (data.message && data.accounts.length === 0) {
        setError(data.message);
      }
    } catch (err) {
      console.error('Error fetching available accounts:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch accounts');
    } finally {
      setLoading(false);
    }
  }, [brokerType]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // Toggle account selection
  const handleToggleSelection = async (account: BrokerAccountInfo) => {
    if (!account.stored_account_id) {
      toast({
        title: 'Account not stored',
        description: 'This account needs to be added before it can be selected.',
        variant: 'destructive',
      });
      return;
    }

    const accountId = account.stored_account_id;
    const newSelected = !account.is_selected;

    setUpdating(prev => ({ ...prev, [accountId]: true }));

    try {
      const response = await fetch(`/api/accounts/${accountId}/select`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ selected: newSelected }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to update selection');
      }

      // Update local state
      setAccounts(prev =>
        prev.map(a =>
          a.stored_account_id === accountId
            ? { ...a, is_selected: newSelected }
            : a
        )
      );

      // Notify parent
      onSelectionChange?.(accountId, newSelected);

      toast({
        title: newSelected ? 'Account Selected' : 'Account Deselected',
        description: newSelected
          ? `${account.name} will now receive trading signals.`
          : `${account.name} will no longer receive signals.`,
      });
    } catch (err) {
      console.error('Error updating account selection:', err);
      toast({
        title: 'Selection Failed',
        description: err instanceof Error ? err.message : 'Failed to update selection',
        variant: 'destructive',
      });
    } finally {
      setUpdating(prev => ({ ...prev, [accountId]: false }));
    }
  };

  // Select/Deselect all
  const handleSelectAll = async (selectAll: boolean) => {
    const storedAccounts = accounts.filter(a => a.stored_account_id);
    const accountsToUpdate = storedAccounts.filter(a => a.is_selected !== selectAll);

    if (accountsToUpdate.length === 0) return;

    // Update all accounts
    for (const account of accountsToUpdate) {
      await handleToggleSelection(account);
    }
  };

  // Sync accounts from broker
  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await fetch('/api/accounts/sync-all', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to sync accounts');
      }

      const data = await response.json();

      toast({
        title: 'Sync Complete',
        description: data.message || 'Accounts synced successfully.',
      });

      // Refresh the account list
      await fetchAccounts();
    } catch (err) {
      console.error('Error syncing accounts:', err);
      toast({
        title: 'Sync Failed',
        description: 'Failed to sync accounts from broker.',
        variant: 'destructive',
      });
    } finally {
      setSyncing(false);
    }
  };

  // Group accounts by type
  const groupedAccounts = accounts.reduce((groups, account) => {
    const type = account.account_type || 'other';
    if (!groups[type]) {
      groups[type] = [];
    }
    groups[type].push(account);
    return groups;
  }, {} as Record<string, BrokerAccountInfo[]>);

  // Selection counts
  const selectedCount = accounts.filter(a => a.is_selected).length;
  const totalStoredCount = accounts.filter(a => a.stored_account_id).length;

  // Account type display names
  const accountTypeNames: Record<string, string> = {
    live: 'Live Accounts',
    demo: 'Demo Accounts',
    evaluation: 'Evaluation Accounts',
    express: 'Express Accounts',
    funded: 'Funded Accounts',
    other: 'Other Accounts',
  };

  // Format currency
  const formatCurrency = (value: number | null, currency: string | null) => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  // Loading skeleton
  if (loading) {
    return (
      <Card className={cn(compact && 'border-0 shadow-none')}>
        {showHeader && (
          <CardHeader className={cn(compact && 'px-0 pt-0')}>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </CardHeader>
        )}
        <CardContent className={cn(compact && 'px-0 pb-0')}>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex items-center gap-3 p-3 border rounded-lg">
                <Skeleton className="h-4 w-4 rounded" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error && accounts.length === 0) {
    return (
      <Card className={cn(compact && 'border-0 shadow-none')}>
        {showHeader && (
          <CardHeader className={cn(compact && 'px-0 pt-0')}>
            <CardTitle className="text-lg">Select Accounts</CardTitle>
          </CardHeader>
        )}
        <CardContent className={cn(compact && 'px-0 pb-0')}>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // Empty state
  if (accounts.length === 0) {
    return (
      <Card className={cn(compact && 'border-0 shadow-none')}>
        {showHeader && (
          <CardHeader className={cn(compact && 'px-0 pt-0')}>
            <CardTitle className="text-lg">Select Accounts</CardTitle>
          </CardHeader>
        )}
        <CardContent className={cn(compact && 'px-0 pb-0')}>
          <div className="text-center py-8 text-muted-foreground">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No accounts found.</p>
            <p className="text-sm mt-1">Connect a {BROKER_DISPLAY_NAMES[brokerType]} account first.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <Card className={cn(compact && 'border-0 shadow-none')}>
        {showHeader && (
          <CardHeader className={cn(compact && 'px-0 pt-0')}>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  Select Accounts
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <AlertCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent side="right" className="max-w-xs">
                      <p>Selected accounts will receive trading signals. Deselect accounts you want to exclude from signal routing.</p>
                    </TooltipContent>
                  </Tooltip>
                </CardTitle>
                <CardDescription className="mt-1">
                  {selectedCount} of {totalStoredCount} accounts selected
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSync}
                disabled={syncing}
              >
                {syncing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                <span className="ml-2 hidden sm:inline">Sync</span>
              </Button>
            </div>
          </CardHeader>
        )}

        <CardContent className={cn(compact && 'px-0 pb-0')}>
          {/* Select All / Deselect All */}
          <div className="flex gap-2 mb-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSelectAll(true)}
              disabled={selectedCount === totalStoredCount}
            >
              <CheckCircle2 className="h-4 w-4 mr-1" />
              Select All
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSelectAll(false)}
              disabled={selectedCount === 0}
            >
              Deselect All
            </Button>
          </div>

          {/* Account list grouped by type */}
          <div className="space-y-6">
            {Object.entries(groupedAccounts).map(([type, typeAccounts]) => (
              <div key={type}>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">
                  {accountTypeNames[type] || type}
                </h4>
                <div className="space-y-2">
                  {typeAccounts.map(account => (
                    <div
                      key={account.id}
                      className={cn(
                        'flex items-center gap-3 p-3 border rounded-lg transition-colors',
                        !account.is_stored && 'opacity-50 bg-muted/50',
                        account.is_selected && account.is_stored && 'border-primary/50 bg-primary/5',
                        !account.is_selected && account.is_stored && 'hover:border-border/80'
                      )}
                    >
                      {/* Checkbox */}
                      <Checkbox
                        id={`account-${account.id}`}
                        checked={account.is_selected}
                        onCheckedChange={() => handleToggleSelection(account)}
                        disabled={!account.is_stored || updating[account.stored_account_id || 0]}
                        className="shrink-0"
                      />

                      {/* Account info */}
                      <div className="flex-1 min-w-0">
                        <label
                          htmlFor={`account-${account.id}`}
                          className={cn(
                            'text-sm font-medium cursor-pointer flex items-center gap-2',
                            !account.is_stored && 'cursor-not-allowed'
                          )}
                        >
                          {account.name}
                          {account.is_selected && (
                            <Zap className="h-3.5 w-3.5 text-green-500" />
                          )}
                          {!account.is_selected && account.is_stored && (
                            <ZapOff className="h-3.5 w-3.5 text-muted-foreground" />
                          )}
                        </label>
                        <div className="text-xs text-muted-foreground space-y-0.5">
                          {/* MT4/MT5 show login/server */}
                          {(account.broker_type === 'mt4' || account.broker_type === 'mt5') && (
                            <p>
                              {account.login && <span>Login: {account.login}</span>}
                              {account.login && account.server && <span> | </span>}
                              {account.server && <span>Server: {account.server}</span>}
                            </p>
                          )}
                          {/* Balance */}
                          {account.balance !== null && (
                            <p>Balance: {formatCurrency(account.balance, account.currency)}</p>
                          )}
                        </div>
                      </div>

                      {/* Status badges */}
                      <div className="flex items-center gap-2 shrink-0">
                        {updating[account.stored_account_id || 0] && (
                          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                        )}
                        {!account.is_stored && (
                          <Badge variant="secondary" className="text-xs">
                            Not added
                          </Badge>
                        )}
                        <Badge
                          variant={account.is_active ? 'default' : 'secondary'}
                          className={cn(
                            'text-xs',
                            account.is_active
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : ''
                          )}
                        >
                          {account.account_type}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
