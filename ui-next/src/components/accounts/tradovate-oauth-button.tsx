'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, ExternalLink } from 'lucide-react';

export function TradovateOAuthButton() {
  const [environment, setEnvironment] = useState<'demo' | 'live'>('demo');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/tradovate/authorize?environment=${environment}`
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || data.detail || 'Failed to initiate OAuth');
      }

      const data = await response.json();
      const authorizationUrl = data.authorization_url || data.url;

      if (!authorizationUrl) {
        throw new Error('No authorization URL received from server');
      }

      // Redirect to Tradovate authorization page
      window.location.href = authorizationUrl;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Connection failed';
      setError(errorMessage);
      setLoading(false);
      console.error('Tradovate OAuth error:', err);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">Environment</label>
        <Select
          value={environment}
          onValueChange={(v) => setEnvironment(v as 'demo' | 'live')}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="demo">Demo (Paper Trading)</SelectItem>
            <SelectItem value="live">Live (Real Money)</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          {environment === 'demo'
            ? 'Practice trading with virtual funds'
            : 'Trade with real money - use with caution'}
        </p>
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      <Button
        onClick={handleConnect}
        disabled={loading}
        className="w-full"
        variant="default"
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Connecting...
          </>
        ) : (
          <>
            <ExternalLink className="mr-2 h-4 w-4" />
            Connect with Tradovate
          </>
        )}
      </Button>

      <p className="text-xs text-muted-foreground text-center">
        You will be redirected to Tradovate to authorize access
      </p>
    </div>
  );
}
