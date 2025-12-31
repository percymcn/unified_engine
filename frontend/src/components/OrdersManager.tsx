import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Search, Filter, RefreshCw, X } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface OrdersManagerProps {
  broker: 'tradelocker' | 'topstep' | 'truforex';
}

const INITIAL_ORDERS = [
  {
    id: 'ORD-1001',
    symbol: 'ES',
    side: 'BUY',
    type: 'MARKET',
    qty: 2,
    price: null,
    filledQty: 2,
    avgFillPrice: 4825.50,
    status: 'FILLED',
    timestamp: '2025-10-14 14:23:15',
    tag: 'ES_Breakout_Long'
  },
  {
    id: 'ORD-1002',
    symbol: 'NQ',
    side: 'SELL',
    type: 'LIMIT',
    qty: 1,
    price: 16250.00,
    filledQty: 0,
    avgFillPrice: null,
    status: 'PENDING',
    timestamp: '2025-10-14 14:25:30',
    tag: 'NQ_Supply_Zone'
  },
  {
    id: 'ORD-1003',
    symbol: 'RTY',
    side: 'BUY',
    type: 'STOP',
    qty: 3,
    price: 2050.00,
    filledQty: 0,
    avgFillPrice: null,
    status: 'PENDING',
    timestamp: '2025-10-14 14:28:12',
    tag: 'RTY_Momentum'
  },
  {
    id: 'ORD-1004',
    symbol: 'ES',
    side: 'SELL',
    type: 'MARKET',
    qty: 2,
    price: null,
    filledQty: 2,
    avgFillPrice: 4832.25,
    status: 'FILLED',
    timestamp: '2025-10-14 14:30:45',
    tag: 'ES_Exit'
  },
  {
    id: 'ORD-1005',
    symbol: 'GC',
    side: 'BUY',
    type: 'LIMIT',
    qty: 1,
    price: 2650.00,
    filledQty: 0,
    avgFillPrice: null,
    status: 'REJECTED',
    timestamp: '2025-10-14 14:32:18',
    tag: 'GC_Support',
    rejectReason: 'Insufficient margin'
  }
];

export function OrdersManager({ broker }: OrdersManagerProps) {
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [orders, setOrders] = useState(INITIAL_ORDERS);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const filteredOrders = orders.filter(order => {
    const matchesStatus = filterStatus === 'all' || order.status.toLowerCase() === filterStatus.toLowerCase();
    const matchesSearch = order.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         order.tag.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Simulate API call to refresh orders
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // In production, this would fetch fresh data from the API
      // For now, reset to initial orders
      setOrders([...INITIAL_ORDERS]);
      
      toast.success('Orders refreshed successfully');
    } catch (error) {
      toast.error('Failed to refresh orders');
      console.error('Error refreshing orders:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleCancelOrder = async (orderId: string) => {
    try {
      // Find the order to get its symbol for the toast message
      const order = orders.find(o => o.id === orderId);
      
      // Optimistically update the UI
      setOrders(prevOrders =>
        prevOrders.map(o =>
          o.id === orderId ? { ...o, status: 'CANCELLED' } : o
        )
      );

      // Simulate API call to cancel the order
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // In production, this would call the actual API:
      // await apiClient.cancelOrder(broker, orderId);
      
      toast.success(`Order ${order?.symbol || orderId} cancelled successfully`);
    } catch (error) {
      // Revert the optimistic update on error
      setOrders(prevOrders =>
        prevOrders.map(o =>
          o.id === orderId ? { ...o, status: 'PENDING' } : o
        )
      );
      toast.error('Failed to cancel order');
      console.error('Error cancelling order:', orderId, error);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      FILLED: 'bg-[#00ffc2] text-[#002b36]',
      PENDING: 'border-yellow-400 text-yellow-400',
      REJECTED: 'border-red-400 text-red-400',
      CANCELLED: 'border-gray-400 text-gray-400'
    };
    return variants[status as keyof typeof variants] || 'border-gray-400 text-gray-400';
  };

  const getSideBadge = (side: string) => {
    return side === 'BUY'
      ? 'border-[#00ffc2] text-[#00ffc2]'
      : 'border-red-400 text-red-400';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white mb-1">Order Management</h2>
          <p className="text-sm text-gray-400">View and manage orders for {broker}</p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="text-blue-400 hover:text-blue-300 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search by symbol or tag..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-[#002b36] border-gray-700 text-white"
              />
            </div>
            <div className="w-48">
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="bg-[#002b36] border-gray-700 text-white">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#002b36] border-gray-700">
                  <SelectItem value="all">All Orders</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="filled">Filled</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Orders Table */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">
            Orders ({filteredOrders.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {filteredOrders.map((order) => (
              <div
                key={order.id}
                className="p-4 bg-[#002b36] rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-white">{order.symbol}</span>
                      <Badge variant="outline" className={getSideBadge(order.side)}>
                        {order.side}
                      </Badge>
                      <Badge variant="outline" className="border-gray-600 text-gray-300">
                        {order.type}
                      </Badge>
                      <Badge
                        variant={order.status === 'FILLED' ? 'default' : 'outline'}
                        className={getStatusBadge(order.status)}
                      >
                        {order.status}
                      </Badge>
                      <span className="text-xs text-gray-400">{order.id}</span>
                    </div>
                    
                    <div className="grid grid-cols-5 gap-4 text-sm">
                      <div>
                        <p className="text-xs text-gray-400">Quantity</p>
                        <p className="text-white">
                          {order.filledQty > 0 ? `${order.filledQty}/${order.qty}` : order.qty}
                        </p>
                      </div>
                      
                      {order.price && (
                        <div>
                          <p className="text-xs text-gray-400">Limit Price</p>
                          <p className="text-white">${order.price.toFixed(2)}</p>
                        </div>
                      )}
                      
                      {order.avgFillPrice && (
                        <div>
                          <p className="text-xs text-gray-400">Avg Fill</p>
                          <p className="text-[#00ffc2]">${order.avgFillPrice.toFixed(2)}</p>
                        </div>
                      )}
                      
                      <div>
                        <p className="text-xs text-gray-400">Time</p>
                        <p className="text-white">{order.timestamp.split(' ')[1]}</p>
                      </div>
                      
                      <div>
                        <p className="text-xs text-gray-400">Tag</p>
                        <p className="text-white truncate">{order.tag}</p>
                      </div>
                    </div>

                    {order.rejectReason && (
                      <div className="mt-2 p-2 bg-red-950 border border-red-800 rounded">
                        <p className="text-xs text-red-300">
                          <strong>Reject Reason:</strong> {order.rejectReason}
                        </p>
                      </div>
                    )}
                  </div>

                  {(order.status === 'PENDING' || order.status === 'CANCELLED') && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCancelOrder(order.id)}
                      disabled={order.status === 'CANCELLED'}
                      className="text-red-400 hover:text-red-300 hover:bg-red-950 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <X className="w-4 h-4 mr-1" />
                      {order.status === 'CANCELLED' ? 'Cancelled' : 'Cancel'}
                    </Button>
                  )}
                </div>
              </div>
            ))}

            {filteredOrders.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-400">No orders found</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Order Statistics */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Total Orders</p>
            <p className="text-white text-2xl">{orders.length}</p>
          </CardContent>
        </Card>
        
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Filled</p>
            <p className="text-[#00ffc2] text-2xl">
              {orders.filter(o => o.status === 'FILLED').length}
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Pending</p>
            <p className="text-yellow-400 text-2xl">
              {orders.filter(o => o.status === 'PENDING').length}
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Rejected</p>
            <p className="text-red-400 text-2xl">
              {orders.filter(o => o.status === 'REJECTED').length}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
