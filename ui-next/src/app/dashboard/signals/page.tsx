'use client';

import { useEffect, useState } from 'react';
import { Signal } from '@/types/signal';
import { SignalsTable } from '@/components/signals/signals-table';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchSignals = async () => {
    try {
      setError(null);
      const response = await fetch('/api/signals');

      if (!response.ok) {
        throw new Error('Failed to fetch signals');
      }

      const data = await response.json();
      setSignals(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchSignals();
  };

  useEffect(() => {
    fetchSignals();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading signals...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-destructive">Error: {error}</p>
          <Button onClick={handleRefresh} className="mt-4">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Signals</h1>
          <p className="text-muted-foreground mt-1">
            Monitor your trading signals in real-time
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={refreshing}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <SignalsTable signals={signals} />
    </div>
  );
}
