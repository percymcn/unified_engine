'use client';

import { useEffect, useState, useCallback } from 'react';
import { Trade, TradeFilters as TradeFiltersType } from '@/types/trade';
import { getTrades } from '@/lib/api/trades';
import { TradesTable } from '@/components/trades/trades-table';
import { TradeFilters } from '@/components/trades/trade-filters';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [filters, setFilters] = useState<TradeFiltersType>({});

  const fetchTrades = useCallback(async () => {
    try {
      setError(null);
      const data = await getTrades(filters);
      setTrades(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filters]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchTrades();
  };

  const handleFiltersChange = (newFilters: TradeFiltersType) => {
    setFilters(newFilters);
  };

  // Fetch trades on mount and when filters change
  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading trades...</div>
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
          <h1 className="text-3xl font-bold">Trade History</h1>
          <p className="text-muted-foreground mt-1">
            Review your trade execution history
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

      <TradeFilters filters={filters} onFiltersChange={handleFiltersChange} />

      <TradesTable trades={trades} />
    </div>
  );
}
