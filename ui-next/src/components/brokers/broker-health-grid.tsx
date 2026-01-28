'use client';

import { useEffect, useState, useCallback } from 'react';
import { BrokerHealthCard } from './broker-health-card';
import { getBrokerHealth } from '@/lib/api/brokers';
import { BrokerType, HealthStatus } from '@/types/broker';
import { useWebSocketContext } from '@/providers/websocket-provider';
import { AccountUpdateData } from '@/types/websocket';

// All 5 broker types we support
const ALL_BROKERS: BrokerType[] = ['mt4', 'mt5', 'tradelocker', 'tradovate', 'projectx'];

// Map broker names to lowercase for matching
const BROKER_NAME_MAP: Record<string, BrokerType> = {
  mt4: 'mt4',
  mt5: 'mt5',
  tradelocker: 'tradelocker',
  tradovate: 'tradovate',
  projectx: 'projectx',
  topstep: 'projectx',
};

export function BrokerHealthGrid() {
  const { subscribeToAccounts } = useWebSocketContext();
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [accountBrokers, setAccountBrokers] = useState<Set<BrokerType>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentlyChanged, setRecentlyChanged] = useState<Set<string>>(new Set());

  // Fetch accounts and health status
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);

        // Fetch both accounts and health in parallel
        const [accountsRes, healthRes] = await Promise.all([
          fetch('/api/accounts', { credentials: 'include' }).then(r => r.ok ? r.json() : []),
          getBrokerHealth().catch(() => null),
        ]);

        // Extract brokers that have active accounts
        const accounts = Array.isArray(accountsRes) ? accountsRes : (accountsRes?.accounts || []);
        const brokersWithAccounts = new Set<BrokerType>();

        for (const acc of accounts) {
          if (acc.is_active !== false) {
            const brokerKey = BROKER_NAME_MAP[acc.broker?.toLowerCase()] || acc.broker?.toLowerCase();
            if (brokerKey && ALL_BROKERS.includes(brokerKey as BrokerType)) {
              brokersWithAccounts.add(brokerKey as BrokerType);
            }
          }
        }

        setAccountBrokers(brokersWithAccounts);

        if (healthRes) {
          setHealthStatus(healthRes);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to fetch broker data:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch broker data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
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

  // Determine if broker is connected: ONLY if user has an active account
  // No fallback to system-wide health - show only the user's own connections
  const isBrokerConnected = (broker: BrokerType): boolean => {
    // Only show connected if user has an active account for this broker
    return accountBrokers.has(broker);
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {ALL_BROKERS.map((broker) => (
        <BrokerHealthCard
          key={broker}
          name={broker}
          connected={isBrokerConnected(broker)}
          loading={loading}
          recentlyChanged={recentlyChanged.has(broker)}
        />
      ))}
    </div>
  );
}
