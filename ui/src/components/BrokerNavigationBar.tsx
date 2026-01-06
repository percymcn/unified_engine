import { useBroker, BrokerType, getBrokerDisplayName } from '../contexts/BrokerContext';
import { cn } from './ui/utils';
import { TradeLockerIcon } from './TradeLockerLogo';
import { CheckCircle, Loader2 } from 'lucide-react';

export function BrokerNavigationBar() {
  const { 
    activeBroker, 
    connectedBrokers, 
    switchBroker,
    isSyncing
  } = useBroker();

  const brokerOptions: Array<{
    id: BrokerType;
    name: string;
    icon: React.ReactNode;
    color: string;
  }> = [
    {
      id: 'tradelocker',
      name: 'TradeLocker',
      icon: <TradeLockerIcon className="w-5 h-5" />,
      color: '#0EA5E9'
    },
    {
      id: 'topstep',
      name: 'Topstep',
      icon: <span className="text-lg">🎯</span>,
      color: '#10b981'
    },
    {
      id: 'truforex',
      name: 'TruForex',
      icon: <span className="text-lg">📊</span>,
      color: '#f59e0b'
    }
  ];

  const handleBrokerClick = async (brokerId: BrokerType) => {
    // Find the first connected account for this broker
    const brokerAccount = connectedBrokers.find(b => b.broker === brokerId);
    
    if (brokerAccount && brokerAccount.accountId) {
      await switchBroker(brokerId, brokerAccount.accountId);
    }
  };

  const isBrokerConnected = (brokerId: BrokerType) => {
    return connectedBrokers.some(b => b.broker === brokerId);
  };

  const isBrokerActive = (brokerId: BrokerType) => {
    return activeBroker === brokerId;
  };

  return (
    <div className="w-full bg-[#001f29] border-b border-gray-800">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Broker Tabs */}
        <div className="flex items-center gap-1">
          {brokerOptions.map((broker) => {
            const isConnected = isBrokerConnected(broker.id);
            const isActive = isBrokerActive(broker.id);
            
            return (
              <button
                key={broker.id}
                onClick={() => isConnected && handleBrokerClick(broker.id)}
                disabled={!isConnected || isSyncing}
                className={cn(
                  "px-6 py-2.5 rounded-lg transition-all duration-200 flex items-center gap-2.5 relative",
                  "border border-transparent",
                  isActive && isConnected && "bg-[#002b36] border-gray-700",
                  !isActive && isConnected && "hover:bg-[#002b36]/50",
                  !isConnected && "opacity-40 cursor-not-allowed",
                  isConnected && !isActive && "cursor-pointer",
                  isSyncing && isActive && "opacity-70"
                )}
                style={{
                  borderBottomColor: isActive && isConnected ? broker.color : 'transparent',
                  borderBottomWidth: isActive && isConnected ? '2px' : '0'
                }}
              >
                {/* Broker Icon */}
                <div className="flex items-center justify-center">
                  {broker.icon}
                </div>

                {/* Broker Name */}
                <span
                  className={cn(
                    "text-sm transition-colors",
                    isActive && isConnected ? "text-white font-medium" : "text-gray-400"
                  )}
                >
                  {broker.name}
                </span>

                {/* Syncing Indicator */}
                {isActive && isSyncing && (
                  <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin absolute -top-1 -right-1" />
                )}

                {/* Active Indicator */}
                {isActive && isConnected && !isSyncing && (
                  <CheckCircle 
                    className="w-3.5 h-3.5 text-green-400 absolute -top-1 -right-1" 
                    fill="currentColor"
                  />
                )}

                {/* Connection Status Dot */}
                {isConnected && !isActive && (
                  <div 
                    className="w-1.5 h-1.5 rounded-full absolute top-1 right-1"
                    style={{ backgroundColor: broker.color }}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Sync Status Text */}
        {isSyncing && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Syncing data...</span>
          </div>
        )}
      </div>
    </div>
  );
}
