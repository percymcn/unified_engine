import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, Users, Signal, TrendingUp } from 'lucide-react';

export default function DashboardPage() {
  // Placeholder stats - will be populated with real data in Phase 8
  const stats = [
    {
      title: 'Active Signals',
      value: '-',
      description: 'Pending signals today',
      icon: Signal,
      iconColor: 'text-primary',
    },
    {
      title: 'Connected Brokers',
      value: '-',
      description: 'Active broker connections',
      icon: Users,
      iconColor: 'text-chart-2',
    },
    {
      title: "Today's Trades",
      value: '-',
      description: 'Executed today',
      icon: Activity,
      iconColor: 'text-chart-3',
    },
    {
      title: 'Total Balance',
      value: '-',
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
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.iconColor}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
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
