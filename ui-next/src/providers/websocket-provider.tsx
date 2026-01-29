'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from 'react';
import { useWebSocket } from '@/hooks/use-websocket';
import {
  WebSocketMessage,
  ConnectionStatus,
  SignalUpdateData,
  OrderUpdateData,
  PositionUpdateData,
  AccountUpdateData,
} from '@/types/websocket';

// Message handlers registry type
type MessageHandler<T = unknown> = (data: T) => void;

interface WebSocketContextValue {
  status: ConnectionStatus;
  reconnectAttempts: number;
  connect: () => void;
  disconnect: () => void;
  // Last messages by type
  lastSignalUpdate: SignalUpdateData | null;
  lastOrderUpdate: OrderUpdateData | null;
  lastPositionUpdate: PositionUpdateData | null;
  lastAccountUpdate: AccountUpdateData | null;
  // Subscribe to specific message types
  subscribeToSignals: (handler: MessageHandler<SignalUpdateData>) => () => void;
  subscribeToOrders: (handler: MessageHandler<OrderUpdateData>) => () => void;
  subscribeToPositions: (handler: MessageHandler<PositionUpdateData>) => () => void;
  subscribeToAccounts: (handler: MessageHandler<AccountUpdateData>) => () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

// Get WebSocket URL from environment or construct from backend URL
function getWebSocketUrl(): string {
  // Check for explicit WebSocket URL first
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  // Construct from backend URL - convert http(s) to ws(s)
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765';
  const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
  const baseUrl = backendUrl.replace(/^https?/, wsProtocol);
  return `${baseUrl}/ws`;
}

interface WebSocketProviderProps {
  children: ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  // Handlers registries
  const [signalHandlers] = useState<Set<MessageHandler<SignalUpdateData>>>(
    () => new Set()
  );
  const [orderHandlers] = useState<Set<MessageHandler<OrderUpdateData>>>(
    () => new Set()
  );
  const [positionHandlers] = useState<Set<MessageHandler<PositionUpdateData>>>(
    () => new Set()
  );
  const [accountHandlers] = useState<Set<MessageHandler<AccountUpdateData>>>(
    () => new Set()
  );

  // Last messages by type
  const [lastSignalUpdate, setLastSignalUpdate] =
    useState<SignalUpdateData | null>(null);
  const [lastOrderUpdate, setLastOrderUpdate] =
    useState<OrderUpdateData | null>(null);
  const [lastPositionUpdate, setLastPositionUpdate] =
    useState<PositionUpdateData | null>(null);
  const [lastAccountUpdate, setLastAccountUpdate] =
    useState<AccountUpdateData | null>(null);

  // Handle incoming messages
  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      switch (message.type) {
        case 'signal_update': {
          const data = message.data as SignalUpdateData;
          setLastSignalUpdate(data);
          signalHandlers.forEach((handler) => handler(data));
          break;
        }
        case 'order_update': {
          const data = message.data as OrderUpdateData;
          setLastOrderUpdate(data);
          orderHandlers.forEach((handler) => handler(data));
          break;
        }
        case 'position_update': {
          const data = message.data as PositionUpdateData;
          setLastPositionUpdate(data);
          positionHandlers.forEach((handler) => handler(data));
          break;
        }
        case 'account_update': {
          const data = message.data as AccountUpdateData;
          setLastAccountUpdate(data);
          accountHandlers.forEach((handler) => handler(data));
          break;
        }
        case 'heartbeat':
        case 'pong':
          // Heartbeat/pong handled silently - connection is alive
          break;
        case 'error':
          console.error('WebSocket error message:', message.data);
          break;
        default:
          // Only log for truly unknown message types
          if (message.type && !['ping', 'ack', 'connected'].includes(message.type)) {
            console.warn('Unknown WebSocket message type:', message.type);
          }
      }
    },
    [signalHandlers, orderHandlers, positionHandlers, accountHandlers]
  );

  // Initialize WebSocket connection
  const wsUrl = getWebSocketUrl();
  const { status, connect, disconnect, reconnectAttempts } = useWebSocket(
    wsUrl,
    {
      onMessage: handleMessage,
      autoConnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
    }
  );

  // Subscription helpers
  const subscribeToSignals = useCallback(
    (handler: MessageHandler<SignalUpdateData>) => {
      signalHandlers.add(handler);
      return () => {
        signalHandlers.delete(handler);
      };
    },
    [signalHandlers]
  );

  const subscribeToOrders = useCallback(
    (handler: MessageHandler<OrderUpdateData>) => {
      orderHandlers.add(handler);
      return () => {
        orderHandlers.delete(handler);
      };
    },
    [orderHandlers]
  );

  const subscribeToPositions = useCallback(
    (handler: MessageHandler<PositionUpdateData>) => {
      positionHandlers.add(handler);
      return () => {
        positionHandlers.delete(handler);
      };
    },
    [positionHandlers]
  );

  const subscribeToAccounts = useCallback(
    (handler: MessageHandler<AccountUpdateData>) => {
      accountHandlers.add(handler);
      return () => {
        accountHandlers.delete(handler);
      };
    },
    [accountHandlers]
  );

  const value: WebSocketContextValue = {
    status,
    reconnectAttempts,
    connect,
    disconnect,
    lastSignalUpdate,
    lastOrderUpdate,
    lastPositionUpdate,
    lastAccountUpdate,
    subscribeToSignals,
    subscribeToOrders,
    subscribeToPositions,
    subscribeToAccounts,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext(): WebSocketContextValue {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error(
      'useWebSocketContext must be used within a WebSocketProvider'
    );
  }
  return context;
}
