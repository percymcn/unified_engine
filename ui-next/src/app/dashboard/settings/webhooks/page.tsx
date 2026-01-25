'use client';

import { useEffect, useState } from 'react';
import { Webhook, RefreshCw, KeyRound, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WebhookEndpointCard } from '@/components/webhooks/webhook-endpoint-card';
import { IntegrationInstructions } from '@/components/webhooks/integration-instructions';
import { WebhookEndpoint } from '@/types/webhook';
import { WebhookConfig } from '@/types/routing';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { CopyButton } from '@/components/ui/copy-button';
import { useToast } from '@/hooks/use-toast';
import { useUser } from '@/providers/user-provider';
import { useQueryClient } from '@tanstack/react-query';

const WEBHOOK_ENDPOINTS: WebhookEndpoint[] = [
  {
    source: 'tradingview',
    name: 'TradingView',
    description: 'Receive signals from TradingView alerts and Pine Script strategies',
    url_template: '/webhooks/tradingview/{webhook_key}',
    required_fields: ['symbol', 'action'],
    example_payload: {
      symbol: 'EURUSD',
      action: 'buy',
      price: 1.0850,
      strategy: 'EMA Crossover',
      timeframe: '1h',
    },
  },
  {
    source: 'trailhacker',
    name: 'TrailHacker',
    description: 'Receive signals from TrailHacker trading platform',
    url_template: '/webhooks/trailhacker/{webhook_key}',
    required_fields: ['symbol', 'action'],
    example_payload: {
      symbol: 'GBPUSD',
      action: 'sell',
      price: 1.2650,
      strategy: 'Momentum Breakout',
    },
  },
  {
    source: 'custom',
    name: 'Custom Webhook',
    description: 'Integrate with any custom trading system or bot',
    url_template: '/webhooks/custom/{source}/{webhook_key}',
    required_fields: ['symbol', 'action'],
    example_payload: {
      symbol: 'USDJPY',
      action: 'close',
      price: 148.50,
      source: 'mybot',
      metadata: {
        confidence: 0.85,
        indicator: 'RSI',
      },
    },
  },
];

export default function WebhooksPage() {
  const [configs, setConfigs] = useState<WebhookConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [baseUrl, setBaseUrl] = useState('');
  const [generatingKey, setGeneratingKey] = useState(false);
  const { toast } = useToast();

  // Use same source as dashboard for consistent webhook key
  const { user, refetch: refetchUser } = useUser();
  const queryClient = useQueryClient();

  useEffect(() => {
    // Get base URL from environment - prefer WEBHOOK_BASE_URL for public-facing URLs
    const webhookBaseUrl = process.env.NEXT_PUBLIC_WEBHOOK_BASE_URL ||
                           process.env.NEXT_PUBLIC_BACKEND_URL ||
                           'http://localhost:8765';
    setBaseUrl(webhookBaseUrl);

    // Fetch webhook configs
    fetchConfigs();
  }, []);

  const fetchConfigs = async (showLoading = true) => {
    try {
      if (showLoading) {
        setLoading(true);
      }
      setError(null);
      const response = await fetch('/api/webhook-configs');

      // Handle 401 specifically
      if (response.status === 401) {
        setError('Please log in to view your webhook configurations.');
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch webhook configs');
      }

      const data = await response.json();

      // Handle error responses from API (which might return empty array or error object)
      if (data.error) {
        setError(data.error);
        return;
      }

      setConfigs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load webhook configs:', err);
      setError('Unable to connect to server. Please check your connection and try again.');
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  const getWebhookUrl = (endpoint: WebhookEndpoint): string => {
    // Use primaryKey (from user profile) for consistent URLs across pages
    const keyToUse = primaryKey || 'YOUR_WEBHOOK_KEY';
    let url = endpoint.url_template.replace('{webhook_key}', keyToUse);

    // For custom webhooks, replace {source} placeholder
    if (endpoint.source === 'custom') {
      url = url.replace('{source}', 'yoursource');
    }

    return `${baseUrl}${url}`;
  };

  const isConfigured = (source: string): boolean => {
    return configs.some((c) => c.source === source && c.is_active);
  };

  const getConfigForSource = (source: string): WebhookConfig | undefined => {
    return configs.find((c) => c.source === source && c.is_active);
  };

  // Use webhook key from user profile (same source as dashboard) for consistency
  const primaryKey = user?.primary_webhook_key || '';

  const handleGenerateKey = async () => {
    try {
      setGeneratingKey(true);
      const response = await fetch('/api/webhooks/generate-key', { method: 'POST' });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to generate webhook key' }));
        throw new Error(err.detail || 'Failed to generate webhook key');
      }
      // Refresh both data sources for consistency across pages
      await Promise.all([
        fetchConfigs(false),
        refetchUser(),
      ]);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['user-profile'] }),
        queryClient.invalidateQueries({ queryKey: ['webhook-configs'] }),
      ]);
      toast({
        title: 'Webhook key updated',
        description: 'Your new webhook key is ready to copy.',
      });
    } catch (err) {
      console.error('Failed to generate key:', err);
      toast({
        title: 'Webhook key update failed',
        description: err instanceof Error ? err.message : 'Failed to generate webhook key',
        variant: 'destructive',
      });
    } finally {
      setGeneratingKey(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Webhook Endpoints</h1>
          <p className="text-muted-foreground mt-2">Loading...</p>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <Webhook className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold">Webhook Endpoints</h1>
        </div>
        <p className="text-muted-foreground mt-2">
          Connect your trading signals from external platforms. Copy the webhook URLs below and
          configure them in your signal sources.
        </p>
      </div>

      {/* Error Alert with Retry */}
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error Loading Data</AlertTitle>
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={fetchConfigs} className="ml-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Base URL Info */}
      <div className="rounded-lg border p-4 bg-muted/50">
        <h3 className="font-semibold mb-2">Base URL</h3>
        <div className="flex items-center gap-2">
          <div className="text-sm text-muted-foreground break-all font-mono">{baseUrl}</div>
          <CopyButton text={baseUrl} tooltip="Copy base URL" />
        </div>
      </div>

      {/* Webhook Key */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-primary" />
              <h3 className="font-semibold">Webhook Key</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Use this key in your webhook URLs to authenticate requests.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateKey}
            disabled={generatingKey}
          >
            {generatingKey ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              'Generate new key'
            )}
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 rounded-md bg-muted px-3 py-2 font-mono text-xs break-all">
            {primaryKey || 'No key yet. Click generate to create one.'}
          </div>
          {primaryKey && (
            <CopyButton text={primaryKey} tooltip="Copy webhook key" />
          )}
        </div>
      </div>

      {/* Endpoint Cards */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Available Endpoints</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          {WEBHOOK_ENDPOINTS.map((endpoint) => {
            const webhookUrl = getWebhookUrl(endpoint);
            // Show as configured if we have a valid key
            const configured = !!primaryKey;

            return (
              <WebhookEndpointCard
                key={endpoint.source}
                endpoint={endpoint}
                webhookUrl={webhookUrl}
                isConfigured={configured}
              />
            );
          })}
        </div>
      </div>

      {/* Integration Instructions */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Integration Guides</h2>
        <IntegrationInstructions />
      </div>
    </div>
  );
}
