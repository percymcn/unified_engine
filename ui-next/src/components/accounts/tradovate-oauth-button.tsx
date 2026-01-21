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

interface TradovateOAuthButtonProps {
  onSuccess?: () => void;
}

export function TradovateOAuthButton({ onSuccess }: TradovateOAuthButtonProps) {
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
        const data = await response.json();
        throw new Error(data.error || 'Failed to initiate OAuth');
      }

      const { authorization_url } = await response.json();

      // Redirect to Tradovate authorization page
      window.location.href = authorization_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setLoading(false);
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
