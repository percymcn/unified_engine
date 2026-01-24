'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Loader2, ArrowLeft, Settings, Shield, GitBranch, RefreshCw, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AccountSettingsForm } from '@/components/accounts/account-settings-form';
import { Account, AccountSettings, AccountGroup, BROKER_DISPLAY_NAMES } from '@/types/account';
import { getAccountSettings, updateAccountSettings, getAccountGroups, refreshBrokerAccounts, updateAccount, DiscoveredAccount } from '@/lib/api/accounts';
import { useToast } from '@/hooks/use-toast';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';

export default function AccountSettingsPage() {
  const params = useParams();
  const { toast } = useToast();
  const accountId = Number(params.id);

  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [groups, setGroups] = useState<AccountGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [discoveredAccounts, setDiscoveredAccounts] = useState<DiscoveredAccount[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<Set<string>>(new Set());
  const [defaultAccountId, setDefaultAccountId] = useState<string>('');

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch account details and settings in parallel
      const [settingsData, groupsData, accountResponse] = await Promise.all([
        getAccountSettings(accountId),
        getAccountGroups(),
        fetch(`/api/accounts/${accountId}`).then(r => r.json()),
      ]);

      setSettings(settingsData);
      setGroups(groupsData);
      setAccount(accountResponse);
      
      // Load broker account selection if available
      if (accountResponse.enabled_broker_account_ids) {
        setSelectedAccountIds(new Set(accountResponse.enabled_broker_account_ids));
      }
      if (accountResponse.default_broker_account_id) {
        setDefaultAccountId(accountResponse.default_broker_account_id);
      }
      if (accountResponse.discovered_accounts_cache) {
        setDiscoveredAccounts(accountResponse.discovered_accounts_cache as DiscoveredAccount[]);
      }
      
      // Load broker account selection if available
      if (accountResponse.enabled_broker_account_ids) {
        setSelectedAccountIds(new Set(accountResponse.enabled_broker_account_ids));
      }
      if (accountResponse.default_broker_account_id) {
        setDefaultAccountId(accountResponse.default_broker_account_id);
      }
      if (accountResponse.discovered_accounts_cache) {
        setDiscoveredAccounts(accountResponse.discovered_accounts_cache as DiscoveredAccount[]);
      }
    } catch (err) {
      console.error('Failed to load account settings:', err);
      setError('Failed to load account settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshAccounts = async () => {
    if (!account) return;
    
    try {
      setRefreshing(true);
      const result = await refreshBrokerAccounts(account.id);
      
      if (result.accounts && result.accounts.length > 0) {
        setDiscoveredAccounts(result.accounts);
        toast({
          title: 'Accounts Refreshed',
          description: `Found ${result.accounts.length} account(s)`,
        });
      } else {
        toast({
          title: 'No Accounts Found',
          description: result.message || 'No accounts discovered',
          variant: 'default',
        });
      }
    } catch (err) {
      console.error('Failed to refresh accounts:', err);
      toast({
        title: 'Refresh Failed',
        description: err instanceof Error ? err.message : 'Failed to refresh accounts',
        variant: 'destructive',
      });
    } finally {
      setRefreshing(false);
    }
  };

  const handleAccountToggle = (accountId: string, checked: boolean) => {
    const newSelected = new Set(selectedAccountIds);
    if (checked) {
      newSelected.add(accountId);
    } else {
      newSelected.delete(accountId);
      if (defaultAccountId === accountId) {
        setDefaultAccountId('');
      }
    }
    setSelectedAccountIds(newSelected);
    
    if (!defaultAccountId && newSelected.size > 0) {
      setDefaultAccountId(Array.from(newSelected)[0]);
    }
  };

  const handleDefaultChange = (accountId: string) => {
    if (selectedAccountIds.has(accountId)) {
      setDefaultAccountId(accountId);
    }
  };

  const handleSaveAccountSelection = async () => {
    if (!account) return;
    
    try {
      setSaving(true);
      await updateAccount(account.id, {
        enabled_broker_account_ids: Array.from(selectedAccountIds),
        default_broker_account_id: defaultAccountId || undefined,
        discovered_accounts_cache: discoveredAccounts,
      });
      
      toast({
        title: 'Account Selection Saved',
        description: 'Broker account selection updated successfully',
      });
      
      // Reload account data
      await loadData();
    } catch (err) {
      console.error('Failed to save account selection:', err);
      toast({
        title: 'Save Failed',
        description: 'Failed to save account selection',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };
    try {
      setSaving(true);

      // Transform nested structure to flat update format
      const updatePayload = {
        positionSizingMode: updates.positionSizing?.mode,
        fixedLotSize: updates.positionSizing?.fixedLotSize,
        percentOfBalance: updates.positionSizing?.percentOfBalance,
        percentOfEquity: updates.positionSizing?.percentOfEquity,
        riskPercentPerTrade: updates.positionSizing?.riskPercentPerTrade,
        maxPositionSize: updates.riskLimits?.maxPositionSize,
        maxDailyLoss: updates.riskLimits?.maxDailyLoss,
        maxDailyLossPct: updates.riskLimits?.maxDailyLossPct,
        maxDrawdownPct: updates.riskLimits?.maxDrawdownPct,
        maxOpenPositions: updates.riskLimits?.maxOpenPositions,
        maxDailyTrades: updates.riskLimits?.maxDailyTrades,
        tradeCooldownSeconds: updates.riskLimits?.tradeCooldownSeconds,
        // NOTE: defaultStopLoss and defaultTakeProfit are in broker-specific units
        // (pips/points/percent). They cannot be converted to absolute prices without
        // an entry price. Backend should convert them when used with signals.
        defaultStopLoss: updates.riskLimits?.defaultStopLoss,
        defaultTakeProfit: updates.riskLimits?.defaultTakeProfit,
        groupId: updates.grouping?.groupId,
        isSignalEnabled: updates.routing?.isSignalEnabled,
        signalPriority: updates.routing?.signalPriority,
      };

      const updated = await updateAccountSettings(accountId, updatePayload);
      setSettings(updated);

      toast({
        title: 'Settings Saved',
        description: 'Account settings have been updated successfully.',
      });
    } catch (err) {
      console.error('Failed to save settings:', err);
      toast({
        title: 'Save Failed',
        description: 'Failed to save settings. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mr-2" />
        <span className="text-muted-foreground">Loading account settings...</span>
      </div>
    );
  }

  if (error || !settings) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/dashboard/settings/accounts">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Accounts
            </Link>
          </Button>
        </div>
        <Alert variant="destructive">
          <AlertDescription>
            {error || 'Failed to load account settings.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const accountName = account
    ? `${BROKER_DISPLAY_NAMES[account.broker as keyof typeof BROKER_DISPLAY_NAMES]} - ${account.account_id}`
    : `Account ${accountId}`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/dashboard/settings/accounts">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Link>
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">{accountName} Settings</h1>
        <p className="text-muted-foreground">
          Configure position sizing, risk limits, and signal routing for this account.
        </p>
      </div>

      {/* Broker Account Selection Section */}
      {account && (
        <div className="space-y-4 p-4 border rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Broker Account Selection</h2>
              <p className="text-sm text-muted-foreground">
                Manage which broker accounts are enabled and set the default account
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshAccounts}
              disabled={refreshing}
            >
              {refreshing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Refreshing...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh Accounts
                </>
              )}
            </Button>
          </div>

          {discoveredAccounts.length > 0 && (
            <div className="space-y-3">
              <div className="space-y-2">
                {discoveredAccounts.map((acc) => {
                  const accId = acc.broker_account_id || acc.id || '';
                  const displayName = acc.display_name || acc.name || accId;
                  const isSelected = selectedAccountIds.has(accId);
                  const isDefault = defaultAccountId === accId;
                  
                  return (
                    <div key={accId} className="flex items-start gap-3 p-3 border rounded-md">
                      <Checkbox
                        id={`account-${accId}`}
                        checked={isSelected}
                        onCheckedChange={(checked) =>
                          handleAccountToggle(accId, checked as boolean)
                        }
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Label
                            htmlFor={`account-${accId}`}
                            className="font-medium cursor-pointer"
                          >
                            {displayName}
                          </Label>
                          {acc.status === 'active' && (
                            <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                              Active
                            </span>
                          )}
                          {acc.status === 'inactive' && (
                            <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded">
                              Inactive
                            </span>
                          )}
                          <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                            {acc.account_type}
                          </span>
                          {isDefault && (
                            <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
                              Default
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {acc.meta?.currency || acc.currency || 'USD'} • 
                          Balance: {(acc.meta?.balance || acc.balance || 0).toFixed(2)} • 
                          Equity: {(acc.meta?.equity || acc.equity || 0).toFixed(2)}
                        </div>
                        {acc.account_number && acc.account_number !== accId && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Account #: {acc.account_number}
                          </div>
                        )}
                      </div>
                      {isSelected && (
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            id={`default-${accId}`}
                            name="defaultAccount"
                            checked={isDefault}
                            onChange={() => handleDefaultChange(accId)}
                            className="cursor-pointer"
                          />
                          <Label
                            htmlFor={`default-${accId}`}
                            className="text-xs text-muted-foreground cursor-pointer"
                          >
                            Default
                          </Label>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              
              <div className="flex items-center gap-2 pt-2">
                <Button
                  onClick={handleSaveAccountSelection}
                  disabled={saving || selectedAccountIds.size === 0}
                  size="sm"
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Selection'
                  )}
                </Button>
                {selectedAccountIds.size === 0 && (
                  <span className="text-xs text-muted-foreground">
                    Select at least one account
                  </span>
                )}
              </div>
            </div>
          )}
          
          {discoveredAccounts.length === 0 && (
            <Alert>
              <AlertDescription>
                No accounts discovered. Click "Refresh Accounts" to discover accounts from the broker.
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}

      {/* Settings Tabs */}
      <Tabs defaultValue="position-sizing" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
          <TabsTrigger value="position-sizing" className="gap-2">
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">Position Sizing</span>
            <span className="sm:hidden">Sizing</span>
          </TabsTrigger>
          <TabsTrigger value="risk-limits" className="gap-2">
            <Shield className="h-4 w-4" />
            <span className="hidden sm:inline">Risk Limits</span>
            <span className="sm:hidden">Risk</span>
          </TabsTrigger>
          <TabsTrigger value="routing" className="gap-2">
            <GitBranch className="h-4 w-4" />
            <span className="hidden sm:inline">Signal Routing</span>
            <span className="sm:hidden">Routing</span>
          </TabsTrigger>
        </TabsList>

        <AccountSettingsForm
          settings={settings}
          groups={groups}
          broker={account?.broker || 'tradelocker'}
          onSave={handleSave}
          saving={saving}
        />
      </Tabs>
    </div>
  );
}
