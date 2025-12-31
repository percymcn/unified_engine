import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Search, Filter, RefreshCw, Download, AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react';

interface LogsViewerProps {
  broker: 'tradelocker' | 'topstep' | 'truforex';
}

export function LogsViewer({ broker }: LogsViewerProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterLevel, setFilterLevel] = useState('all');
  const [filterType, setFilterType] = useState('all');

  const logs = [
    {
      id: 1,
      timestamp: '2025-10-14 14:32:18.245',
      level: 'error',
      type: 'order',
      message: 'Order rejected: Insufficient margin',
      details: {
        orderId: 'ORD-1005',
        symbol: 'GC',
        side: 'BUY',
        qty: 1,
        reason: 'Insufficient margin',
        accountBalance: 52430.00,
        requiredMargin: 75000.00
      },
      correlationId: 'req_abc123'
    },
    {
      id: 2,
      timestamp: '2025-10-14 14:30:45.102',
      level: 'info',
      type: 'order',
      message: 'Order filled successfully',
      details: {
        orderId: 'ORD-1004',
        symbol: 'ES',
        side: 'SELL',
        qty: 2,
        fillPrice: 4832.25,
        executionTime: 42
      },
      correlationId: 'req_def456'
    },
    {
      id: 3,
      timestamp: '2025-10-14 14:28:12.567',
      level: 'info',
      type: 'order',
      message: 'Stop order placed',
      details: {
        orderId: 'ORD-1003',
        symbol: 'RTY',
        side: 'BUY',
        qty: 3,
        stopPrice: 2050.00
      },
      correlationId: 'req_ghi789'
    },
    {
      id: 4,
      timestamp: '2025-10-14 14:25:30.891',
      level: 'info',
      type: 'order',
      message: 'Limit order placed',
      details: {
        orderId: 'ORD-1002',
        symbol: 'NQ',
        side: 'SELL',
        qty: 1,
        limitPrice: 16250.00
      },
      correlationId: 'req_jkl012'
    },
    {
      id: 5,
      timestamp: '2025-10-14 14:23:15.234',
      level: 'success',
      type: 'order',
      message: 'Market order filled',
      details: {
        orderId: 'ORD-1001',
        symbol: 'ES',
        side: 'BUY',
        qty: 2,
        fillPrice: 4825.50,
        executionTime: 38
      },
      correlationId: 'req_mno345'
    },
    {
      id: 6,
      timestamp: '2025-10-14 14:20:08.456',
      level: 'warning',
      type: 'risk',
      message: 'Approaching daily loss limit',
      details: {
        currentLoss: 425.50,
        maxDailyLoss: 500.00,
        utilizationPct: 85.1
      },
      correlationId: 'risk_check_001'
    },
    {
      id: 7,
      timestamp: '2025-10-14 14:18:32.789',
      level: 'info',
      type: 'webhook',
      message: 'Webhook received from TradingView',
      details: {
        source: 'tradingview',
        alertName: 'ES_Breakout_Long',
        payload: { symbol: 'ES', side: 'buy', type: 'market' },
        signature: 'valid',
        processingTime: 12
      },
      correlationId: 'wh_pqr678'
    },
    {
      id: 8,
      timestamp: '2025-10-14 14:15:08.123',
      level: 'success',
      type: 'position',
      message: 'Position closed with profit',
      details: {
        positionId: 'POS-5000',
        symbol: 'ES',
        side: 'LONG',
        entryPrice: 4820.00,
        exitPrice: 4845.50,
        pnl: 510.00,
        holdingTime: '2h 15m'
      },
      correlationId: 'req_stu901'
    },
    {
      id: 9,
      timestamp: '2025-10-14 14:12:45.678',
      level: 'error',
      type: 'risk',
      message: 'Trade blocked: Daily trade limit exceeded',
      details: {
        tradesExecutedToday: 10,
        maxTradesPerDay: 10,
        attemptedSymbol: 'RTY'
      },
      correlationId: 'risk_check_002'
    },
    {
      id: 10,
      timestamp: '2025-10-14 14:10:22.345',
      level: 'info',
      type: 'sync',
      message: 'Account positions synchronized',
      details: {
        accountId: 'ACC-123456',
        positionsFound: 3,
        syncDuration: 1245
      },
      correlationId: 'sync_vwx234'
    }
  ];

  const filteredLogs = logs.filter(log => {
    const matchesSearch = log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         log.correlationId.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         JSON.stringify(log.details).toLowerCase().includes(searchTerm.toLowerCase());
    const matchesLevel = filterLevel === 'all' || log.level === filterLevel;
    const matchesType = filterType === 'all' || log.type === filterType;
    return matchesSearch && matchesLevel && matchesType;
  });

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-[#00ffc2]" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      default:
        return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  const getLevelBadge = (level: string) => {
    const variants = {
      success: 'bg-[#00ffc2] text-[#002b36]',
      error: 'border-red-400 text-red-400',
      warning: 'border-yellow-400 text-yellow-400',
      info: 'border-blue-400 text-blue-400'
    };
    return variants[level as keyof typeof variants];
  };

  const getTypeBadge = (type: string) => {
    const variants = {
      order: 'border-purple-400 text-purple-400',
      position: 'border-[#00ffc2] text-[#00ffc2]',
      webhook: 'border-blue-400 text-blue-400',
      risk: 'border-yellow-400 text-yellow-400',
      sync: 'border-gray-400 text-gray-400'
    };
    return variants[type as keyof typeof variants] || 'border-gray-400 text-gray-400';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white mb-1">System Logs</h2>
          <p className="text-sm text-gray-400">Monitor events and errors for {broker}</p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            className="text-blue-400 hover:text-blue-300"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-gray-700 text-white"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Log Stats */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Total Logs</p>
            <p className="text-white text-2xl">{logs.length}</p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Errors</p>
            <p className="text-red-400 text-2xl">
              {logs.filter(l => l.level === 'error').length}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Warnings</p>
            <p className="text-yellow-400 text-2xl">
              {logs.filter(l => l.level === 'warning').length}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Success</p>
            <p className="text-[#00ffc2] text-2xl">
              {logs.filter(l => l.level === 'success').length}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Info</p>
            <p className="text-blue-400 text-2xl">
              {logs.filter(l => l.level === 'info').length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-[#002b36] border-gray-700 text-white"
              />
            </div>
            <div className="w-48">
              <Select value={filterLevel} onValueChange={setFilterLevel}>
                <SelectTrigger className="bg-[#002b36] border-gray-700 text-white">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#002b36] border-gray-700">
                  <SelectItem value="all">All Levels</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-48">
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="bg-[#002b36] border-gray-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#002b36] border-gray-700">
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="order">Orders</SelectItem>
                  <SelectItem value="position">Positions</SelectItem>
                  <SelectItem value="webhook">Webhooks</SelectItem>
                  <SelectItem value="risk">Risk</SelectItem>
                  <SelectItem value="sync">Sync</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs List */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">
            Event Log ({filteredLogs.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {filteredLogs.map((log) => (
              <div
                key={log.id}
                className="p-4 bg-[#002b36] rounded-lg border border-gray-800"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-1">
                    {getLevelIcon(log.level)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-gray-400 font-mono">
                        {log.timestamp}
                      </span>
                      <Badge
                        variant={log.level === 'success' ? 'default' : 'outline'}
                        className={getLevelBadge(log.level)}
                      >
                        {log.level}
                      </Badge>
                      <Badge variant="outline" className={getTypeBadge(log.type)}>
                        {log.type}
                      </Badge>
                      <span className="text-xs text-gray-400 font-mono">
                        {log.correlationId}
                      </span>
                    </div>
                    <p className="text-white mb-2">{log.message}</p>
                    <details className="text-sm">
                      <summary className="text-gray-400 cursor-pointer hover:text-white">
                        View details
                      </summary>
                      <div className="mt-2 p-3 bg-[#001f29] rounded border border-gray-800 overflow-x-auto">
                        <pre className="text-xs text-gray-300">
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      </div>
                    </details>
                  </div>
                </div>
              </div>
            ))}

            {filteredLogs.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-400">No logs found</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
