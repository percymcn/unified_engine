export type SignalStatus = 'pending' | 'processing' | 'executed' | 'partial' | 'cancelled' | 'failed' | 'ignored' | 'stale';

export interface SignalExecutionResults {
  total_accounts?: number;
  successful?: number;
  failed?: number;
  errors?: string[];
  processing_time_ms?: number;
}

export interface Signal {
  id: number;
  signal_id: string;
  user_id?: number;
  symbol: string;
  action: string;
  quantity?: number;
  volume?: number;
  price?: number;
  stop_loss?: number;
  take_profit?: number;
  comment?: string;
  status: SignalStatus;
  source?: string;
  target_accounts?: number[];
  processed_at?: string;
  created_at: string;
  updated_at?: string;
  executed_at?: string;
  error_message?: string;
  // Signal data with execution results
  signal_data?: {
    execution_results?: SignalExecutionResults;
    [key: string]: unknown;
  };
  // Guard metadata
  guard_reason?: string;
  reason_detail?: string;
  warning_type?: string;
  guard_rule?: string;
  message?: string;
}
