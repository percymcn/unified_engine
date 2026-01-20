export type WebSocketMessageType =
  | 'signal_update'
  | 'order_update'
  | 'position_update'
  | 'account_update'
  | 'heartbeat'
  | 'error';

export interface WebSocketMessage<T = unknown> {
  type: WebSocketMessageType;
  data: T;
  timestamp: string;
}

// Specific message data types for type-safe handling
export interface SignalUpdateData {
  id: number;
  signal_id: string;
  status: string;
  symbol?: string;
  action?: string;
  quantity?: number;
  price?: number;
  error_message?: string;
}

export interface OrderUpdateData {
  id: number;
  order_id: string;
  status: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  filled_quantity?: number;
  price?: number;
  broker: string;
}

export interface PositionUpdateData {
  id: number;
  symbol: string;
  side: 'long' | 'short';
  quantity: number;
  entry_price: number;
  current_price?: number;
  unrealized_pnl?: number;
  broker: string;
}

export interface AccountUpdateData {
  broker: string;
  connected: boolean;
  balance?: number;
  equity?: number;
  margin_used?: number;
  error?: string;
}

export interface HeartbeatData {
  server_time: string;
}

export interface ErrorData {
  code: string;
  message: string;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
