import { useEffect, useState } from 'react';
import { useBroker, getBrokerDisplayName } from '../contexts/BrokerContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { RefreshCw, CheckCircle } from 'lucide-react';

/**
 * Demo component that shows real-time broker data syncing
 * This demonstrates how all data updates when switching brokers
 */
export function BrokerDataSyncDemo() {
  const { activeBroker, activeBrokerAccount, isSyncing } = useBroker();
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [syncCount, setSyncCount] = useState(0);

  // Mock data that changes per broker
  const brokerMockData = {
    tradelocker: {
      balance: 52430.00,
      equity: 53677.50,
      positions: 3,
      pnl: 1247.50,
      server: 'demo.tradelocker.com'
    },
    topstep: {
      balance: 150000.00,
      equity: 151250.00,
      positions: 5,
      pnl: 1250.00,
      server: 'projectx.topstep.com'
    },
    truforex: {
      balance: 10000.00,
      equity: 10385.50,
      positions: 2,
      pnl: 385.50,
      server: 'truforex.securepharma.net'
    }
  };

  const currentData = activeBroker ? brokerMockData[activeBroker] : null;

  // Listen for broker switches
  useEffect(() => {
    const handleBrokerSwitch = () => {
      setLastUpdate(new Date());
      setSyncCount(prev => prev + 1);
    };

    window.addEventListener('broker.switch', handleBrokerSwitch);
    window.addEventListener('broker.refresh', handleBrokerSwitch);

    return () => {
      window.removeEventListener('broker.switch', handleBrokerSwitch);
      window.removeEventListener('broker.refresh', handleBrokerSwitch);
    };
  }, []);

  if (!activeBroker || !currentData) {
    return null;
  }

  return (
    <Card className="bg-[#001f29] border-gray-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-white flex items-center gap-2">
              {getBrokerDisplayName(activeBroker)} - Live Data
              {isSyncing ? (
                <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
              ) : (
                <CheckCircle className="w-4 h-4 text-green-400" />
              )}
            </CardTitle>
            <CardDescription className="text-gray-400 text-xs mt-1">
              Last synced: {lastUpdate.toLocaleTimeString()} • Updates: {syncCount}
            </CardDescription>
          </div>
          <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
            Connected
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-[#002b36] rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400 mb-1">Balance</p>
            <p className="text-white font-medium">
              ${currentData.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </p>
          </div>
          
          <div className="bg-[#002b36] rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400 mb-1">Equity</p>
            <p className="text-white font-medium">
              ${currentData.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </p>
          </div>
          
          <div className="bg-[#002b36] rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400 mb-1">Positions</p>
            <p className="text-white font-medium">{currentData.positions}</p>
          </div>
          
          <div className="bg-[#002b36] rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400 mb-1">P&L</p>
            <p className={`font-medium ${currentData.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${currentData.pnl >= 0 ? '+' : ''}{currentData.pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        <div className="bg-[#002b36] rounded-lg p-3 border border-gray-700">
          <p className="text-xs text-gray-400 mb-1">Server</p>
          <p className="text-white text-sm font-mono">{currentData.server}</p>
        </div>

        {activeBrokerAccount && (
          <div className="bg-blue-950/30 rounded-lg p-3 border border-blue-800/30">
            <p className="text-xs text-blue-300 mb-1">Account Info</p>
            <p className="text-white text-sm">
              {activeBrokerAccount.accountName} • {activeBrokerAccount.accountId}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
