'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Zap, Loader2, CheckCircle, XCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useToast } from '@/hooks/use-toast';
import { useUser } from '@/providers/user-provider';

interface TestResult {
  success: boolean;
  message: string;
  signal_id?: string;
}

interface TestWebhookButtonProps {
  onSuccess?: () => void;
}

export function TestWebhookButton({ onSuccess }: TestWebhookButtonProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
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
      });

      const data = await response.json();

      const testResult: TestResult = {
        success: data.success,
        message: data.message || (data.success ? 'Test signal sent successfully' : 'Failed to send test signal'),
        signal_id: data.signal_id,
      };

      setResult(testResult);

      // Show toast notification
      if (testResult.success) {
        toast({
          title: 'Test sent!',
          description: testResult.signal_id
            ? `Signal ID: ${testResult.signal_id}`
            : 'Your webhook is working correctly.',
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

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={result ? (result.success ? 'outline' : 'destructive') : 'default'}
            size="sm"
            onClick={handleTest}
            disabled={loading}
            className="min-w-[140px]"
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
                Test Webhook
              </>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-[280px]">
          {result ? (
            <div className="space-y-1">
              <p className="font-medium">{result.success ? 'Test Successful' : 'Test Failed'}</p>
              <p className="text-xs text-muted-foreground">{result.message}</p>
              {result.signal_id && (
                <p className="text-xs font-mono">Signal ID: {result.signal_id}</p>
              )}
            </div>
          ) : (
            <p>Send a test signal to verify your webhook configuration</p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
