import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { toast } from 'sonner';

export type BrokerType = 'tradelocker' | 'topstep' | 'truforex' | 'tradovate';

export interface BrokerAccount {
  broker: BrokerType;
  accountId: string;
  accountName: string;
  connected: boolean;
  lastSync?: string;
}

interface BrokerContextType {
  activeBroker: BrokerType | null;
  activeBrokerAccount: BrokerAccount | null;
  connectedBrokers: BrokerAccount[];
  isLoading: boolean;
  isSyncing: boolean;
  switchBroker: (broker: BrokerType, accountId?: string) => Promise<void>;
  refreshBrokerData: () => Promise<void>;
  getApiBaseUrl: () => string;
  addBrokerAccount: (account: BrokerAccount) => void;
  removeBrokerAccount: (broker: BrokerType, accountId: string) => void;
}

const BrokerContext = createContext<BrokerContextType | undefined>(undefined);

export function BrokerProvider({ children }: { children: ReactNode }) {
  const [activeBroker, setActiveBroker] = useState<BrokerType | null>(null);
  const [activeBrokerAccount, setActiveBrokerAccount] = useState<BrokerAccount | null>(null);
  const [connectedBrokers, setConnectedBrokers] = useState<BrokerAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);

  // Load initial broker data from localStorage
  useEffect(() => {
    const loadBrokerData = async () => {
      try {
        const savedBrokers = localStorage.getItem('connectedBrokers');
        const savedActiveBroker = localStorage.getItem('activeBroker');

        if (savedBrokers) {
          const brokers = JSON.parse(savedBrokers);
          setConnectedBrokers(brokers);

          // Set active broker
          if (savedActiveBroker && brokers.length > 0) {
            const active = brokers.find((b: BrokerAccount) => b.broker === savedActiveBroker);
            if (active) {
              setActiveBroker(savedActiveBroker as BrokerType);
              setActiveBrokerAccount(active);
            } else if (brokers.length > 0) {
              // Fallback to first connected broker
              setActiveBroker(brokers[0].broker);
              setActiveBrokerAccount(brokers[0]);
            }
          } else if (brokers.length > 0) {
            setActiveBroker(brokers[0].broker);
            setActiveBrokerAccount(brokers[0]);
          }
        }
      } catch (error) {
        console.error('Error loading broker data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadBrokerData();
  }, []);

  // Save broker data to localStorage whenever it changes
  useEffect(() => {
    if (connectedBrokers.length > 0) {
      localStorage.setItem('connectedBrokers', JSON.stringify(connectedBrokers));
    }
  }, [connectedBrokers]);

  useEffect(() => {
    if (activeBroker) {
      localStorage.setItem('activeBroker', activeBroker);
    }
  }, [activeBroker]);

  const getApiBaseUrl = () => {
    if (!activeBroker) return '';
    
    const baseUrls = {
      tradelocker: '/api/broker/tradelocker',
      topstep: '/api/broker/topstep',
      truforex: '/api/broker/truforex',
      tradovate: '/api/broker/tradovate'
    };

    return baseUrls[activeBroker];
  };

  const switchBroker = async (broker: BrokerType, accountId?: string) => {
    setIsSyncing(true);
    
    try {
      // Dispatch broker switch event
      const event = new CustomEvent('broker.switch', {
        detail: { 
          broker, 
          accountId: accountId || `${broker}-default`,
          timestamp: new Date().toISOString()
        }
      });
      window.dispatchEvent(event);

      // Find the broker account
      const brokerAccount = connectedBrokers.find(
        b => b.broker === broker && (accountId ? b.accountId === accountId : true)
      );

      if (brokerAccount) {
        setActiveBroker(broker);
        setActiveBrokerAccount(brokerAccount);

        // Simulate data fetch delay for smooth UX
        await new Promise(resolve => setTimeout(resolve, 600));

        toast.success(`Switched to ${getBrokerDisplayName(broker)}`);
      } else {
        throw new Error('Broker account not found');
      }
    } catch (error) {
      console.error('Error switching broker:', error);
      toast.error('Failed to switch broker');
    } finally {
      setIsSyncing(false);
    }
  };

  const refreshBrokerData = async () => {
    if (!activeBroker) return;

    setIsSyncing(true);
    try {
      // Dispatch refresh event
      const event = new CustomEvent('broker.refresh', {
        detail: { 
          broker: activeBroker,
          timestamp: new Date().toISOString()
        }
      });
      window.dispatchEvent(event);

      // Simulate API refresh
      await new Promise(resolve => setTimeout(resolve, 800));

      // Update last sync time
      if (activeBrokerAccount) {
        const updatedAccount = {
          ...activeBrokerAccount,
          lastSync: new Date().toISOString()
        };
        setActiveBrokerAccount(updatedAccount);
        
        // Update in connected brokers list
        setConnectedBrokers(prev =>
          prev.map(b =>
            b.broker === activeBroker && b.accountId === activeBrokerAccount.accountId
              ? updatedAccount
              : b
          )
        );
      }

      toast.success('Data refreshed successfully');
    } catch (error) {
      console.error('Error refreshing broker data:', error);
      toast.error('Failed to refresh data');
    } finally {
      setIsSyncing(false);
    }
  };

  const addBrokerAccount = (account: BrokerAccount) => {
    setConnectedBrokers(prev => {
      // Check if account already exists
      const exists = prev.some(
        b => b.broker === account.broker && b.accountId === account.accountId
      );
      
      if (exists) {
        return prev.map(b =>
          b.broker === account.broker && b.accountId === account.accountId
            ? account
            : b
        );
      }
      
      return [...prev, account];
    });

    // If this is the first broker, set it as active
    if (connectedBrokers.length === 0) {
      setActiveBroker(account.broker);
      setActiveBrokerAccount(account);
    }
  };

  const removeBrokerAccount = (broker: BrokerType, accountId: string) => {
    setConnectedBrokers(prev => 
      prev.filter(b => !(b.broker === broker && b.accountId === accountId))
    );

    // If removing active broker, switch to another one
    if (activeBroker === broker && activeBrokerAccount?.accountId === accountId) {
      const remaining = connectedBrokers.filter(
        b => !(b.broker === broker && b.accountId === accountId)
      );
      
      if (remaining.length > 0) {
        setActiveBroker(remaining[0].broker);
        setActiveBrokerAccount(remaining[0]);
      } else {
        setActiveBroker(null);
        setActiveBrokerAccount(null);
      }
    }
  };

  const value: BrokerContextType = {
    activeBroker,
    activeBrokerAccount,
    connectedBrokers,
    isLoading,
    isSyncing,
    switchBroker,
    refreshBrokerData,
    getApiBaseUrl,
    addBrokerAccount,
    removeBrokerAccount
  };

  return (
    <BrokerContext.Provider value={value}>
      {children}
    </BrokerContext.Provider>
  );
}

export function useBroker() {
  const context = useContext(BrokerContext);
  if (context === undefined) {
    throw new Error('useBroker must be used within a BrokerProvider');
  }
  return context;
}

// Helper function to get display name for broker
export function getBrokerDisplayName(broker: BrokerType): string {
  const names = {
    tradelocker: 'TradeLocker',
    topstep: 'TopStep',
    truforex: 'TruForex',
    tradovate: 'Tradovate'
  };
  return names[broker];
}

// Helper function to get broker icon/emoji
export function getBrokerIcon(broker: BrokerType): string {
  const icons = {
    tradelocker: '📈',
    topstep: '🎯',
    truforex: '📊',
    tradovate: '⚡'
  };
  return icons[broker];
}

// Helper function to get broker color
export function getBrokerColor(broker: BrokerType): string {
  const colors = {
    tradelocker: '#0EA5E9',
    topstep: '#10b981',
    truforex: '#f59e0b',
    tradovate: '#8b5cf6'
  };
  return colors[broker];
}
