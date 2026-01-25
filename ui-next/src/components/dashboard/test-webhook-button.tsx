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

  const handleTest = async () => {
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch('/api/webhooks/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
        toast({
          title: 'Invalid key or backend issue',
          description: testResult.message || 'Invalid key or backend issue.',
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
        title: 'Invalid key or backend issue',
        description: errorMessage || 'Invalid key or backend issue.',
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
