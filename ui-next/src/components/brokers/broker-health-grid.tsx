'use client';

import { useEffect, useState, useCallback } from 'react';
import { BrokerHealthCard } from './broker-health-card';
import { getBrokerHealth } from '@/lib/api/brokers';
import { BrokerType, HealthStatus } from '@/types/broker';
import { useWebSocketContext } from '@/providers/websocket-provider';
import { AccountUpdateData } from '@/types/websocket';

// All 5 broker types we support
const ALL_BROKERS: BrokerType[] = ['mt4', 'mt5', 'tradelocker', 'tradovate', 'projectx'];

export function BrokerHealthGrid() {
  const { subscribeToAccounts } = useWebSocketContext();
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentlyChanged, setRecentlyChanged] = useState<Set<string>>(new Set());

  // Fetch initial health status
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

  // Handle WebSocket account updates
  const handleAccountUpdate = useCallback((data: AccountUpdateData) => {
    const brokerKey = data.broker.toLowerCase();

    setHealthStatus((current) => {
      if (!current) {
        // Initialize if not set
        return {
          status: data.connected ? 'healthy' : 'unhealthy',
          redis: 'connected',
          brokers: { [brokerKey]: data.connected },
        };
      }

      // Update broker connection status
      const newBrokers = {
        ...current.brokers,
        [brokerKey]: data.connected,
      };

      // Update overall health based on all brokers
      const anyConnected = Object.values(newBrokers).some((v) => v);
      const newStatus = anyConnected ? 'healthy' : 'unhealthy';

      return {
        ...current,
        status: newStatus as 'healthy' | 'unhealthy',
        brokers: newBrokers,
      };
    });

    // Mark as recently changed for animation
    setRecentlyChanged((prev) => new Set(prev).add(brokerKey));
    setTimeout(() => {
      setRecentlyChanged((prev) => {
        const next = new Set(prev);
        next.delete(brokerKey);
        return next;
      });
    }, 2000);
  }, []);

  // Subscribe to WebSocket account updates
  useEffect(() => {
    const unsubscribe = subscribeToAccounts(handleAccountUpdate);
    return unsubscribe;
  }, [subscribeToAccounts, handleAccountUpdate]);

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
          recentlyChanged={recentlyChanged.has(broker)}
        />
      ))}
    </div>
  );
}
