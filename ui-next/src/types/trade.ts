export type TradeStatus = 'open' | 'closed' | 'pending' | 'cancelled';

export type CloseReason = 'stop_loss' | 'take_profit' | 'trailing_stop' | 'manual' | 'signal' | 'margin_call';

export interface Trade {
  id: number;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  entry_price: number;
  exit_price?: number;
  profit_loss?: number;
  profit_loss_pct?: number;
  status: TradeStatus;
  broker: string;
  account_id: number;
  opened_at: string;
  closed_at?: string;
  // Enhanced risk management fields (migration 027)
  stop_loss?: number;
  take_profit?: number;
  trailing_stop?: number;
  close_reason?: CloseReason;
  order_id?: string;
  position_id?: string;
}

export interface TradeFilters {
  dateFrom?: string;
  dateTo?: string;
  broker?: string;
  status?: TradeStatus | 'all';
}
