'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Zap, Loader2, CheckCircle, XCircle, ChevronDown } from 'lucide-react';
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
} from '@/components/ui/dropdown-menu';
import { useToast } from '@/hooks/use-toast';
import { useUser } from '@/providers/user-provider';

// Test symbols - crypto available 24/7 for when forex is closed
const TEST_SYMBOLS = [
  { value: 'XAUUSD', label: 'Gold (XAUUSD)', category: 'Commodity' },
  { value: 'EURUSD', label: 'EUR/USD', category: 'Forex' },
  { value: 'BTCUSD', label: 'Bitcoin (BTCUSD)', category: 'Crypto 24/7' },
  { value: 'ETHUSD', label: 'Ethereum (ETHUSD)', category: 'Crypto 24/7' },
];

interface TestResult {
  success: boolean;
  message: string;
  signal_id?: string;
  symbol?: string;
  phases?: {
    open: { success: boolean; signal_id?: string };
    close: { success: boolean; signal_id?: string };
  };
}

interface TestWebhookButtonProps {
  onSuccess?: () => void;
}

export function TestWebhookButton({ onSuccess }: TestWebhookButtonProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState('XAUUSD');
  const { toast } = useToast();
  const { user } = useUser();

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

    try {
      const response = await fetch('/api/webhooks/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ symbol: selectedSymbol }),
      });

      const data = await response.json();

      const testResult: TestResult = {
        success: data.success,
        message: data.message || (data.success ? 'Test signal sent successfully' : 'Failed to send test signal'),
        signal_id: data.signal_id,
        symbol: data.symbol || selectedSymbol,
        phases: data.phases,
      };

      setResult(testResult);

      // Show toast notification
      if (testResult.success) {
        const phaseInfo = testResult.phases
          ? `Opened & closed ${testResult.symbol}`
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

  const selectedSymbolData = TEST_SYMBOLS.find(s => s.value === selectedSymbol);

  return (
    <div className="flex items-center gap-1">
      {/* Symbol selector dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="h-9 px-2" disabled={loading}>
            <span className="text-xs font-mono">{selectedSymbol}</span>
            <ChevronDown className="h-3 w-3 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuLabel className="text-xs">Test Symbol</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {TEST_SYMBOLS.map((symbol) => (
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
              disabled={loading}
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
