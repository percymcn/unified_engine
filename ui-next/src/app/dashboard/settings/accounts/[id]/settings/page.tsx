'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Loader2, ArrowLeft, Settings, Shield, GitBranch } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AccountSettingsForm } from '@/components/accounts/account-settings-form';
import { Account, AccountSettings, AccountGroup, BROKER_DISPLAY_NAMES } from '@/types/account';
import { getAccountSettings, updateAccountSettings, getAccountGroups } from '@/lib/api/accounts';
import { useToast } from '@/hooks/use-toast';

export default function AccountSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const accountId = Number(params.id);

  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [groups, setGroups] = useState<AccountGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    loadData();
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
    } catch (err) {
      console.error('Failed to load account settings:', err);
      setError('Failed to load account settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (updates: Partial<AccountSettings>) => {
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
          onSave={handleSave}
          saving={saving}
        />
      </Tabs>
    </div>
  );
}
