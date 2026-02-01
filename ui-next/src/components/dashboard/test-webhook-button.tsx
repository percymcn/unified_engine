'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Zap, Loader2, CheckCircle, XCircle, ChevronDown, Server } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
  DropdownMenuGroup,
} from '@/components/ui/dropdown-menu';
import { useToast } from '@/hooks/use-toast';
import { useUser } from '@/providers/user-provider';

// Broker-specific symbols configuration
const BROKER_SYMBOLS: Record<string, { value: string; label: string; category: string }[]> = {
  mt5: [
    { value: 'XAUUSD', label: 'Gold (XAUUSD)', category: 'Commodity' },
    { value: 'EURUSD', label: 'EUR/USD', category: 'Forex' },
    { value: 'BTCUSD', label: 'Bitcoin (BTCUSD)', category: 'Crypto 24/7' },
    { value: 'ETHUSD', label: 'Ethereum (ETHUSD)', category: 'Crypto 24/7' },
  ],
  mt4: [
    { value: 'XAUUSD', label: 'Gold (XAUUSD)', category: 'Commodity' },
    { value: 'EURUSD', label: 'EUR/USD', category: 'Forex' },
    { value: 'GBPUSD', label: 'GBP/USD', category: 'Forex' },
  ],
  tradelocker: [
    { value: 'BTCUSD', label: 'Bitcoin (BTCUSD)', category: 'Crypto 24/7' },
    { value: 'XAUUSD', label: 'Gold (XAUUSD)', category: 'Commodity' },
    { value: 'EURUSD', label: 'EUR/USD', category: 'Forex' },
    { value: 'ETHUSD', label: 'Ethereum (ETHUSD)', category: 'Crypto 24/7' },
  ],
  projectx: [
    { value: 'MNQ', label: 'Micro Nasdaq (MNQ)', category: 'Futures' },
    { value: 'MES', label: 'Micro S&P (MES)', category: 'Futures' },
    { value: 'ES', label: 'E-mini S&P (ES)', category: 'Futures' },
    { value: 'NQ', label: 'E-mini Nasdaq (NQ)', category: 'Futures' },
  ],
  tradovate: [
    { value: 'MNQ', label: 'Micro Nasdaq (MNQ)', category: 'Futures' },
    { value: 'MES', label: 'Micro S&P (MES)', category: 'Futures' },
    { value: 'ES', label: 'E-mini S&P (ES)', category: 'Futures' },
  ],
};

// Default symbols for unknown brokers
const DEFAULT_SYMBOLS = [
  { value: 'XAUUSD', label: 'Gold (XAUUSD)', category: 'Commodity' },
  { value: 'EURUSD', label: 'EUR/USD', category: 'Forex' },
  { value: 'BTCUSD', label: 'Bitcoin (BTCUSD)', category: 'Crypto 24/7' },
];

// Broker display names
const BROKER_NAMES: Record<string, string> = {
  mt5: 'MetaTrader 5',
  mt4: 'MetaTrader 4',
  tradelocker: 'TradeLocker',
  projectx: 'ProjectX/TopStep',
  tradovate: 'Tradovate',
};

interface TestResult {
  success: boolean;
  message: string;
  signal_id?: string;
  symbol?: string;
  broker?: string;
  phases?: {
    open: { success: boolean; signal_id?: string };
    close: { success: boolean; signal_id?: string };
  };
}

interface Account {
  id: number;
  broker: string;
  account_name?: string;
  account_number?: string;
  is_active: boolean;
}

interface TestWebhookButtonProps {
  onSuccess?: () => void;
}

export function TestWebhookButton({ onSuccess }: TestWebhookButtonProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSD');
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const { toast } = useToast();
  const { user } = useUser();

  // Fetch accounts on mount
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const response = await fetch('/api/accounts', {
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          const activeAccounts = (data.accounts || []).filter((a: Account) => a.is_active);
          setAccounts(activeAccounts);

          // Auto-select first account if available
          if (activeAccounts.length > 0 && !selectedAccountId) {
            setSelectedAccountId(activeAccounts[0].id);
            setSelectedBroker(activeAccounts[0].broker?.toLowerCase() || null);
            // Set default symbol based on broker
            const brokerSymbols = BROKER_SYMBOLS[activeAccounts[0].broker?.toLowerCase() || ''] || DEFAULT_SYMBOLS;
            setSelectedSymbol(brokerSymbols[0]?.value || 'BTCUSD');
          }
        }
      } catch (error) {
        console.error('Failed to fetch accounts:', error);
      }
    };
    fetchAccounts();
  }, []);

  // Get symbols for selected broker
  const availableSymbols = selectedBroker
    ? BROKER_SYMBOLS[selectedBroker] || DEFAULT_SYMBOLS
    : DEFAULT_SYMBOLS;

  // Handle broker/account change
  const handleAccountChange = (accountId: number, broker: string) => {
    setSelectedAccountId(accountId);
    setSelectedBroker(broker.toLowerCase());
    // Reset symbol to first available for new broker
    const brokerSymbols = BROKER_SYMBOLS[broker.toLowerCase()] || DEFAULT_SYMBOLS;
    if (!brokerSymbols.find(s => s.value === selectedSymbol)) {
      setSelectedSymbol(brokerSymbols[0]?.value || 'BTCUSD');
    }
  };

  const handleTest = async () => {
    setLoading(true);
    setResult(null);

    // Safety check: Ensure user has webhook key
    if (!user?.primary_webhook_key) {
      toast({
        title: 'No webhook key',
        description: 'Generate a webhook key first in the Webhook settings.',
        action: (
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.href = '/dashboard/settings/webhooks'}
            className="ml-2 mt-2"
          >
            Generate Webhook Key
          </Button>
        ),
        variant: 'destructive',
      });
      setTimeout(() => setResult(null), 5000);
      setLoading(false);
      return;
    }

    // Safety check: Ensure account is selected
    if (!selectedAccountId) {
      toast({
        title: 'No account selected',
        description: 'Select a broker account to test.',
        variant: 'destructive',
      });
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/webhooks/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          symbol: selectedSymbol,
          account_id: selectedAccountId,
          broker: selectedBroker,
        }),
      });

      const data = await response.json();

      const testResult: TestResult = {
        success: data.success,
        message: data.message || (data.success ? 'Test signal sent successfully' : 'Failed to send test signal'),
        signal_id: data.signal_id,
        symbol: data.symbol || selectedSymbol,
        broker: selectedBroker || undefined,
        phases: data.phases,
      };

      setResult(testResult);

      // Show toast notification
      if (testResult.success) {
        const phaseInfo = testResult.phases
          ? `Opened & closed ${testResult.symbol} on ${BROKER_NAMES[selectedBroker || ''] || selectedBroker}`
          : `Signal ID: ${testResult.signal_id}`;
        toast({
          title: 'Test Complete!',
          description: phaseInfo,
        });
        onSuccess?.();
      } else {
        // Provide helpful error messages based on the issue
        let errorTitle = 'Test Failed';
        let errorDescription = testResult.message || 'Unknown error occurred.';

        if (testResult.message?.toLowerCase().includes('no webhook key')) {
          errorTitle = 'No Webhook Key';
          errorDescription = 'Generate a webhook key first to test.';
        } else if (testResult.message?.toLowerCase().includes('add an account')) {
          errorTitle = 'No Accounts Connected';
          errorDescription = 'Connect a broker account first to test webhooks.';
        } else if (testResult.message?.toLowerCase().includes('invalid')) {
          errorTitle = 'Invalid Webhook Key';
          errorDescription = 'Your webhook key may be invalid. Try generating a new one.';
        } else if (testResult.message?.toLowerCase().includes('market closed')) {
          errorTitle = 'Market Closed';
          errorDescription = 'Try using a crypto symbol (BTCUSD) which is available 24/7.';
        }

        toast({
          title: errorTitle,
          description: errorDescription,
          variant: 'destructive',
        });
      }

      // Clear result after 5 seconds
      setTimeout(() => setResult(null), 5000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send test signal';
      setResult({
        success: false,
        message: errorMessage,
      });
      toast({
        title: 'Connection Error',
        description: 'Could not connect to the backend. Please check if the server is running.',
        variant: 'destructive',
      });
      setTimeout(() => setResult(null), 5000);
    } finally {
      setLoading(false);
    }
  };

  const selectedSymbolData = availableSymbols.find(s => s.value === selectedSymbol);
  const selectedAccount = accounts.find(a => a.id === selectedAccountId);

  // Group accounts by broker
  const accountsByBroker = accounts.reduce((acc, account) => {
    const broker = account.broker?.toLowerCase() || 'unknown';
    if (!acc[broker]) acc[broker] = [];
    acc[broker].push(account);
    return acc;
  }, {} as Record<string, Account[]>);

  return (
    <div className="flex flex-wrap items-center gap-1 sm:gap-1">
      {/* Broker/Account selector */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="h-9 px-2" disabled={loading}>
            <Server className="h-3 w-3 mr-1" />
            <span className="text-xs">
              {selectedAccount
                ? `${BROKER_NAMES[selectedBroker || ''] || selectedBroker}`
                : 'Select Broker'}
            </span>
            <ChevronDown className="h-3 w-3 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[200px] sm:w-[220px] max-w-[90vw]">
          <DropdownMenuLabel className="text-xs">Select Account</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {Object.entries(accountsByBroker).map(([broker, brokerAccounts]) => (
            <DropdownMenuGroup key={broker}>
              <DropdownMenuLabel className="text-xs text-muted-foreground">
                {BROKER_NAMES[broker] || broker.toUpperCase()}
              </DropdownMenuLabel>
              {brokerAccounts.map((account) => (
                <DropdownMenuItem
                  key={account.id}
                  onClick={() => handleAccountChange(account.id, account.broker)}
                  className="flex justify-between"
                >
                  <span className="text-sm truncate">
                    {account.account_name || account.account_number || `Account ${account.id}`}
                  </span>
                  {selectedAccountId === account.id && (
                    <CheckCircle className="h-3 w-3 text-green-500 ml-2" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          ))}
          {accounts.length === 0 && (
            <DropdownMenuItem disabled>
              <span className="text-xs text-muted-foreground">No accounts found</span>
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Symbol selector dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="h-9 px-2" disabled={loading}>
            <span className="text-xs font-mono">{selectedSymbol}</span>
            <ChevronDown className="h-3 w-3 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuLabel className="text-xs">
            Test Symbol {selectedBroker && `(${BROKER_NAMES[selectedBroker] || selectedBroker})`}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {availableSymbols.map((symbol) => (
            <DropdownMenuItem
              key={symbol.value}
              onClick={() => setSelectedSymbol(symbol.value)}
              className="flex justify-between"
            >
              <span>{symbol.label}</span>
              {symbol.category.includes('24/7') && (
                <span className="text-[10px] text-emerald-500 ml-2">24/7</span>
              )}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Test button */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant={result ? (result.success ? 'outline' : 'destructive') : 'default'}
              size="sm"
              onClick={handleTest}
              disabled={loading || !selectedAccountId}
              className="min-w-[120px]"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : result ? (
                <>
                  {result.success ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  {result.success ? 'Success' : 'Failed'}
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Test
                </>
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-[300px]">
            {result ? (
              <div className="space-y-1">
                <p className="font-medium">{result.success ? 'Test Successful' : 'Test Failed'}</p>
                <p className="text-xs text-muted-foreground">{result.message}</p>
                {result.broker && (
                  <p className="text-xs">Broker: {BROKER_NAMES[result.broker] || result.broker}</p>
                )}
                {result.phases && (
                  <div className="text-xs mt-1 space-y-0.5">
                    <p className="flex items-center gap-1">
                      {result.phases.open.success ? <CheckCircle className="h-3 w-3 text-green-500" /> : <XCircle className="h-3 w-3 text-red-500" />}
                      Open: {result.phases.open.signal_id || 'N/A'}
                    </p>
                    <p className="flex items-center gap-1">
                      {result.phases.close.success ? <CheckCircle className="h-3 w-3 text-green-500" /> : <XCircle className="h-3 w-3 text-red-500" />}
                      Close: {result.phases.close.signal_id || 'N/A'}
                    </p>
                  </div>
                )}
                {result.signal_id && !result.phases && (
                  <p className="text-xs font-mono">Signal ID: {result.signal_id}</p>
                )}
              </div>
            ) : (
              <div className="space-y-1">
                <p>Opens a test position on {selectedSymbol}, then closes it</p>
                {selectedBroker && (
                  <p className="text-xs font-medium">Broker: {BROKER_NAMES[selectedBroker] || selectedBroker}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  {selectedSymbolData?.category.includes('24/7')
                    ? 'Crypto is available 24/7 for weekend testing'
                    : 'Use crypto symbols if forex market is closed'}
                </p>
              </div>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
