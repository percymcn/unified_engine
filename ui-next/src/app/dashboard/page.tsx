'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Activity, Users, Signal, TrendingUp } from 'lucide-react';
import { BrokerHealthGrid } from '@/components/brokers/broker-health-grid';

interface DashboardStats {
  activeSignals: number;
  connectedBrokers: number;
  todaysTrades: number;
  totalBalance: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    activeSignals: 0,
    connectedBrokers: 0,
    todaysTrades: 0,
    totalBalance: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await fetch('/api/dashboard/stats');
        if (!response.ok) {
          throw new Error('Failed to fetch stats');
        }
        const data = await response.json();
        setStats(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard stats:', err);
        setError('Failed to load stats');
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const statCards = [
    {
      title: 'Active Signals',
      value: loading ? null : stats.activeSignals.toString(),
      description: 'Pending signals today',
      icon: Signal,
      iconColor: 'text-primary',
    },
    {
      title: 'Connected Brokers',
      value: loading ? null : stats.connectedBrokers.toString(),
      description: 'Active broker connections',
      icon: Users,
      iconColor: 'text-chart-2',
    },
    {
      title: "Today's Trades",
      value: loading ? null : stats.todaysTrades.toString(),
      description: 'Executed today',
      icon: Activity,
      iconColor: 'text-chart-3',
    },
    {
      title: 'Total Balance',
      value: loading ? null : formatCurrency(stats.totalBalance),
      description: 'Across all accounts',
      icon: TrendingUp,
      iconColor: 'text-chart-1',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome heading */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to Tradeflow. Monitor your trading signals and accounts.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.iconColor}`} />
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-8 w-20" />
              ) : error ? (
                <div className="text-2xl font-bold text-muted-foreground">-</div>
              ) : (
                <div className="text-2xl font-bold">{stat.value}</div>
              )}
              <p className="text-xs text-muted-foreground">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Broker Connections */}
      <div>
        <h2 className="text-lg font-semibold tracking-tight mb-4">Broker Connections</h2>
        <BrokerHealthGrid />
      </div>

      {/* Placeholder for future content */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Signal and trade activity will appear here once configured.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
