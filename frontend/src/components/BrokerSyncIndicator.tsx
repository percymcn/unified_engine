import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { RefreshCw, WifiOff, Wifi } from 'lucide-react';
import { useBroker, getBrokerDisplayName } from '../contexts/BrokerContext';
import { cn } from './ui/utils';

export function BrokerSyncIndicator() {
  const { activeBroker, isSyncing, activeBrokerAccount } = useBroker();
  const [showIndicator, setShowIndicator] = useState(false);

  useEffect(() => {
    if (isSyncing) {
      setShowIndicator(true);
    } else {
      // Keep visible for a moment after syncing completes
      const timer = setTimeout(() => setShowIndicator(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [isSyncing]);

  if (!activeBroker || !showIndicator) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed top-20 right-6 z-50"
    >
      <div className="bg-[#002b36] border border-gray-700 rounded-lg px-4 py-2 shadow-lg flex items-center gap-3">
        <div className={cn(
          "relative flex items-center justify-center w-8 h-8 rounded-full",
          isSyncing ? "bg-blue-500/20" : "bg-green-500/20"
        )}>
          {isSyncing ? (
            <>
              <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
              <span className="absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-20 animate-ping" />
            </>
          ) : (
            <Wifi className="w-4 h-4 text-green-400" />
          )}
        </div>
        
        <div className="flex flex-col">
          <span className="text-white text-sm">
            {isSyncing ? 'Syncing...' : 'Synced'}
          </span>
          <span className="text-xs text-gray-400">
            {getBrokerDisplayName(activeBroker)}
            {activeBrokerAccount?.lastSync && !isSyncing && (
              <> • {new Date(activeBrokerAccount.lastSync).toLocaleTimeString()}</>
            )}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
