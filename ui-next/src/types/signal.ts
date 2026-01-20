export type SignalStatus = 'pending' | 'processing' | 'executed' | 'cancelled' | 'failed';

export interface Signal {
  id: number;
  signal_id: string;
  symbol: string;
  action: string;
  quantity: number;
  price?: number;
  stop_loss?: number;
  take_profit?: number;
  status: SignalStatus;
  source?: string;
  created_at: string;
  executed_at?: string;
  error_message?: string;
}
