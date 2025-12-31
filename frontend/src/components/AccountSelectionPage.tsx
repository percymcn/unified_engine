import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Checkbox } from './ui/checkbox';
import { Alert, AlertDescription } from './ui/alert';
import { CheckCircle, AlertCircle, Loader2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface SyncedAccount {
  id: string;
  account_number: string;
  account_type: 'demo' | 'live' | 'funded';
  balance: number;
  status: 'available' | 'in_use' | 'error';
  broker: string;
}

interface AccountSelectionPageProps {
  onComplete: () => void;
  onBack: () => void;
}

export function AccountSelectionPage({ onComplete, onBack }: AccountSelectionPageProps) {
  const [accounts, setAccounts] = useState<SyncedAccount[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);

  useEffect(() => {
    fetchSyncedAccounts();
  }, []);

  const fetchSyncedAccounts = async () => {
    setLoading(true);
    try {
      // Mock data - replace with real API call
      const mockAccounts: SyncedAccount[] = [
        {
          id: '1',
          account_number: 'PA-123456',
          account_type: 'funded',
          balance: 50000,
          status: 'available',
          broker: 'Topstep'
        },
        {
          id: '2',
          account_number: 'PA-789012',
          account_type: 'funded',
          balance: 150000,
          status: 'available',
          broker: 'Topstep'
        },
        {
          id: '3',
          account_number: 'PA-345678',
          account_type: 'demo',
          balance: 100000,
          status: 'in_use',
          broker: 'Topstep'
        }
      ];
      
      setTimeout(() => {
        setAccounts(mockAccounts);
        setLoading(false);
      }, 800);
    } catch (error) {
      toast.error('Failed to load synced accounts');
      setLoading(false);
    }
  };

  const toggleAccountSelection = (accountId: string) => {
    const newSelection = new Set(selectedAccounts);
    if (newSelection.has(accountId)) {
      newSelection.delete(accountId);
    } else {
      newSelection.add(accountId);
    }
    setSelectedAccounts(newSelection);
  };

  const handleActivateAccounts = async () => {
    if (selectedAccounts.size === 0) {
      toast.error('Please select at least one account');
      return;
    }

    setActivating(true);
    try {
      // Replace with real API call
      // await apiClient.post('/api/accounts/activate', {
      //   account_ids: Array.from(selectedAccounts)
      // });
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      toast.success(`${selectedAccounts.size} account(s) activated successfully`);
      onComplete();
    } catch (error) {
      toast.error('Failed to activate accounts');
    } finally {
      setActivating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <Badge className="bg-green-100 text-green-700 border-green-200">Available</Badge>;
      case 'in_use':
        return <Badge className="bg-amber-100 text-amber-700 border-amber-200">In Use</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-700 border-red-200">Error</Badge>;
      default:
        return null;
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'funded':
        return <Badge className="bg-blue-100 text-blue-700 border-blue-200">Funded</Badge>;
      case 'live':
        return <Badge className="bg-purple-100 text-purple-700 border-purple-200">Live</Badge>;
      case 'demo':
        return <Badge variant="outline">Demo</Badge>;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading synced accounts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={onBack}
            className="mb-4 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Accounts
          </Button>
          
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-semibold mb-2">Account Sync Results</h1>
              <p className="text-muted-foreground">
                Select accounts to activate for trading
              </p>
            </div>
            <CheckCircle className="w-12 h-12 text-green-500" />
          </div>
        </div>

        {/* Info Alert */}
        <Alert className="mb-6 bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800">
          <AlertCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <AlertDescription className="text-blue-800 dark:text-blue-200">
            Found <strong>{accounts.length}</strong> synced accounts from your broker. 
            Select which accounts you want to use for trading.
          </AlertDescription>
        </Alert>

        {/* Accounts Grid */}
        <div className="space-y-4 mb-6">
          {accounts.map((account) => (
            <Card
              key={account.id}
              className={`border-2 transition-all ${
                selectedAccounts.has(account.id)
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              } ${account.status === 'in_use' ? 'opacity-60' : ''}`}
            >
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  {/* Checkbox */}
                  <Checkbox
                    checked={selectedAccounts.has(account.id)}
                    onCheckedChange={() => toggleAccountSelection(account.id)}
                    disabled={account.status === 'in_use'}
                    className="mt-1"
                  />

                  {/* Account Details */}
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-lg font-semibold mb-1">
                          {account.account_number}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {account.broker}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        {getTypeBadge(account.account_type)}
                        {getStatusBadge(account.status)}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Balance</p>
                        <p className="text-lg font-semibold">
                          ${account.balance.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Account Type</p>
                        <p className="text-lg font-semibold capitalize">
                          {account.account_type}
                        </p>
                      </div>
                    </div>

                    {account.status === 'in_use' && (
                      <Alert className="mt-4 bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800">
                        <AlertDescription className="text-amber-800 dark:text-amber-200 text-sm">
                          This account is already in use
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Action Bar */}
        <Card className="sticky bottom-4 border-2 shadow-lg">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">
                  {selectedAccounts.size} account{selectedAccounts.size !== 1 ? 's' : ''} selected
                </p>
                <p className="text-sm text-muted-foreground">
                  {selectedAccounts.size > 0 
                    ? 'Ready to activate'
                    : 'Select at least one account to continue'
                  }
                </p>
              </div>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={onBack}
                  disabled={activating}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleActivateAccounts}
                  disabled={selectedAccounts.size === 0 || activating}
                  className="bg-primary hover:bg-primary/90 min-w-32"
                >
                  {activating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Activating...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Activate Selected
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
