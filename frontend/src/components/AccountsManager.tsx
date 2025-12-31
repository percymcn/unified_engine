import { useState, useEffect } from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Switch } from './ui/switch';
import { Plus, Trash2, RefreshCw, CheckCircle, Edit2, ChevronDown, ChevronUp } from 'lucide-react';
import { useBroker, BrokerType, getBrokerDisplayName } from '../contexts/BrokerContext';
import { useUser } from '../contexts/UserContext';
import { toast } from 'sonner@2.0.3';
import { cn } from './ui/utils';
import { ApiKeyDisplay } from './ApiKeyDisplay';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';

interface Account {
  id: string;
  broker: BrokerType;
  accountId: string;
  accountName: string;
  enabled: boolean;
  connected: boolean;
  lastSync?: string;
  balance: number;
  equity: number;
  pnl: number;
  pnlPercent: number;
  apiKey?: string;  // Generated API key for this account
}

interface AccountsManagerProps {
  broker: BrokerType;
}

export function AccountsManager({ broker }: AccountsManagerProps) {
  const { connectedBrokers, addBrokerAccount, removeBrokerAccount, refreshBrokerData } = useBroker();
  const { user } = useUser();
  
  // Filter accounts for the current broker
  const brokerAccounts = connectedBrokers
    .filter(acc => acc.broker === broker)
    .map(acc => ({
      id: acc.accountId,
      broker: acc.broker,
      accountId: acc.accountId,
      accountName: acc.accountName,
      enabled: acc.connected,
      connected: acc.connected,
      lastSync: acc.lastSync,
      // Mock financial data - in production, fetch from backend
      balance: Math.random() * 100000,
      equity: Math.random() * 100000,
      pnl: 0,
      pnlPercent: 0,
      // Generate mock API key - in production, this comes from backend after account registration
      apiKey: `${broker}_${acc.accountId.slice(0, 8)}_${Math.random().toString(36).substring(2, 15)}`
    }));

  // Calculate P&L for each account
  brokerAccounts.forEach(acc => {
    acc.pnl = acc.equity - acc.balance;
    acc.pnlPercent = (acc.pnl / acc.balance) * 100;
  });

  const [accounts, setAccounts] = useState<Account[]>(brokerAccounts);
  const [isRefreshing, setIsRefreshing] = useState<string | null>(null);
  const [expandedAccounts, setExpandedAccounts] = useState<Set<string>>(new Set());

  useEffect(() => {
    setAccounts(brokerAccounts);
  }, [connectedBrokers, broker]);

  // Get tier limits
  const tierLimits = {
    trial: { brokers: 1, accounts: 1 },
    starter: { brokers: 1, accounts: 1 },
    pro: { brokers: 2, accounts: 2 },
    elite: { brokers: 3, accounts: 3 }
  };

  const currentTier = user?.plan || 'trial';
  const limit = tierLimits[currentTier as keyof typeof tierLimits] || tierLimits.trial;
  const canAddMore = accounts.length < limit.accounts;

  const handleAddAccount = () => {
    if (!canAddMore) {
      toast.error(`Upgrade to add more accounts. Current plan allows ${limit.accounts} account(s) per broker.`);
      return;
    }
    // Navigate to connect broker page or open dialog
    toast.info('Opening add account dialog...');
  };

  const handleToggle = async (accountId: string) => {
    setAccounts(accounts.map(acc => 
      acc.id === accountId ? { ...acc, enabled: !acc.enabled } : acc
    ));
    
    const account = accounts.find(a => a.id === accountId);
    toast.success(`${account?.accountName} ${!account?.enabled ? 'enabled' : 'disabled'}`);
  };

  const handleRefresh = async (accountId: string) => {
    setIsRefreshing(accountId);
    try {
      await refreshBrokerData();
      
      // Update last sync time
      setAccounts(accounts.map(acc =>
        acc.id === accountId
          ? { ...acc, lastSync: 'Just now' }
          : acc
      ));
      
      toast.success('Account data refreshed');
    } catch (error) {
      toast.error('Failed to refresh account');
    } finally {
      setIsRefreshing(null);
    }
  };

  const handleDelete = async (accountId: string) => {
    const account = accounts.find(a => a.id === accountId);
    if (!account) return;

    if (confirm(`Are you sure you want to delete ${account.accountName}?`)) {
      try {
        removeBrokerAccount(broker, accountId);
        setAccounts(accounts.filter(acc => acc.id !== accountId));
        toast.success(`${account.accountName} deleted`);
      } catch (error) {
        toast.error('Failed to delete account');
      }
    }
  };

  const handleEditAccountNumber = (accountId: string) => {
    const newNumber = prompt('Enter new account number:');
    if (newNumber) {
      setAccounts(accounts.map(acc =>
        acc.id === accountId
          ? { ...acc, accountId: newNumber }
          : acc
      ));
      toast.success('Account number updated');
    }
  };

  const handleRegenerateApiKey = async (accountId: string) => {
    // In production, call backend API to regenerate
    // POST /api/accounts/{accountId}/regenerate-api-key
    const newApiKey = `${broker}_${accountId.slice(0, 8)}_${Math.random().toString(36).substring(2, 15)}`;
    
    setAccounts(accounts.map(acc =>
      acc.id === accountId
        ? { ...acc, apiKey: newApiKey }
        : acc
    ));
  };

  const toggleExpanded = (accountId: string) => {
    setExpandedAccounts(prev => {
      const next = new Set(prev);
      if (next.has(accountId)) {
        next.delete(accountId);
      } else {
        next.add(accountId);
      }
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white mb-1">Account Management</h2>
          <p className="text-sm text-gray-400">
            Connect and configure your {getBrokerDisplayName(broker)} accounts
          </p>
        </div>
        <Button
          onClick={handleAddAccount}
          disabled={!canAddMore}
          className={cn(
            "bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad]",
            !canAddMore && "opacity-50 cursor-not-allowed"
          )}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Account
        </Button>
      </div>

      {/* Tier Info */}
      <Card className="bg-blue-950/30 border-blue-800/30">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-300">
                {accounts.length} / {limit.accounts} accounts used for {getBrokerDisplayName(broker)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Current plan: <span className="text-[#00ffc2] font-medium">{currentTier.toUpperCase()}</span>
              </p>
            </div>
            {!canAddMore && (
              <Button
                size="sm"
                className="bg-blue-600 hover:bg-blue-700 text-white"
                onClick={() => toast.info('Navigate to Billing to upgrade')}
              >
                Upgrade Plan
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Accounts List */}
      {accounts.length === 0 ? (
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-12 text-center">
            <div className="text-gray-400 mb-4">
              <p className="text-lg mb-2">No accounts connected</p>
              <p className="text-sm">
                Click "Add Account" to connect your {getBrokerDisplayName(broker)} account
              </p>
            </div>
            <Button
              onClick={handleAddAccount}
              className="bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad]"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Account
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {accounts.map((account) => (
            <Card
              key={account.id}
              className={cn(
                "bg-[#001f29] border-gray-800 transition-all",
                !account.enabled && "opacity-60"
              )}
            >
              <CardContent className="p-6">
                {/* Header Row */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-white font-medium">{account.accountName}</h3>
                      <Badge
                        variant="outline"
                        className={
                          account.connected
                            ? 'border-green-500 text-green-400 bg-green-500/10'
                            : 'border-red-500 text-red-400 bg-red-500/10'
                        }
                      >
                        {account.connected ? (
                          <>
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Connected
                          </>
                        ) : (
                          'Disconnected'
                        )}
                      </Badge>
                      <button
                        onClick={() => handleEditAccountNumber(account.id)}
                        className="text-gray-400 hover:text-white transition-colors"
                        title="Edit account number"
                      >
                        <Badge variant="secondary" className="bg-[#002b36] text-gray-300 cursor-pointer hover:bg-[#003545]">
                          {account.accountId}
                          <Edit2 className="w-3 h-3 ml-1" />
                        </Badge>
                      </button>
                    </div>
                    <p className="text-sm text-gray-400">
                      Last synced: {account.lastSync || 'Never'}
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-400">Enabled</span>
                      <Switch
                        checked={account.enabled}
                        onCheckedChange={() => handleToggle(account.id)}
                        className="data-[state=checked]:bg-[#00ffc2]"
                      />
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRefresh(account.id)}
                      disabled={isRefreshing === account.id}
                      className="text-blue-400 hover:text-blue-300 hover:bg-blue-950/30"
                      title="Refresh account data"
                    >
                      <RefreshCw
                        className={cn(
                          "w-4 h-4",
                          isRefreshing === account.id && "animate-spin"
                        )}
                      />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(account.id)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-950/30"
                      title="Delete account"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-[#002b36] rounded-lg p-4 border border-gray-700">
                    <p className="text-xs text-gray-400 mb-1">Balance</p>
                    <p className="text-white font-medium">
                      ${account.balance.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </p>
                  </div>
                  <div className="bg-[#002b36] rounded-lg p-4 border border-gray-700">
                    <p className="text-xs text-gray-400 mb-1">Equity</p>
                    <p className="text-white font-medium">
                      ${account.equity.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </p>
                  </div>
                  <div className="bg-[#002b36] rounded-lg p-4 border border-gray-700">
                    <p className="text-xs text-gray-400 mb-1">P&L</p>
                    <p
                      className={cn(
                        "font-medium",
                        account.pnl >= 0 ? "text-green-400" : "text-red-400"
                      )}
                    >
                      {account.pnl >= 0 ? '+' : ''}${account.pnl.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })}
                    </p>
                  </div>
                  <div className="bg-[#002b36] rounded-lg p-4 border border-gray-700">
                    <p className="text-xs text-gray-400 mb-1">P&L %</p>
                    <p
                      className={cn(
                        "font-medium",
                        account.pnlPercent >= 0 ? "text-green-400" : "text-red-400"
                      )}
                    >
                      {account.pnlPercent >= 0 ? '+' : ''}{account.pnlPercent.toFixed(2)}%
                    </p>
                  </div>
                </div>

                {/* API Key Section - Collapsible */}
                <Collapsible
                  open={expandedAccounts.has(account.id)}
                  onOpenChange={() => toggleExpanded(account.id)}
                  className="mt-4"
                >
                  <CollapsibleTrigger asChild>
                    <Button
                      variant="ghost"
                      className="w-full flex items-center justify-between p-3 text-sm text-gray-300 hover:bg-[#002b36] rounded-lg"
                    >
                      <span>API Key & Webhook Configuration</span>
                      {expandedAccounts.has(account.id) ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-3 p-4 bg-[#002b36]/50 rounded-lg border border-gray-700">
                    {account.apiKey && (
                      <ApiKeyDisplay
                        apiKey={account.apiKey}
                        accountId={account.id}
                        accountName={account.accountName}
                        broker={getBrokerDisplayName(account.broker)}
                        onRegenerate={handleRegenerateApiKey}
                      />
                    )}
                  </CollapsibleContent>
                </Collapsible>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Help Section */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-4">
          <h3 className="text-white mb-3">💡 Quick Tips</h3>
          <div className="space-y-2 text-sm text-gray-400">
            <p>
              • <span className="text-white">Enable/Disable:</span> Control which accounts receive trading signals
            </p>
            <p>
              • <span className="text-white">Refresh:</span> Manually sync account data with broker
            </p>
            <p>
              • <span className="text-white">Edit Account:</span> Click the account number to update it
            </p>
            <p>
              • <span className="text-white">Delete:</span> Permanently remove account from platform
            </p>
            {!canAddMore && (
              <p className="text-yellow-400 mt-3">
                ⚠️ Upgrade your plan to connect more accounts per broker
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
