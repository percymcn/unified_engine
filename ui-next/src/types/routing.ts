/**
 * Signal Routing Configuration Types
 */

export type RoutingConditionField = 'symbol' | 'action' | 'source' | 'strategy';
export type RoutingConditionOperator = 'equals' | 'contains' | 'startsWith' | 'endsWith';

export interface RoutingCondition {
  field: RoutingConditionField;
  operator: RoutingConditionOperator;
  value: string;
}

export interface RoutingRule {
  id: string;
  condition: RoutingCondition;
  target_account_id: number;
  priority: number;
}

export type WebhookSource = 'tradingview' | 'custom';
export type SignalAction = 'buy' | 'sell' | 'close';

// Routing strategies for signal distribution
export type RoutingStrategy = 'all_accounts' | 'specific_accounts' | 'rules_based' | 'default_only';

export interface WebhookConfig {
  id: number;
  name: string;
  webhook_key: string;
  source: WebhookSource;
  routing_strategy: RoutingStrategy;
  default_account_id?: number;
  specific_account_ids?: number[];
  routing_rules: RoutingRule[];
  symbol_filter?: string[];
  action_filter?: SignalAction[];
  is_active: boolean;
  total_signals: number;
  successful_signals: number;
  failed_signals: number;
  last_signal_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface WebhookConfigCreate {
  name: string;
  source: WebhookSource;
  routing_strategy?: RoutingStrategy;
  default_account_id?: number;
  specific_account_ids?: number[];
  routing_rules?: RoutingRule[];
  symbol_filter?: string[];
  action_filter?: SignalAction[];
  is_active?: boolean;
}

export interface WebhookConfigUpdate {
  name?: string;
  source?: WebhookSource;
  routing_strategy?: RoutingStrategy;
  default_account_id?: number;
  specific_account_ids?: number[];
  routing_rules?: RoutingRule[];
  symbol_filter?: string[];
  action_filter?: SignalAction[];
  is_active?: boolean;
}
