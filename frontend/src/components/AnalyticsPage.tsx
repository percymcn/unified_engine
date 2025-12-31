import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { 
  TrendingUp, 
  TrendingDown, 
  Users, 
  Activity, 
  DollarSign,
  BarChart3,
  PieChart,
  AlertCircle
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  PieChart as RechartsPie, 
  Pie, 
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';
import { useUser } from '../contexts/UserContext';

interface AnalyticsPageProps {
  broker?: string;
}

export function AnalyticsPage({ broker = 'all' }: AnalyticsPageProps) {
  const { isAdmin } = useUser();
  const [timeRange, setTimeRange] = useState('7d');
  const [selectedBroker, setSelectedBroker] = useState(broker);

  // Mock data - replace with real API calls
  const kpiData = {
    totalTrades: 1248,
    totalTradesChange: '+12.5%',
    activeUsers: isAdmin ? 189 : 1,
    activeUsersChange: isAdmin ? '+8.3%' : '0%',
    totalPnL: 45230.50,
    totalPnLChange: '+23.4%',
    winRate: 67.8,
    winRateChange: '+2.1%'
  };

  const tradesOverTime = [
    { date: 'Oct 10', trades: 45, pnl: 1250 },
    { date: 'Oct 11', trades: 52, pnl: 1890 },
    { date: 'Oct 12', trades: 38, pnl: -450 },
    { date: 'Oct 13', trades: 61, pnl: 2340 },
    { date: 'Oct 14', trades: 55, pnl: 1670 },
    { date: 'Oct 15', trades: 48, pnl: 890 },
    { date: 'Oct 16', trades: 58, pnl: 2120 }
  ];

  const pnlDistribution = [
    { date: 'Oct 10', profit: 2250, loss: 1000 },
    { date: 'Oct 11', profit: 3890, loss: 2000 },
    { date: 'Oct 12', profit: 1550, loss: 2000 },
    { date: 'Oct 13', profit: 4340, loss: 2000 },
    { date: 'Oct 14', profit: 3670, loss: 2000 },
    { date: 'Oct 15', profit: 2890, loss: 2000 },
    { date: 'Oct 16', profit: 4120, loss: 2000 }
  ];

  const brokerDistribution = [
    { name: 'TradeLocker', value: 45, color: '#3B82F6' },
    { name: 'Topstep', value: 35, color: '#A855F7' },
    { name: 'MT4/MT5', value: 20, color: '#10B981' }
  ];

  const alertsPerDay = [
    { date: 'Oct 10', alerts: 12 },
    { date: 'Oct 11', alerts: 15 },
    { date: 'Oct 12', alerts: 9 },
    { date: 'Oct 13', alerts: 18 },
    { date: 'Oct 14', alerts: 14 },
    { date: 'Oct 15', alerts: 11 },
    { date: 'Oct 16', alerts: 16 }
  ];

  const topPerformingStrategies = [
    { name: 'Breakout Scalper', trades: 234, winRate: 72.5, pnl: 12450 },
    { name: 'Trend Following', trades: 189, winRate: 68.2, pnl: 9870 },
    { name: 'Mean Reversion', trades: 156, winRate: 64.1, pnl: 7340 },
    { name: 'Grid Trading', trades: 145, winRate: 61.3, pnl: 5620 }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-white mb-1">Analytics & KPIs</h2>
          <p className="text-sm text-gray-400">
            {isAdmin ? 'System-wide performance metrics and insights' : 'Your trading performance metrics and insights'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedBroker} onValueChange={setSelectedBroker}>
            <SelectTrigger className="w-[180px] bg-[#001f29] border-gray-800 text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#002b36] border-gray-700">
              <SelectItem value="all">All Brokers</SelectItem>
              <SelectItem value="tradelocker">TradeLocker</SelectItem>
              <SelectItem value="topstep">Topstep</SelectItem>
              <SelectItem value="mt4">MT4/MT5</SelectItem>
            </SelectContent>
          </Select>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[140px] bg-[#001f29] border-gray-800 text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#002b36] border-gray-700">
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="90d">Last 90 Days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <Activity className="w-5 h-5 text-[#00ffc2]" />
              <Badge variant="outline" className="border-green-400 text-green-400 text-xs">
                {kpiData.totalTradesChange}
              </Badge>
            </div>
            <p className="text-sm text-gray-400 mb-1">Total Trades</p>
            <p className="text-white text-2xl">{kpiData.totalTrades.toLocaleString()}</p>
          </CardContent>
        </Card>

        {isAdmin && (
          <Card className="bg-[#001f29] border-gray-800">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <Users className="w-5 h-5 text-blue-400" />
                <Badge variant="outline" className="border-green-400 text-green-400 text-xs">
                  {kpiData.activeUsersChange}
                </Badge>
              </div>
              <p className="text-sm text-gray-400 mb-1">Active Users</p>
              <p className="text-white text-2xl">{kpiData.activeUsers}</p>
            </CardContent>
          </Card>
        )}

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <DollarSign className="w-5 h-5 text-green-400" />
              <Badge variant="outline" className="border-green-400 text-green-400 text-xs">
                {kpiData.totalPnLChange}
              </Badge>
            </div>
            <p className="text-sm text-gray-400 mb-1">Total P&L</p>
            <p className="text-[#00ffc2] text-2xl">${kpiData.totalPnL.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-5 h-5 text-purple-400" />
              <Badge variant="outline" className="border-green-400 text-green-400 text-xs">
                {kpiData.winRateChange}
              </Badge>
            </div>
            <p className="text-sm text-gray-400 mb-1">Win Rate</p>
            <p className="text-white text-2xl">{kpiData.winRate}%</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Trades Over Time */}
        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Trades Over Time</CardTitle>
            <CardDescription className="text-gray-400">Daily trade volume</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={tradesOverTime}>
                <defs>
                  <linearGradient id="tradesGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00ffc2" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#00ffc2" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
                <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#001f29', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="trades" 
                  stroke="#00ffc2" 
                  fillOpacity={1}
                  fill="url(#tradesGradient)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* P&L Distribution */}
        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">P&L Distribution</CardTitle>
            <CardDescription className="text-gray-400">Profit vs Loss breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={pnlDistribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
                <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#001f29', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Bar dataKey="profit" fill="#10B981" name="Profit" />
                <Bar dataKey="loss" fill="#EF4444" name="Loss" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Broker Distribution */}
        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Broker Distribution</CardTitle>
            <CardDescription className="text-gray-400">Trades by broker</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <RechartsPie>
                <Pie
                  data={brokerDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {brokerDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#001f29', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                />
              </RechartsPie>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Alerts Per Day */}
        <Card className="bg-[#001f29] border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Alerts Per Day</CardTitle>
            <CardDescription className="text-gray-400">TradingView webhook activity</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={alertsPerDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
                <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#001f29', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="alerts" 
                  stroke="#A855F7" 
                  strokeWidth={2}
                  dot={{ fill: '#A855F7', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Top Performing Strategies */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Top Performing Strategies</CardTitle>
          <CardDescription className="text-gray-400">Best strategies by P&L</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {topPerformingStrategies.map((strategy, index) => (
              <div 
                key={strategy.name}
                className="p-4 bg-[#002b36] rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-[#00ffc2]/10 flex items-center justify-center">
                      <span className="text-[#00ffc2]">#{index + 1}</span>
                    </div>
                    <div>
                      <h4 className="text-white mb-1">{strategy.name}</h4>
                      <p className="text-sm text-gray-400">{strategy.trades} trades</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-sm text-gray-400">Win Rate</p>
                      <p className="text-white">{strategy.winRate}%</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-400">P&L</p>
                      <p className="text-[#00ffc2]">${strategy.pnl.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
