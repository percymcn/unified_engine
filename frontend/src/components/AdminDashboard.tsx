import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Alert, AlertDescription } from './ui/alert';
import {
  Users,
  Activity,
  Webhook,
  BarChart3,
  Settings,
  RefreshCw,
  Download,
  Search,
  UserPlus,
  Edit,
  Trash2,
  Shield,
  TrendingUp,
  DollarSign,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  LogOut,
  Key
} from 'lucide-react';
import { TradeFlowLogo } from './TradeFlowLogo';
import { AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { toast } from 'sonner@2.0.3';
import { AdminAccountsViewer } from './AdminAccountsViewer';

interface AdminDashboardProps {
  onLogout: () => void;
}

export function AdminDashboard({ onLogout }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterBroker, setFilterBroker] = useState('all');

  // Mock data - replace with real API calls
  const systemStats = {
    totalUsers: 1247,
    activeUsers: 894,
    totalTrades: 45230,
    totalVolume: 12.5, // Million
    mrr: 49680,
    churnRate: 2.3,
    activeConnections: 2341,
    errorRate: 0.4
  };

  const recentUsers = [
    { id: 1, name: 'John Doe', email: 'john@example.com', plan: 'Pro', status: 'active', joined: '2025-10-15', brokers: 2 },
    { id: 2, name: 'Jane Smith', email: 'jane@example.com', plan: 'Elite', status: 'active', joined: '2025-10-14', brokers: 3 },
    { id: 3, name: 'Bob Wilson', email: 'bob@example.com', plan: 'Starter', status: 'trial', joined: '2025-10-17', brokers: 1 },
    { id: 4, name: 'Alice Brown', email: 'alice@example.com', plan: 'Pro', status: 'active', joined: '2025-10-12', brokers: 2 }
  ];

  const webhookLogs = [
    { id: 1, timestamp: '2025-10-17 14:32:15', user: 'john@example.com', symbol: 'BTCUSD', action: 'BUY', broker: 'TradeLocker', status: 'success' },
    { id: 2, timestamp: '2025-10-17 14:31:42', user: 'jane@example.com', symbol: 'EURUSD', action: 'SELL', broker: 'Topstep', status: 'success' },
    { id: 3, timestamp: '2025-10-17 14:30:18', user: 'bob@example.com', symbol: 'GOLD', action: 'BUY', broker: 'MT5', status: 'error' },
    { id: 4, timestamp: '2025-10-17 14:29:55', user: 'alice@example.com', symbol: 'GBPUSD', action: 'SELL', broker: 'TradeLocker', status: 'success' }
  ];

  const tradesData = [
    { date: 'Oct 11', trades: 432, volume: 1.2 },
    { date: 'Oct 12', trades: 518, volume: 1.8 },
    { date: 'Oct 13', trades: 394, volume: 1.1 },
    { date: 'Oct 14', trades: 621, volume: 2.1 },
    { date: 'Oct 15', trades: 548, volume: 1.7 },
    { date: 'Oct 16', trades: 482, volume: 1.5 },
    { date: 'Oct 17', trades: 597, volume: 1.9 }
  ];

  const brokerDistribution = [
    { name: 'TradeLocker', value: 42, color: '#0EA5E9' },
    { name: 'Topstep', value: 31, color: '#10b981' },
    { name: 'MT4/MT5', value: 27, color: '#f59e0b' }
  ];

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { color: string; icon: any }> = {
      active: { color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
      trial: { color: 'bg-amber-100 text-amber-700 border-amber-200', icon: Clock },
      suspended: { color: 'bg-red-100 text-red-700 border-red-200', icon: XCircle },
      success: { color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
      error: { color: 'bg-red-100 text-red-700 border-red-200', icon: XCircle }
    };
    const config = variants[status] || variants.active;
    const Icon = config.icon;
    return (
      <Badge variant="outline" className={config.color}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Admin Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <TradeFlowLogo size="md" />
              <Badge className="bg-purple-100 text-purple-700 border-purple-200">
                <Shield className="w-3 h-3 mr-1" />
                Admin Portal
              </Badge>
            </div>
            <Button
              variant="outline"
              onClick={onLogout}
              className="border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="p-6 max-w-[1600px] mx-auto">
        {/* Admin Notice */}
        <Alert className="mb-6 bg-purple-50 border-purple-200">
          <Shield className="w-4 h-4 text-purple-600" />
          <AlertDescription className="text-purple-800">
            You are viewing the admin dashboard with full system access. All actions are logged.
          </AlertDescription>
        </Alert>

        {/* System Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card className="border-slate-200">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <Users className="w-5 h-5 text-blue-500" />
                <span className="text-sm text-green-600">+12%</span>
              </div>
              <p className="text-sm text-slate-600 mb-1">Total Users</p>
              <p className="text-2xl font-semibold text-slate-900">{systemStats.totalUsers.toLocaleString()}</p>
              <p className="text-xs text-slate-500 mt-1">{systemStats.activeUsers} active</p>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <Activity className="w-5 h-5 text-green-500" />
                <span className="text-sm text-green-600">+8%</span>
              </div>
              <p className="text-sm text-slate-600 mb-1">Total Trades</p>
              <p className="text-2xl font-semibold text-slate-900">{systemStats.totalTrades.toLocaleString()}</p>
              <p className="text-xs text-slate-500 mt-1">${systemStats.totalVolume}M volume</p>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <DollarSign className="w-5 h-5 text-emerald-500" />
                <span className="text-sm text-green-600">+15%</span>
              </div>
              <p className="text-sm text-slate-600 mb-1">MRR</p>
              <p className="text-2xl font-semibold text-slate-900">${(systemStats.mrr / 1000).toFixed(1)}K</p>
              <p className="text-xs text-slate-500 mt-1">Churn: {systemStats.churnRate}%</p>
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <Webhook className="w-5 h-5 text-purple-500" />
                <span className="text-sm text-red-600">{systemStats.errorRate}% errors</span>
              </div>
              <p className="text-sm text-slate-600 mb-1">Active Connections</p>
              <p className="text-2xl font-semibold text-slate-900">{systemStats.activeConnections.toLocaleString()}</p>
              <p className="text-xs text-slate-500 mt-1">Real-time webhooks</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-white border border-slate-200 p-1">
            <TabsTrigger value="overview" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700">
              <BarChart3 className="w-4 h-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="users" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700">
              <Users className="w-4 h-4 mr-2" />
              Users
            </TabsTrigger>
            <TabsTrigger value="accounts" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700">
              <Key className="w-4 h-4 mr-2" />
              Accounts & API Keys
            </TabsTrigger>
            <TabsTrigger value="webhooks" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700">
              <Webhook className="w-4 h-4 mr-2" />
              Webhook Logs
            </TabsTrigger>
            <TabsTrigger value="system" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700">
              <Settings className="w-4 h-4 mr-2" />
              System
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="mt-6 space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Trades Chart */}
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="text-slate-900">Daily Trades</CardTitle>
                  <CardDescription>Trade volume over the last 7 days</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={tradesData}>
                      <defs>
                        <linearGradient id="tradesGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" stroke="#64748b" style={{ fontSize: '12px' }} />
                      <YAxis stroke="#64748b" style={{ fontSize: '12px' }} />
                      <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px' }} />
                      <Area type="monotone" dataKey="trades" stroke="#0EA5E9" fillOpacity={1} fill="url(#tradesGradient)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Broker Distribution */}
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="text-slate-900">Broker Distribution</CardTitle>
                  <CardDescription>Active connections by broker</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={brokerDistribution}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={90}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {brokerDistribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="text-slate-900">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Button className="h-auto py-4 flex-col gap-2 bg-blue-500 hover:bg-blue-600">
                    <UserPlus className="w-5 h-5" />
                    <span>Add User</span>
                  </Button>
                  <Button className="h-auto py-4 flex-col gap-2 bg-green-500 hover:bg-green-600">
                    <RefreshCw className="w-5 h-5" />
                    <span>Sync Accounts</span>
                  </Button>
                  <Button className="h-auto py-4 flex-col gap-2 bg-purple-500 hover:bg-purple-600">
                    <Download className="w-5 h-5" />
                    <span>Export Data</span>
                  </Button>
                  <Button className="h-auto py-4 flex-col gap-2 bg-amber-500 hover:bg-amber-600">
                    <Settings className="w-5 h-5" />
                    <span>System Config</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Users Tab */}
          <TabsContent value="users" className="mt-6">
            <Card className="border-slate-200">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-slate-900">User Management</CardTitle>
                    <CardDescription>Manage all platform users and their accounts</CardDescription>
                  </div>
                  <Button className="bg-blue-500 hover:bg-blue-600">
                    <UserPlus className="w-4 h-4 mr-2" />
                    Add User
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {/* Filters */}
                <div className="flex gap-4 mb-6">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      placeholder="Search users..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10 bg-white border-slate-200"
                    />
                  </div>
                  <Select value={filterBroker} onValueChange={setFilterBroker}>
                    <SelectTrigger className="w-48 bg-white border-slate-200">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-white border-slate-200">
                      <SelectItem value="all">All Brokers</SelectItem>
                      <SelectItem value="tradelocker">TradeLocker</SelectItem>
                      <SelectItem value="topstep">Topstep</SelectItem>
                      <SelectItem value="mt4">MT4/MT5</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Users Table */}
                <div className="space-y-3">
                  {recentUsers.map((user) => (
                    <div key={user.id} className="p-4 bg-slate-50 rounded-lg border border-slate-200 hover:border-blue-300 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="font-medium text-slate-900">{user.name}</h4>
                            {getStatusBadge(user.status)}
                            <Badge variant="outline" className="border-slate-200 text-slate-600">
                              {user.plan}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-3 gap-4 text-sm">
                            <div>
                              <p className="text-xs text-slate-500">Email</p>
                              <p className="text-slate-700">{user.email}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-500">Connected Brokers</p>
                              <p className="text-slate-700">{user.brokers}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-500">Joined</p>
                              <p className="text-slate-700">{user.joined}</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" className="border-slate-200">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="outline" className="border-slate-200 text-red-600 hover:bg-red-50">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Accounts & API Keys Tab */}
          <TabsContent value="accounts" className="mt-6">
            <AdminAccountsViewer />
          </TabsContent>

          {/* Webhooks Tab */}
          <TabsContent value="webhooks" className="mt-6">
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="text-slate-900">Webhook Activity Logs</CardTitle>
                <CardDescription>Real-time webhook events and responses</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {webhookLogs.map((log) => (
                    <div key={log.id} className="p-4 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                      <div className="flex-1 grid grid-cols-6 gap-4 text-sm">
                        <div>
                          <p className="text-xs text-slate-500">Time</p>
                          <p className="text-slate-700 font-mono text-xs">{log.timestamp}</p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500">User</p>
                          <p className="text-slate-700">{log.user}</p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500">Symbol</p>
                          <p className="text-slate-700 font-semibold">{log.symbol}</p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500">Action</p>
                          <Badge className={log.action === 'BUY' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                            {log.action}
                          </Badge>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500">Broker</p>
                          <p className="text-slate-700">{log.broker}</p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500">Status</p>
                          {getStatusBadge(log.status)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* System Tab */}
          <TabsContent value="system" className="mt-6">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="text-slate-900">System Health</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                    <span className="text-sm text-slate-700">API Status</span>
                    <Badge className="bg-green-100 text-green-700">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Operational
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                    <span className="text-sm text-slate-700">Database</span>
                    <Badge className="bg-green-100 text-green-700">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Healthy
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                    <span className="text-sm text-slate-700">Webhooks</span>
                    <Badge className="bg-green-100 text-green-700">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Active
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <span className="text-sm text-slate-700">Cache</span>
                    <Badge className="bg-amber-100 text-amber-700">
                      <Clock className="w-3 h-3 mr-1" />
                      83% full
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle className="text-slate-900">Admin Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button variant="outline" className="w-full justify-start border-slate-200">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Sync All Accounts
                  </Button>
                  <Button variant="outline" className="w-full justify-start border-slate-200">
                    <Download className="w-4 h-4 mr-2" />
                    Export System Logs
                  </Button>
                  <Button variant="outline" className="w-full justify-start border-slate-200">
                    <Settings className="w-4 h-4 mr-2" />
                    Configure Instruments
                  </Button>
                  <Button variant="outline" className="w-full justify-start border-red-200 text-red-600 hover:bg-red-50">
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Clear Cache
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
