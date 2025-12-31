import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { RefreshCw, CheckCircle, AlertCircle, Loader2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface BrokerAccount {
  id: string;
  account_number: string;
  account_type: 'demo' | 'live' | 'funded';
  balance: number;
  broker: string;
  is_active: boolean;
  last_sync: string;
}

interface ChangeAccountPageProps {
  onComplete: () => void;
  onBack: () => void;
}

export function ChangeAccountPage({ onComplete, onBack }: ChangeAccountPageProps) {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [currentAccountId, setCurrentAccountId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      // Mock data - replace with real API call
      const mockAccounts: BrokerAccount[] = [
        {
          id: '1',
          account_number: 'PA-123456',
          account_type: 'funded',
          balance: 50000,
          broker: 'Topstep',
          is_active: true,
          last_sync: '2025-10-18T10:30:00Z'
        },
        {
          id: '2',
          account_number: 'PA-789012',
          account_type: 'funded',
          balance: 150000,
          broker: 'Topstep',
          is_active: false,
          last_sync: '2025-10-18T09:15:00Z'
        },
        {
          id: '3',
          account_number: 'TL-456789',
          account_type: 'live',
          balance: 25000,
          broker: 'TradeLocker',
          is_active: false,
          last_sync: '2025-10-18T08:45:00Z'
        }
      ];
      
      setTimeout(() => {
        setAccounts(mockAccounts);
        const active = mockAccounts.find(a => a.is_active);
        if (active) {
          setCurrentAccountId(active.id);
          setSelectedAccountId(active.id);
        }
        setLoading(false);
      }, 800);
    } catch (error) {
      toast.error('Failed to load accounts');
      setLoading(false);
    }
  };

  const handleSwitchAccount = async () => {
    if (!selectedAccountId || selectedAccountId === currentAccountId) {
      toast.error('Please select a different account');
      return;
    }

    setSwitching(true);
    setShowConfirmDialog(false);

    try {
      // Replace with real API call
      // await apiClient.post('/api/accounts/switch', {
      //   account_id: selectedAccountId
      // });
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const selectedAccount = accounts.find(a => a.id === selectedAccountId);
      toast.success(`Switched to account ${selectedAccount?.account_number}`);
      onComplete();
    } catch (error) {
      toast.error('Failed to switch account');
      setSwitching(false);
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading accounts...</p>
        </div>
      </div>
    );
  }

  const currentAccount = accounts.find(a => a.id === currentAccountId);
  const selectedAccount = accounts.find(a => a.id === selectedAccountId);
  const hasChanges = selectedAccountId !== currentAccountId;

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-5xl">
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
              <h1 className="text-3xl font-semibold mb-2">Change Active Account</h1>
              <p className="text-muted-foreground">
                Switch between your connected broker accounts
              </p>
            </div>
            <RefreshCw className="w-10 h-10 text-primary" />
          </div>
        </div>

        {/* Current Account Display */}
        {currentAccount && (
          <Card className="mb-6 border-2 border-primary bg-primary/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-500" />
                Current Active Account
              </CardTitle>
              <CardDescription>
                This is the account currently receiving trading signals
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Account Number</p>
                  <p className="text-lg font-semibold">{currentAccount.account_number}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Broker</p>
                  <p className="text-lg font-semibold">{currentAccount.broker}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Balance</p>
                  <p className="text-lg font-semibold">${currentAccount.balance.toLocaleString()}</p>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                {getTypeBadge(currentAccount.account_type)}
                <Badge className="bg-green-100 text-green-700 border-green-200">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Active
                </Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Available Accounts */}
        <Card>
          <CardHeader>
            <CardTitle>Available Accounts</CardTitle>
            <CardDescription>
              Select an account to switch to
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RadioGroup value={selectedAccountId || ''} onValueChange={setSelectedAccountId}>
              <div className="space-y-4">
                {accounts.map((account) => (
                  <div
                    key={account.id}
                    className={`relative flex items-start p-4 border-2 rounded-lg transition-all cursor-pointer ${
                      selectedAccountId === account.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                    onClick={() => setSelectedAccountId(account.id)}
                  >
                    <RadioGroupItem
                      value={account.id}
                      id={account.id}
                      className="mt-1"
                    />
                    <Label
                      htmlFor={account.id}
                      className="flex-1 ml-4 cursor-pointer"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h4 className="font-semibold text-lg mb-1">
                            {account.account_number}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {account.broker}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {getTypeBadge(account.account_type)}
                          {account.is_active && (
                            <Badge className="bg-green-100 text-green-700 border-green-200">
                              Active
                            </Badge>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Balance</p>
                          <p className="font-semibold">${account.balance.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Type</p>
                          <p className="font-semibold capitalize">{account.account_type}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Last Sync</p>
                          <p className="font-semibold text-sm">{formatDate(account.last_sync)}</p>
                        </div>
                      </div>
                    </Label>
                  </div>
                ))}
              </div>
            </RadioGroup>

            {accounts.length === 0 && (
              <Alert className="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800">
                <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <AlertDescription className="text-amber-800 dark:text-amber-200">
                  No accounts available. Please connect a broker account first.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Action Bar */}
        <Card className="mt-6 sticky bottom-4 border-2 shadow-lg">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                {hasChanges ? (
                  <>
                    <p className="font-medium">Ready to switch accounts</p>
                    <p className="text-sm text-muted-foreground">
                      Switch to {selectedAccount?.account_number}
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-medium">No changes</p>
                    <p className="text-sm text-muted-foreground">
                      Select a different account to switch
                    </p>
                  </>
                )}
              </div>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={onBack}
                  disabled={switching}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => setShowConfirmDialog(true)}
                  disabled={!hasChanges || switching}
                  className="bg-primary hover:bg-primary/90 min-w-32"
                >
                  {switching ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Switching...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Switch Account
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Confirmation Dialog */}
        <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Confirm Account Switch</AlertDialogTitle>
              <AlertDialogDescription asChild>
                <div className="space-y-3">
                  <p>
                    You are about to switch from <strong>{currentAccount?.account_number}</strong> to{' '}
                    <strong>{selectedAccount?.account_number}</strong>.
                  </p>
                  <Alert className="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800">
                    <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <AlertDescription className="text-amber-800 dark:text-amber-200">
                      All future trading signals will be routed to the new account. 
                      Any open positions on the current account will remain active.
                    </AlertDescription>
                  </Alert>
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleSwitchAccount}
                className="bg-primary hover:bg-primary/90"
              >
                Confirm Switch
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
