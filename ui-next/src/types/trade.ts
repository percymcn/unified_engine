export type TradeStatus = 'open' | 'closed' | 'pending' | 'cancelled';

export interface Trade {
  id: number;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  entry_price: number;
  exit_price?: number;
  profit_loss?: number;
  status: TradeStatus;
  broker: string;
  account_id: number;
  opened_at: string;
  closed_at?: string;
}

export interface TradeFilters {
  dateFrom?: string;
  dateTo?: string;
  broker?: string;
  status?: TradeStatus | 'all';
}
