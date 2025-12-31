import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Label } from './ui/label';
import { TrendingUp, TrendingDown, X, RefreshCw } from 'lucide-react';
import { apiClient } from '../utils/api-client';
import { toast } from 'sonner@2.0.3';

interface PositionsMonitorProps {
  broker: 'tradelocker' | 'topstep' | 'truforex';
}

export function PositionsMonitor({ broker }: PositionsMonitorProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [modifyDialogOpen, setModifyDialogOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<any>(null);
  const [newStopLoss, setNewStopLoss] = useState('');
  const [newTakeProfit, setNewTakeProfit] = useState('');

  const positions = [
    {
      id: 'POS-5001',
      symbol: 'ES',
      side: 'LONG',
      qty: 2,
      entryPrice: 4825.50,
      currentPrice: 4832.25,
      unrealizedPnL: 135.00,
      unrealizedPnLPct: 2.8,
      stopLoss: 4815.00,
      takeProfit: 4850.00,
      openTime: '2025-10-14 14:23:15',
      tag: 'ES_Breakout_Long'
    },
    {
      id: 'POS-5002',
      symbol: 'NQ',
      side: 'SHORT',
      qty: 1,
      entryPrice: 16245.00,
      currentPrice: 16260.50,
      unrealizedPnL: -155.00,
      unrealizedPnLPct: -0.95,
      stopLoss: 16280.00,
      takeProfit: 16200.00,
      openTime: '2025-10-14 13:45:22',
      tag: 'NQ_Reversal_Short'
    },
    {
      id: 'POS-5003',
      symbol: 'RTY',
      side: 'LONG',
      qty: 3,
      entryPrice: 2048.75,
      currentPrice: 2052.00,
      unrealizedPnL: 97.50,
      unrealizedPnLPct: 1.58,
      stopLoss: 2042.00,
      takeProfit: 2065.00,
      openTime: '2025-10-14 12:18:45',
      tag: 'RTY_Support_Bounce'
    }
  ];

  const filteredPositions = positions.filter(pos =>
    pos.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    pos.tag.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalPnL = positions.reduce((sum, pos) => sum + pos.unrealizedPnL, 0);
  const totalPnLPct = positions.reduce((sum, pos) => sum + pos.unrealizedPnLPct, 0) / positions.length;

  const handleSync = async () => {
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

  const handleClosePosition = async (positionId: string) => {
    if (!window.confirm('Are you sure you want to close this position?')) {
      return;
    }

    setLoading(true);
    try {
      toast.info('Closing position...');
      const result = await apiClient.closePosition(positionId);
      toast.success(`Position closed successfully. P&L: ${result.pnl >= 0 ? '+' : ''}${result.pnl.toFixed(2)}`);
      console.log('Closed position:', positionId, result);
      
      // Refresh positions after closing
      await handleSync();
    } catch (error) {
      console.error('Close position error:', error);
      toast.error('Failed to close position');
    } finally {
      setLoading(false);
    }
  };

  const handleModifyPosition = (position: any) => {
    setSelectedPosition(position);
    setNewStopLoss(position.stopLoss.toString());
    setNewTakeProfit(position.takeProfit.toString());
    setModifyDialogOpen(true);
  };

  const handleSaveModification = async () => {
    if (!selectedPosition) return;

    setLoading(true);
    try {
      const stopLossValue = parseFloat(newStopLoss);
      const takeProfitValue = parseFloat(newTakeProfit);

      if (isNaN(stopLossValue) || isNaN(takeProfitValue)) {
        toast.error('Please enter valid numbers for SL/TP');
        return;
      }

      toast.info('Updating position...');
      
      // Simulate API call to modify position
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      toast.success('Position updated successfully');
      console.log('Modified position:', selectedPosition.id, {
        stopLoss: stopLossValue,
        takeProfit: takeProfitValue
      });
      
      setModifyDialogOpen(false);
      
      // Refresh positions
      await handleSync();
    } catch (error) {
      console.error('Modify position error:', error);
      toast.error('Failed to modify position');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white mb-1">Open Positions</h2>
          <p className="text-sm text-gray-400">Monitor and manage positions for {broker}</p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          className="text-blue-400 hover:text-blue-300"
          onClick={handleSync}
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Sync
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Open Positions</p>
            <p className="text-white text-2xl">{positions.length}</p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Total P&L</p>
            <div className="flex items-baseline gap-2">
              <p className={`text-2xl ${totalPnL >= 0 ? 'text-[#00ffc2]' : 'text-red-400'}`}>
                {totalPnL >= 0 ? '+' : ''}${totalPnL.toFixed(2)}
              </p>
              {totalPnL >= 0 ? (
                <TrendingUp className="w-5 h-5 text-[#00ffc2]" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-400" />
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Avg P&L %</p>
            <p className={`text-2xl ${totalPnLPct >= 0 ? 'text-[#00ffc2]' : 'text-red-400'}`}>
              {totalPnLPct >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}%
            </p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Winners / Losers</p>
            <div className="flex items-baseline gap-2">
              <p className="text-[#00ffc2] text-xl">
                {positions.filter(p => p.unrealizedPnL > 0).length}
              </p>
              <span className="text-gray-400">/</span>
              <p className="text-red-400 text-xl">
                {positions.filter(p => p.unrealizedPnL < 0).length}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-4">
          <Input
            placeholder="Search by symbol or tag..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-[#002b36] border-gray-700 text-white"
          />
        </CardContent>
      </Card>

      {/* Positions List */}
      <div className="space-y-3">
        {filteredPositions.map((position) => (
          <Card key={position.id} className="bg-[#001f29] border-gray-800">
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <h3 className="text-white text-xl">{position.symbol}</h3>
                  <Badge
                    variant="outline"
                    className={
                      position.side === 'LONG'
                        ? 'border-[#00ffc2] text-[#00ffc2]'
                        : 'border-red-400 text-red-400'
                    }
                  >
                    {position.side}
                  </Badge>
                  <span className="text-xs text-gray-400">{position.id}</span>
                </div>
                
                <div className="text-right">
                  <div className={`text-xl ${position.unrealizedPnL >= 0 ? 'text-[#00ffc2]' : 'text-red-400'}`}>
                    {position.unrealizedPnL >= 0 ? '+' : ''}${position.unrealizedPnL.toFixed(2)}
                  </div>
                  <div className={`text-sm ${position.unrealizedPnL >= 0 ? 'text-[#00ffc2]' : 'text-red-400'}`}>
                    {position.unrealizedPnL >= 0 ? '+' : ''}{position.unrealizedPnLPct.toFixed(2)}%
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-6 gap-4 mb-4">
                <div>
                  <p className="text-xs text-gray-400 mb-1">Quantity</p>
                  <p className="text-white">{position.qty}</p>
                </div>
                
                <div>
                  <p className="text-xs text-gray-400 mb-1">Entry</p>
                  <p className="text-white">${position.entryPrice.toFixed(2)}</p>
                </div>
                
                <div>
                  <p className="text-xs text-gray-400 mb-1">Current</p>
                  <p className="text-white">${position.currentPrice.toFixed(2)}</p>
                </div>
                
                <div>
                  <p className="text-xs text-gray-400 mb-1">Stop Loss</p>
                  <p className="text-red-400">${position.stopLoss.toFixed(2)}</p>
                </div>
                
                <div>
                  <p className="text-xs text-gray-400 mb-1">Take Profit</p>
                  <p className="text-[#00ffc2]">${position.takeProfit.toFixed(2)}</p>
                </div>
                
                <div>
                  <p className="text-xs text-gray-400 mb-1">Open Time</p>
                  <p className="text-white text-xs">{position.openTime.split(' ')[1]}</p>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-[#002b36] rounded-lg mb-3">
                <div>
                  <p className="text-xs text-gray-400 mb-1">Strategy Tag</p>
                  <p className="text-white text-sm">{position.tag}</p>
                </div>
                
                <div className="flex items-center gap-2">
                  <div className="text-right mr-4">
                    <p className="text-xs text-gray-400">Risk/Reward</p>
                    <p className="text-white text-sm">
                      {((position.takeProfit - position.entryPrice) / (position.entryPrice - position.stopLoss)).toFixed(2)}R
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleModifyPosition(position)}
                  disabled={loading}
                  className="flex-1 border-gray-700 text-white hover:bg-[#002b36] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Modify SL/TP
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleClosePosition(position.id)}
                  disabled={loading}
                  className="flex-1 border-red-700 text-red-400 hover:bg-red-950 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <X className="w-4 h-4 mr-1" />
                  Close Position
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}

        {filteredPositions.length === 0 && (
          <Card className="bg-[#001f29] border-gray-800">
            <CardContent className="p-12 text-center">
              <p className="text-gray-400">No open positions</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Modify Position Dialog */}
      <Dialog open={modifyDialogOpen} onOpenChange={setModifyDialogOpen}>
        <DialogContent className="bg-[#001f29] border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle>Modify Stop Loss / Take Profit</DialogTitle>
            <DialogDescription className="text-gray-400">
              {selectedPosition && `Modifying ${selectedPosition.symbol} - ${selectedPosition.side}`}
            </DialogDescription>
          </DialogHeader>
          
          {selectedPosition && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="stopLoss" className="text-white">Stop Loss</Label>
                <Input
                  id="stopLoss"
                  type="number"
                  step="0.01"
                  value={newStopLoss}
                  onChange={(e) => setNewStopLoss(e.target.value)}
                  className="bg-[#002b36] border-gray-700 text-white"
                  placeholder="Enter stop loss price"
                />
                <p className="text-xs text-gray-400">
                  Current: ${selectedPosition.stopLoss.toFixed(2)}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="takeProfit" className="text-white">Take Profit</Label>
                <Input
                  id="takeProfit"
                  type="number"
                  step="0.01"
                  value={newTakeProfit}
                  onChange={(e) => setNewTakeProfit(e.target.value)}
                  className="bg-[#002b36] border-gray-700 text-white"
                  placeholder="Enter take profit price"
                />
                <p className="text-xs text-gray-400">
                  Current: ${selectedPosition.takeProfit.toFixed(2)}
                </p>
              </div>

              <div className="p-3 bg-[#002b36] rounded-lg">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Entry Price:</span>
                  <span className="text-white">${selectedPosition.entryPrice.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Current Price:</span>
                  <span className="text-white">${selectedPosition.currentPrice.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Unrealized P&L:</span>
                  <span className={selectedPosition.unrealizedPnL >= 0 ? 'text-[#00ffc2]' : 'text-red-400'}>
                    {selectedPosition.unrealizedPnL >= 0 ? '+' : ''}${selectedPosition.unrealizedPnL.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setModifyDialogOpen(false)}
              className="border-gray-700 text-gray-300"
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveModification}
              className="bg-[#00ffc2] text-[#002b36] hover:bg-[#00ffc2]/90"
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
