import { useState } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { ChevronDown, RefreshCw, Check, Plus } from 'lucide-react';
import { useBroker, getBrokerDisplayName, getBrokerIcon, getBrokerColor, BrokerType } from '../contexts/BrokerContext';
import { cn } from './ui/utils';

interface BrokerSwitcherProps {
  onConnectBroker?: () => void;
  compact?: boolean;
}

export function BrokerSwitcher({ onConnectBroker, compact = false }: BrokerSwitcherProps) {
  const { 
    activeBroker, 
    activeBrokerAccount,
    connectedBrokers, 
    isSyncing, 
    switchBroker,
    refreshBrokerData
  } = useBroker();

  const [isOpen, setIsOpen] = useState(false);

  const handleBrokerSwitch = async (broker: BrokerType, accountId: string) => {
    setIsOpen(false);
    await switchBroker(broker, accountId);
  };

  const handleRefresh = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await refreshBrokerData();
  };

  if (!activeBroker) {
    return (
      <Button
        variant="outline"
        size={compact ? "sm" : "default"}
        onClick={onConnectBroker}
        className="border-gray-700 text-gray-300 hover:text-white hover:bg-[#002b36]"
      >
        <Plus className="w-4 h-4 mr-2" />
        Connect Broker
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size={compact ? "sm" : "default"}
            className={cn(
              "border-gray-700 hover:bg-[#002b36] transition-all",
              isSyncing && "opacity-50"
            )}
            style={{ borderLeftColor: getBrokerColor(activeBroker), borderLeftWidth: '3px' }}
          >
            <span className="mr-2">{getBrokerIcon(activeBroker)}</span>
            <div className="flex flex-col items-start mr-2">
              <span className="text-white text-sm">
                {getBrokerDisplayName(activeBroker)}
              </span>
              {!compact && activeBrokerAccount && (
                <span className="text-xs text-gray-400">
                  {activeBrokerAccount.accountName}
                </span>
              )}
            </div>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent 
          align="start" 
          className="w-72 bg-[#002b36] border-gray-700"
        >
          <DropdownMenuLabel className="text-gray-400 text-xs uppercase tracking-wide">
            Connected Brokers
          </DropdownMenuLabel>
          <DropdownMenuSeparator className="bg-gray-700" />
          
          {connectedBrokers.map((account) => (
            <DropdownMenuItem
              key={`${account.broker}-${account.accountId}`}
              onClick={() => handleBrokerSwitch(account.broker, account.accountId)}
              className="cursor-pointer hover:bg-[#001f29] focus:bg-[#001f29] py-3"
              style={{ 
                borderLeft: account.broker === activeBroker && account.accountId === activeBrokerAccount?.accountId
                  ? `3px solid ${getBrokerColor(account.broker)}`
                  : '3px solid transparent'
              }}
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                  <span className="text-xl">{getBrokerIcon(account.broker)}</span>
                  <div className="flex flex-col">
                    <span className="text-white text-sm">
                      {getBrokerDisplayName(account.broker)}
                    </span>
                    <span className="text-xs text-gray-400">
                      {account.accountName}
                    </span>
                    {account.lastSync && (
                      <span className="text-xs text-gray-500">
                        Synced: {new Date(account.lastSync).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {account.connected && (
                    <Badge 
                      variant="outline" 
                      className="border-green-500 text-green-400 text-xs"
                    >
                      Active
                    </Badge>
                  )}
                  {account.broker === activeBroker && account.accountId === activeBrokerAccount?.accountId && (
                    <Check className="w-4 h-4 text-[#00ffc2]" />
                  )}
                </div>
              </div>
            </DropdownMenuItem>
          ))}

          {connectedBrokers.length === 0 && (
            <div className="py-6 text-center text-sm text-gray-400">
              No brokers connected
            </div>
          )}

          <DropdownMenuSeparator className="bg-gray-700" />
          
          {onConnectBroker && (
            <DropdownMenuItem
              onClick={onConnectBroker}
              className="cursor-pointer hover:bg-[#001f29] focus:bg-[#001f29] text-blue-400"
            >
              <Plus className="w-4 h-4 mr-2" />
              Connect New Broker
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Button
        variant="ghost"
        size="sm"
        onClick={handleRefresh}
        disabled={isSyncing}
        className="text-gray-400 hover:text-white hover:bg-[#002b36]"
        title="Refresh broker data"
      >
        <RefreshCw className={cn("w-4 h-4", isSyncing && "animate-spin")} />
      </Button>
    </div>
  );
}
