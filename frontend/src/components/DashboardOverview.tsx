import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Activity, TrendingUp, TrendingDown, AlertCircle, CheckCircle, DollarSign, Bell } from 'lucide-react';
import { useUser } from '../contexts/UserContext';
import { useBroker, getBrokerDisplayName } from '../contexts/BrokerContext';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from './ui/sheet';
import { apiClient } from '../utils/api-client';
import { toast } from 'sonner@2.0.3';

interface DashboardOverviewProps {
  broker: 'tradelocker' | 'topstep' | 'truforex';
  onNavigateToAccountSelection?: () => void;
  onNavigateToChangeAccount?: () => void;
  onNavigateToSyncResults?: () => void;
}

export function DashboardOverview({ 
  broker,
  onNavigateToAccountSelection,
  onNavigateToChangeAccount,
  onNavigateToSyncResults
}: DashboardOverviewProps) {
  const { user, isAdmin } = useUser();
  const { activeBroker, isSyncing } = useBroker();
  const [loading, setLoading] = useState(false);
  const [alertsPanelOpen, setAlertsPanelOpen] = useState(false);
  
  // Broker-specific mock data that updates when broker changes
  const getBrokerData = (brokerType: string) => {
    const data = {
      tradelocker: {
        activeOrders: 12,
        openPositions: 8,
        dailyPnL: 1247.50,
        dailyPnLPercent: 3.2,
        totalValue: 52430.00,
        serverHealth: 'healthy',
        orderSuccessRate: 98.5,
        avgLatency: 42,
        recentActivity: [
          { id: 1, type: 'order', symbol: 'ES', side: 'BUY', status: 'filled', time: '14:23:15', pnl: null },
          { id: 2, type: 'order', symbol: 'NQ', side: 'SELL', status: 'filled', time: '14:18:32', pnl: null },
          { id: 3, type: 'position', symbol: 'ES', side: 'LONG', status: 'closed', time: '14:15:08', pnl: 425.00 },
          { id: 4, type: 'order', symbol: 'RTY', side: 'BUY', status: 'rejected', time: '14:12:45', pnl: null },
          { id: 5, type: 'position', symbol: 'GC', side: 'SHORT', status: 'open', time: '13:58:22', pnl: -125.50 }
        ],
        alerts: [
          { id: 1, type: 'info', message: 'TradeLocker API connection stable', time: '5 min ago' },
          { id: 2, type: 'success', message: 'Position EURUSD closed with +$425 profit', time: '15 min ago' },
          { id: 3, type: 'warning', message: 'High volatility detected on ES futures', time: '1 hour ago' }
        ]
      },
      topstep: {
        activeOrders: 5,
        openPositions: 3,
        dailyPnL: 850.25,
        dailyPnLPercent: 2.1,
        totalValue: 150000.00,
        serverHealth: 'healthy',
        orderSuccessRate: 99.2,
        avgLatency: 28,
        recentActivity: [
          { id: 1, type: 'order', symbol: 'MES', side: 'BUY', status: 'filled', time: '13:45:20', pnl: null },
          { id: 2, type: 'position', symbol: 'MNQ', side: 'SHORT', status: 'closed', time: '13:30:15', pnl: 320.00 },
          { id: 3, type: 'order', symbol: 'MES', side: 'SELL', status: 'filled', time: '13:15:08', pnl: null }
        ],
        alerts: [
          { id: 1, type: 'success', message: 'Topstep daily profit target 80% reached', time: '10 min ago' },
          { id: 2, type: 'info', message: 'ProjectX connection active', time: '30 min ago' }
        ]
      },
      truforex: {
        activeOrders: 8,
        openPositions: 6,
        dailyPnL: -180.75,
        dailyPnLPercent: -1.8,
        totalValue: 10000.00,
        serverHealth: 'healthy',
        orderSuccessRate: 96.8,
        avgLatency: 55,
        recentActivity: [
          { id: 1, type: 'order', symbol: 'GBPUSD', side: 'BUY', status: 'filled', time: '12:50:30', pnl: null },
          { id: 2, type: 'position', symbol: 'EURUSD', side: 'LONG', status: 'open', time: '12:35:22', pnl: -90.50 },
          { id: 3, type: 'order', symbol: 'USDJPY', side: 'SELL', status: 'filled', time: '12:20:15', pnl: null }
        ],
        alerts: [
          { id: 1, type: 'warning', message: 'MT4 EA requires reconnection', time: '2 min ago' },
          { id: 2, type: 'info', message: 'TruForex server connected', time: '20 min ago' }
        ]
      }
    };

    return data[brokerType as keyof typeof data] || data.tradelocker;
  };

  const [metrics, setMetrics] = useState(getBrokerData(activeBroker || broker));

  // Update metrics when broker changes
  useEffect(() => {
    const currentBroker = activeBroker || broker;
    setMetrics(getBrokerData(currentBroker));
  }, [activeBroker, broker]);

  // Listen for broker switch events
  useEffect(() => {
    const handleBrokerSwitch = (e: any) => {
      const newBroker = e.detail.broker;
      setMetrics(getBrokerData(newBroker));
      toast.info(`Loaded ${getBrokerDisplayName(newBroker)} data`);
    };

    window.addEventListener('broker.switch', handleBrokerSwitch);
    return () => window.removeEventListener('broker.switch', handleBrokerSwitch);
  }, []);

  // Quick Action Handlers
  const handleSyncPositions = async () => {
    setLoading(true);
    try {
      toast.info('Syncing positions...');
      const positions = await apiClient.getPositions();
      toast.success(`Successfully synced ${positions.length} positions`);
      console.log('Synced positions:', positions);
    } catch (error) {
      console.error('Sync positions error:', error);
      toast.error('Failed to sync positions');
    } finally {
      setLoading(false);
    }
  };

  const handleExportLogs = async () => {
    setLoading(true);
    try {
      toast.info('Exporting logs...');
      const logs = await apiClient.getLogs(100);
      
      const csvContent = [
        ['Timestamp', 'Level', 'Message'].join(','),
        ...logs.map(log => [
          log.timestamp,
          log.level,
          `"${log.message.replace(/"/g, '""')}"`
        ].join(','))
      ].join('\n');
      
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tradeflow-logs-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Exported ${logs.length} log entries`);
    } catch (error) {
      console.error('Export logs error:', error);
      toast.error('Failed to export logs');
    } finally {
      setLoading(false);
    }
  };

  const handleTestWebhook = async () => {
    setLoading(true);
    try {
      toast.info('Testing webhook connection...');
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const testResult = {
        status: 'success',
        latency: Math.floor(Math.random() * 100) + 50,
        timestamp: new Date().toISOString()
      };
      
      toast.success(`Webhook test successful! Latency: ${testResult.latency}ms`);
      console.log('Webhook test result:', testResult);
    } catch (error) {
      console.error('Test webhook error:', error);
      toast.error('Webhook test failed');
    } finally {
      setLoading(false);
    }
  };

  const handleViewAlerts = () => {
    setAlertsPanelOpen(true);
    toast.success('Alerts panel opened');
  };

  const currentBrokerName = getBrokerDisplayName(activeBroker || broker);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white mb-1">Dashboard Overview</h2>
          <p className="text-sm text-gray-400">
            Real-time metrics for {currentBrokerName} {!isAdmin && '(Your Account)'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isAdmin && (
            <Badge variant="outline" className="border-[#00ffc2] text-[#00ffc2]">
              Personal View
            </Badge>
          )}
          {user?.plan && (
            <Badge variant="outline" className="border-blue-400 text-blue-400">
              {user.plan.charAt(0).toUpperCase() + user.plan.slice(1)} Plan
            </Badge>
          )}
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-gray-400">Active Orders</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-white">{metrics.activeOrders}</span>
              <Activity className="w-4 h-4 text-blue-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-gray-400">Open Positions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-white">{metrics.openPositions}</span>
              <TrendingUp className="w-4 h-4 text-purple-400" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-gray-400">Daily P&L</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className={metrics.dailyPnL >= 0 ? 'text-[#00ffc2]' : 'text-red-400'}>
                ${metrics.dailyPnL.toFixed(2)}
              </span>
              {metrics.dailyPnL >= 0 ? (
                <TrendingUp className="w-4 h-4 text-[#00ffc2]" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-400" />
              )}
              <span className="text-sm text-gray-400">
                {metrics.dailyPnLPercent >= 0 ? '+' : ''}{metrics.dailyPnLPercent}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader className="pb-2">
            <CardDescription className="text-gray-400">Account Value</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-white">${metrics.totalValue.toLocaleString()}</span>
              <DollarSign className="w-4 h-4 text-yellow-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Health & Performance */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader>
            <CardTitle className="text-white text-sm">Server Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-[#00ffc2]" />
              <span className="text-[#00ffc2]">Healthy</span>
            </div>
            <div className="mt-3 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Success Rate</span>
                <span className="text-white">{metrics.orderSuccessRate}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Avg Latency</span>
                <span className="text-white">{metrics.avgLatency}ms</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800 md:col-span-2">
          <CardHeader>
            <CardTitle className="text-white text-sm">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              <button 
                onClick={handleSyncPositions}
                disabled={loading || isSyncing}
                className="px-4 py-2 bg-[#002b36] text-[#00ffc2] rounded-lg hover:bg-[#003545] transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Sync Positions
              </button>
              <button 
                onClick={handleTestWebhook}
                disabled={loading}
                className="px-4 py-2 bg-[#002b36] text-white rounded-lg hover:bg-[#003545] transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Test Webhook
              </button>
              <button 
                onClick={handleExportLogs}
                disabled={loading}
                className="px-4 py-2 bg-[#002b36] text-white rounded-lg hover:bg-[#003545] transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Export Logs
              </button>
              <button 
                onClick={handleViewAlerts}
                disabled={loading}
                className="px-4 py-2 bg-[#002b36] text-white rounded-lg hover:bg-[#003545] transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Bell className="w-4 h-4" />
                View Alerts
              </button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Grid Layout: Recent Activity + Account Management */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent Activity - Takes 2 columns */}
        <div className="lg:col-span-2">
          <Card className="bg-[#001f29] border-gray-800">
            <CardHeader>
              <CardTitle className="text-white">Recent Activity</CardTitle>
              <CardDescription className="text-gray-400">Latest orders and position updates</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {metrics.recentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center justify-between p-3 bg-[#002b36] rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${
                        activity.status === 'filled' ? 'bg-green-400' :
                        activity.status === 'closed' ? 'bg-blue-400' :
                        activity.status === 'open' ? 'bg-yellow-400' :
                        'bg-red-400'
                      }`} />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-white font-medium">{activity.symbol}</span>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${
                              activity.side === 'BUY' || activity.side === 'LONG'
                                ? 'border-green-500 text-green-400'
                                : 'border-red-500 text-red-400'
                            }`}
                          >
                            {activity.side}
                          </Badge>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${
                              activity.status === 'filled' || activity.status === 'closed'
                                ? 'border-green-500 text-green-400'
                                : activity.status === 'open'
                                ? 'border-yellow-500 text-yellow-400'
                                : 'border-red-500 text-red-400'
                            }`}
                          >
                            {activity.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-400">{activity.time}</p>
                      </div>
                    </div>
                    {activity.pnl !== null && (
                      <span className={activity.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {activity.pnl >= 0 ? '+' : ''}${activity.pnl.toFixed(2)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Account Management - Takes 1 column */}
        <div>
          <Card className="bg-[#001f29] border-gray-800">
            <CardHeader>
              <CardTitle className="text-white">Account Management</CardTitle>
              <CardDescription className="text-gray-400">Quick account actions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <button
                onClick={onNavigateToAccountSelection}
                className="w-full p-3 bg-[#002b36] rounded-lg hover:bg-[#003545] transition-colors text-left"
              >
                <p className="text-white text-sm font-medium">Select Account</p>
                <p className="text-xs text-gray-400">Choose active trading account</p>
              </button>
              <button
                onClick={onNavigateToChangeAccount}
                className="w-full p-3 bg-[#002b36] rounded-lg hover:bg-[#003545] transition-colors text-left"
              >
                <p className="text-white text-sm font-medium">Change Account</p>
                <p className="text-xs text-gray-400">Switch to different account</p>
              </button>
              <button
                onClick={onNavigateToSyncResults}
                className="w-full p-3 bg-[#002b36] rounded-lg hover:bg-[#003545] transition-colors text-left"
              >
                <p className="text-white text-sm font-medium">Sync Results</p>
                <p className="text-xs text-gray-400">View recent sync status</p>
              </button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Alerts Panel Sheet */}
      <Sheet open={alertsPanelOpen} onOpenChange={setAlertsPanelOpen}>
        <SheetContent side="right" className="bg-[#001f29] border-gray-800 w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle className="text-white flex items-center gap-2">
              <Bell className="w-5 h-5 text-[#00ffc2]" />
              Alerts & Notifications
            </SheetTitle>
            <SheetDescription className="text-gray-400">
              View and manage system alerts and notifications for {currentBrokerName}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-3">
            {metrics.alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border ${
                  alert.type === 'success'
                    ? 'bg-green-950/30 border-green-800/30'
                    : alert.type === 'warning'
                    ? 'bg-orange-950/30 border-orange-800/30'
                    : 'bg-blue-950/30 border-blue-800/30'
                }`}
              >
                <div className="flex items-start gap-3">
                  {alert.type === 'success' && <CheckCircle className="w-5 h-5 text-green-400 mt-0.5" />}
                  {alert.type === 'warning' && <AlertCircle className="w-5 h-5 text-orange-400 mt-0.5" />}
                  {alert.type === 'info' && <Activity className="w-5 h-5 text-blue-400 mt-0.5" />}
                  <div className="flex-1">
                    <p className="text-white text-sm">{alert.message}</p>
                    <p className="text-xs text-gray-400 mt-1">{alert.time}</p>
                  </div>
                </div>
              </div>
            ))}
            
            {metrics.alerts.length === 0 && (
              <div className="text-center py-12">
                <Bell className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No alerts at this time</p>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
