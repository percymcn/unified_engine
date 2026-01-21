export type BrokerType = 'mt4' | 'mt5' | 'tradelocker' | 'tradovate' | 'projectx';

/**
 * Connection status for broker health indicators
 * - connected: Broker is online and authenticated (green)
 * - connecting: Connection in progress or being verified (amber)
 * - disconnected: Broker is offline or authentication failed (red)
 */
export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export interface BrokerHealth {
  name: BrokerType;
  connected: boolean;
  status?: ConnectionStatus;
  lastSeen?: string;
  error?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  redis: 'connected' | 'disconnected';
  brokers: Record<string, boolean>;
}
