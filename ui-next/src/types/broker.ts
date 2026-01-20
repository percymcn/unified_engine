export type BrokerType = 'mt4' | 'mt5' | 'tradelocker' | 'tradovate' | 'projectx';

export interface BrokerHealth {
  name: BrokerType;
  connected: boolean;
  lastSeen?: string;
  error?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  redis: 'connected' | 'disconnected';
  brokers: Record<string, boolean>;
}
