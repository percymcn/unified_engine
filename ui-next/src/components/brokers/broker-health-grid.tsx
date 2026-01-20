'use client';

import { useEffect, useState } from 'react';
import { BrokerHealthCard } from './broker-health-card';
import { getBrokerHealth } from '@/lib/api/brokers';
import { BrokerType, HealthStatus } from '@/types/broker';

// All 5 broker types we support
const ALL_BROKERS: BrokerType[] = ['mt4', 'mt5', 'tradelocker', 'tradovate', 'projectx'];

export function BrokerHealthGrid() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHealth() {
      try {
        setLoading(true);
        const status = await getBrokerHealth();
        setHealthStatus(status);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch broker health:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch broker health');
      } finally {
        setLoading(false);
      }
    }

    fetchHealth();
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <p className="text-sm text-destructive">
          Failed to load broker health: {error}
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {ALL_BROKERS.map((broker) => (
        <BrokerHealthCard
          key={broker}
          name={broker}
          connected={healthStatus?.brokers[broker] ?? false}
          loading={loading}
        />
      ))}
    </div>
  );
}
