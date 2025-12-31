/**
 * TradeFlow v6 Enhanced API Client
 * Complete implementation of all REST endpoints from the unified blueprint
 * Matches the authoritative endpoint list exactly
 */

import { projectId, publicAnonKey } from './supabase/info';

const API_BASE_URL = `https://unified.fluxeo.net/api/unify/v1`;
const BACKUP_URL = `https://${projectId}.supabase.co/functions/v1/make-server-d751d621`;

// Toggle between real backend and mock for development
// Set to true for local development until backend is ready
const USE_MOCK = true;

// ============================================================================
// TYPE DEFINITIONS (matching backend contracts)
// ============================================================================

export interface Position {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  qty: number;
  avg_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
  broker: string;
  opened_at: string;
  stop_loss?: number;
  take_profit?: number;
  tag?: string;
}

export interface Order {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT' | 'STOP';
  qty: number;
  price?: number;
  status: 'PENDING' | 'FILLED' | 'CANCELED' | 'REJECTED';
  broker: string;
  created_at: string;
  filled_at?: string;
}

export interface BrokerAccount {
  id: string;
  broker: 'tradelocker' | 'topstep' | 'truforex' | 'mt4' | 'mt5';
  email: string;
  server?: string;
  mode: 'demo' | 'live';
  status: 'active' | 'inactive' | 'pending' | 'error';
  balance: number;
  equity: number;
  margin_used: number;
  margin_available: number;
  created_at: string;
  last_sync?: string;
}

export interface Overview {
  total_pnl: number;
  total_pnl_pct: number;
  today_pnl: number;
  today_trades: number;
  win_rate: number;
  active_positions: number;
  total_trades: number;
  largest_win: number;
  largest_loss: number;
  avg_win: number;
  avg_loss: number;
  sharpe_ratio: number;
}

export interface PnLReport {
  start_date: string;
  end_date: string;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  daily_breakdown: Array<{
    date: string;
    pnl: number;
    trades: number;
    volume: number;
  }>;
}

export interface AnalyticsMetrics {
  period: string;
  broker?: string;
  total_volume: number;
  total_trades: number;
  avg_trade_duration: number;
  best_symbol: string;
  worst_symbol: string;
  best_day: string;
  worst_day: string;
  metrics_by_symbol: Record<string, {
    trades: number;
    pnl: number;
    win_rate: number;
  }>;
}

export interface TradeAnalytics {
  trades: Array<{
    id: string;
    symbol: string;
    side: 'BUY' | 'SELL';
    entry_price: number;
    exit_price: number;
    qty: number;
    pnl: number;
    duration_minutes: number;
    opened_at: string;
    closed_at: string;
    broker: string;
  }>;
}

export interface UserConfig {
  stop_loss_pct: number;
  take_profit_pct: number;
  position_size: number;
  max_daily_loss: number;
  max_daily_trades: number;
  allow_weekend_trading: boolean;
}

export interface RiskConfig {
  max_risk_per_trade: number;
  max_drawdown: number;
  max_correlation: number;
  max_open_positions: number;
  emergency_stop_enabled: boolean;
  emergency_stop_loss: number;
}

export interface ApiKey {
  id: string;
  key: string;
  name: string;
  permissions: string[];
  created_at: string;
  last_used?: string;
  expires_at?: string;
}

export interface BillingStatus {
  status: 'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete';
  plan: 'starter' | 'pro' | 'elite';
  price_id: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  trial_end?: string;
  customer_id?: string;
}

export interface BillingUsage {
  trades_count: number;
  trades_limit: number;
  days_remaining?: number;
  trial_trades_remaining?: number;
  brokers_connected: number;
  brokers_limit: number;
  strategies_active: number;
  strategies_limit: number;
}

export interface WebhookLog {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  status: number;
  payload: any;
  response: any;
  latency_ms: number;
  error?: string;
}

export interface SyncResult {
  account_id: string;
  broker: string;
  status: 'success' | 'error' | 'partial';
  positions_synced: number;
  orders_synced: number;
  balance_updated: boolean;
  errors: string[];
  synced_at: string;
}

// ============================================================================
// API CLIENT CLASS
// ============================================================================

class EnhancedApiClient {
  private token: string | null = null;
  private apiKey: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  setApiKey(key: string) {
    this.apiKey = key;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    useApiKey = false
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (useApiKey && this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    } else if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    } else {
      headers['Authorization'] = `Bearer ${publicAnonKey}`;
    }

    try {
      const url = `${API_BASE_URL}${endpoint}`;
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorData.message || errorMessage;
        } catch {
          errorMessage = `Request failed with status ${response.status}`;
        }
        throw new Error(errorMessage);
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T;
      }

      return response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // ============================================================================
  // OVERVIEW & ANALYTICS
  // ============================================================================

  async getOverview(): Promise<Overview> {
    if (USE_MOCK) {
      await this.delay(300);
      return {
        total_pnl: 12450.75,
        total_pnl_pct: 24.9,
        today_pnl: 385.50,
        today_trades: 12,
        win_rate: 68.5,
        active_positions: 3,
        total_trades: 245,
        largest_win: 1250.00,
        largest_loss: -450.00,
        avg_win: 215.30,
        avg_loss: -125.80,
        sharpe_ratio: 1.85
      };
    }
    return this.request<Overview>('/api/overview');
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async getPositions(): Promise<Position[]> {
    return this.request<Position[]>('/api/positions');
  }

  async getOrders(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    symbol?: string;
  }): Promise<Order[]> {
    const query = new URLSearchParams();
    if (params?.limit) query.append('limit', params.limit.toString());
    if (params?.offset) query.append('offset', params.offset.toString());
    if (params?.status) query.append('status', params.status);
    if (params?.symbol) query.append('symbol', params.symbol);
    
    const queryString = query.toString();
    return this.request<Order[]>(`/api/orders${queryString ? `?${queryString}` : ''}`);
  }

  async closePosition(position_id: string): Promise<{ success: boolean; pnl: number }> {
    return this.request('/api/orders/close', {
      method: 'POST',
      body: JSON.stringify({ position_id }),
    });
  }

  async deleteOrder(order_id: string): Promise<void> {
    return this.request(`/api/orders/${order_id}`, {
      method: 'DELETE',
    });
  }

  async getPnLReport(start_date: string, end_date: string): Promise<PnLReport> {
    return this.request<PnLReport>(
      `/api/reports/pnl?start_date=${start_date}&end_date=${end_date}`
    );
  }

  async getAnalyticsMetrics(params: {
    start_date: string;
    end_date: string;
    broker?: string;
  }): Promise<AnalyticsMetrics> {
    const query = new URLSearchParams({
      start_date: params.start_date,
      end_date: params.end_date,
    });
    if (params.broker) query.append('broker', params.broker);
    
    return this.request<AnalyticsMetrics>(`/api/analytics/metrics?${query}`);
  }

  async getAnalyticsTrades(start_date: string, end_date: string): Promise<TradeAnalytics> {
    return this.request<TradeAnalytics>(
      `/api/analytics/trades?start_date=${start_date}&end_date=${end_date}`
    );
  }

  // ============================================================================
  // BROKER ACCOUNTS
  // ============================================================================

  async getUserBrokers(): Promise<BrokerAccount[]> {
    return this.request<BrokerAccount[]>('/api/user/brokers');
  }

  async registerBroker(broker: string, data: {
    email: string;
    password: string;
    server?: string;
    mode: 'demo' | 'live';
  }): Promise<BrokerAccount> {
    return this.request(`/register/${broker}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async switchAccount(account_id: string): Promise<{ success: boolean; message: string }> {
    return this.request('/api/accounts/switch', {
      method: 'POST',
      body: JSON.stringify({ account_id }),
    });
  }

  async getSyncResults(): Promise<SyncResult[]> {
    return this.request<SyncResult[]>('/api/accounts/sync_results');
  }

  async syncAccount(id: string): Promise<SyncResult> {
    return this.request<SyncResult>(`/api/accounts/sync/${id}`, {
      method: 'POST',
    });
  }

  // ============================================================================
  // USER CONFIGURATION
  // ============================================================================

  async getUserConfig(): Promise<UserConfig> {
    return this.request<UserConfig>('/api/user/config');
  }

  async updateUserConfig(config: Partial<UserConfig>): Promise<UserConfig> {
    return this.request('/api/user/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getRiskConfig(): Promise<RiskConfig> {
    return this.request<RiskConfig>('/api/user/risk_config');
  }

  async updateRiskConfig(config: Partial<RiskConfig>): Promise<RiskConfig> {
    return this.request('/api/user/risk_config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async emergencyStop(): Promise<{ success: boolean; positions_closed: number }> {
    if (USE_MOCK) {
      await this.delay(800);
      return {
        success: true,
        positions_closed: 3,
      };
    }
    return this.request('/api/user/emergency_stop', {
      method: 'POST',
    });
  }

  // ============================================================================
  // API KEYS
  // ============================================================================

  async getApiKeys(): Promise<ApiKey[]> {
    return this.request<ApiKey[]>('/api/user/api_keys');
  }

  async generateApiKey(data: {
    name: string;
    permissions: string[];
  }): Promise<ApiKey & { secret: string }> {
    return this.request('/api/user/api_keys/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteApiKey(key_id: string): Promise<void> {
    return this.request(`/api/user/api_keys/${key_id}`, {
      method: 'DELETE',
    });
  }

  // ============================================================================
  // BILLING
  // ============================================================================

  async getBillingStatus(): Promise<BillingStatus> {
    if (USE_MOCK) {
      await this.delay(200);
      return {
        status: 'trialing',
        plan: 'pro',
        price_id: 'price_1ProMonthly',
        current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        cancel_at_period_end: false,
        trial_end: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      };
    }
    return this.request<BillingStatus>('/api/billing/status');
  }

  async getBillingUsage(): Promise<BillingUsage> {
    if (USE_MOCK) {
      await this.delay(200);
      return {
        trades_count: 65,
        trades_limit: 100,
        days_remaining: 2,
        trial_trades_remaining: 35,
        brokers_connected: 2,
        brokers_limit: 2,
        strategies_active: 1,
        strategies_limit: 1,
      };
    }
    return this.request<BillingUsage>('/api/billing/usage');
  }

  async createCheckout(data: {
    price_id: string;
    success_url: string;
    cancel_url: string;
  }): Promise<{ url: string; session_id: string }> {
    return this.request('/api/billing/checkout', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async cancelSubscription(): Promise<{ success: boolean; effective_date: string }> {
    return this.request('/api/billing/cancel', {
      method: 'POST',
    });
  }

  // ============================================================================
  // LOGS
  // ============================================================================

  async getWebhookLogs(params?: {
    limit?: number;
    offset?: number;
  }): Promise<WebhookLog[]> {
    const query = new URLSearchParams();
    if (params?.limit) query.append('limit', params.limit.toString());
    if (params?.offset) query.append('offset', params.offset.toString());
    
    const queryString = query.toString();
    return this.request<WebhookLog[]>(
      `/api/logs/webhooks${queryString ? `?${queryString}` : ''}`
    );
  }

  // ============================================================================
  // AUTH UTILITIES
  // ============================================================================

  async resetPassword(email: string): Promise<{ success: boolean; message: string }> {
    return this.request('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  // ============================================================================
  // WEBHOOK (for documentation only - called by TradingView)
  // ============================================================================

  /**
   * This endpoint is called by TradingView, not by the frontend
   * Documented here for completeness
   */
  webhookEndpointDocs = {
    method: 'POST',
    path: '/webhook',
    headers: {
      'X-API-Key': 'your_api_key_here',
    },
    body: {
      symbol: 'ES',
      action: 'BUY', // or 'SELL'
      price: 4825.50,
      sl: 4815.00,
      tp: 4850.00,
      qty: 1,
      tag: 'ES_Breakout_Long',
    },
  };
}

export const enhancedApiClient = new EnhancedApiClient();

// Also export as default for convenience
export default enhancedApiClient;
