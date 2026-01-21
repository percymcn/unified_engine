'use client';

import { useEffect, useState } from 'react';
import { Webhook, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WebhookEndpointCard } from '@/components/webhooks/webhook-endpoint-card';
import { IntegrationInstructions } from '@/components/webhooks/integration-instructions';
import { WebhookEndpoint } from '@/types/webhook';
import { WebhookConfig } from '@/types/routing';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';

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

  useEffect(() => {
    // Get base URL from environment - prefer WEBHOOK_BASE_URL for public-facing URLs
    const webhookBaseUrl = process.env.NEXT_PUBLIC_WEBHOOK_BASE_URL ||
                           process.env.NEXT_PUBLIC_BACKEND_URL ||
                           'http://localhost:8765';
    setBaseUrl(webhookBaseUrl);

    // Fetch webhook configs
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
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
      setLoading(false);
    }
  };

  const getWebhookUrl = (endpoint: WebhookEndpoint, config?: WebhookConfig): string => {
    if (!config) {
      return `${baseUrl}${endpoint.url_template.replace('{webhook_key}', 'YOUR_WEBHOOK_KEY')}`;
    }

    let url = endpoint.url_template.replace('{webhook_key}', config.webhook_key);

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
        <p className="text-sm text-muted-foreground">
          All webhook URLs start with: <code className="font-mono">{baseUrl}</code>
        </p>
      </div>

      {/* Endpoint Cards */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Available Endpoints</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          {WEBHOOK_ENDPOINTS.map((endpoint) => {
            const config = getConfigForSource(endpoint.source);
            const webhookUrl = getWebhookUrl(endpoint, config);
            const configured = isConfigured(endpoint.source);

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
