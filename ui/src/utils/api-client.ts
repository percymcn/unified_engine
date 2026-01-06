import { projectId, publicAnonKey } from './supabase/info';
import { mockBackend } from './mock-backend';

// Use unified auth service for auth endpoints
const AUTH_API_BASE_URL = process.env.VITE_AUTH_API_URL || 'https://unifiedash.fluxeo.net/api/auth';
// Use broker-specific endpoints via nginx proxy
const BROKER_API_BASE_URL = process.env.VITE_BROKER_API_URL || 'https://unifiedash.fluxeo.net/api/broker';

// Set to false to use real backend
const USE_MOCK_BACKEND = process.env.VITE_USE_MOCK_BACKEND === 'true';

export interface BrokerAccount {
  id: string;
  broker: string;
  accountType: 'live' | 'demo';
  balance: number;
  equity: number;
  margin: number;
  status: 'connected' | 'disconnected' | 'error';
  createdAt: string;
}

export interface Position {
  id: string;
  accountId: string;
  symbol: string;
  side: 'buy' | 'sell';
  size: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  openedAt: string;
}

export interface Order {
  id: string;
  accountId: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit' | 'stop';
  size: number;
  price?: number;
  status: 'pending' | 'filled' | 'canceled' | 'rejected';
  createdAt: string;
}

export interface RiskSettings {
  accountId: string;
  maxRiskPercent: number;
  defaultStopLoss: number;
  defaultTakeProfit: number;
  maxPositionSize: number;
}

export interface ApiKey {
  id: string;
  name: string;
  key: string;
  secret?: string;
  permissions: string[];
  createdAt: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  metadata?: any;
}

export interface BillingInfo {
  plan: 'starter' | 'pro' | 'elite';
  status: 'active' | 'trial' | 'canceled';
  trialEndsAt?: string;
  currentPeriodEnd: string;
  tradesUsed: number;
  tradesLimit: number;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async request(endpoint: string, options: RequestInit = {}, useAuth: boolean = true) {
    // Use relative paths - nginx will proxy them correctly
    // All API calls go through https://unifiedash.fluxeo.net/api/*
    const baseUrl = window.location.origin; // Will be https://unifiedash.fluxeo.net
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    };
    
    if (useAuth && this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    // Ensure endpoint starts with /api/
    let normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    
    // If endpoint doesn't start with /api/, prepend appropriate path
    if (!normalizedEndpoint.startsWith('/api/')) {
      if (normalizedEndpoint.startsWith('/auth') || normalizedEndpoint.startsWith('/billing') || normalizedEndpoint.startsWith('/register')) {
        normalizedEndpoint = `/api${normalizedEndpoint}`;
      } else {
        normalizedEndpoint = `/api${normalizedEndpoint}`;
      }
    }
    
    const response = await fetch(`${baseUrl}${normalizedEndpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = 'Request failed';
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.message || errorData.detail || errorMessage;
      } catch {
        errorMessage = `Request failed with status ${response.status}`;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // Broker Accounts
  async getBrokerAccounts(): Promise<BrokerAccount[]> {
    if (USE_MOCK_BACKEND) return mockBackend.getBrokerAccounts();
    return this.request('/accounts');
  }

  async addBrokerAccount(data: {
    broker: string;
    accountType: 'live' | 'demo';
    apiKey: string;
    apiSecret: string;
  }): Promise<BrokerAccount> {
    if (USE_MOCK_BACKEND) return mockBackend.addBrokerAccount(data);
    return this.request('/accounts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateBrokerAccount(id: string, data: Partial<BrokerAccount>): Promise<BrokerAccount> {
    if (USE_MOCK_BACKEND) return mockBackend.updateBrokerAccount(id, data);
    return this.request(`/accounts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteBrokerAccount(id: string): Promise<void> {
    if (USE_MOCK_BACKEND) return mockBackend.deleteBrokerAccount(id);
    return this.request(`/accounts/${id}`, {
      method: 'DELETE',
    });
  }

  async testBrokerConnection(id: string): Promise<{ status: string; latency: number }> {
    if (USE_MOCK_BACKEND) return mockBackend.testBrokerConnection(id);
    return this.request(`/accounts/${id}/test`, {
      method: 'POST',
    });
  }

  // Positions
  async getPositions(accountId?: string): Promise<Position[]> {
    if (USE_MOCK_BACKEND) return mockBackend.getPositions(accountId);
    const query = accountId ? `?accountId=${accountId}` : '';
    return this.request(`/positions${query}`);
  }

  async closePosition(id: string): Promise<{ success: boolean; pnl: number }> {
    if (USE_MOCK_BACKEND) return mockBackend.closePosition(id);
    return this.request(`/positions/${id}/close`, {
      method: 'POST',
    });
  }

  // Orders
  async getOrders(accountId?: string, status?: string): Promise<Order[]> {
    if (USE_MOCK_BACKEND) return mockBackend.getOrders(accountId, status);
    const params = new URLSearchParams();
    if (accountId) params.append('accountId', accountId);
    if (status) params.append('status', status);
    const query = params.toString() ? `?${params}` : '';
    return this.request(`/orders${query}`);
  }

  async placeOrder(data: {
    accountId: string;
    symbol: string;
    side: 'buy' | 'sell';
    type: 'market' | 'limit' | 'stop';
    size: number;
    price?: number;
  }): Promise<Order> {
    if (USE_MOCK_BACKEND) return mockBackend.placeOrder(data);
    return this.request('/orders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async cancelOrder(id: string): Promise<void> {
    if (USE_MOCK_BACKEND) return mockBackend.cancelOrder(id);
    return this.request(`/orders/${id}/cancel`, {
      method: 'POST',
    });
  }

  // Risk Settings
  async getRiskSettings(accountId: string): Promise<RiskSettings> {
    if (USE_MOCK_BACKEND) return mockBackend.getRiskSettings(accountId);
    return this.request(`/risk/${accountId}`);
  }

  async updateRiskSettings(accountId: string, data: Partial<RiskSettings>): Promise<RiskSettings> {
    if (USE_MOCK_BACKEND) return mockBackend.updateRiskSettings(accountId, data);
    return this.request(`/risk/${accountId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async calculatePositionSize(data: {
    accountBalance: number;
    riskPercent: number;
    stopLossPips: number;
  }): Promise<{ lotSize: number; riskAmount: number }> {
    if (USE_MOCK_BACKEND) return mockBackend.calculatePositionSize(data);
    return this.request('/risk/calculate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // API Keys
  async getApiKeys(): Promise<ApiKey[]> {
    if (USE_MOCK_BACKEND) return mockBackend.getApiKeys();
    return this.request('/api-keys');
  }

  async generateApiKey(data: {
    name: string;
    permissions: string[];
  }): Promise<ApiKey> {
    if (USE_MOCK_BACKEND) return mockBackend.generateApiKey(data);
    return this.request('/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async revokeApiKey(id: string): Promise<void> {
    if (USE_MOCK_BACKEND) return mockBackend.revokeApiKey(id);
    return this.request(`/api-keys/${id}`, {
      method: 'DELETE',
    });
  }

  async getWebhookUrl(keyId: string): Promise<{ url: string; signature: string }> {
    if (USE_MOCK_BACKEND) return mockBackend.getWebhookUrl(keyId);
    return this.request(`/api-keys/${keyId}/webhook`);
  }

  // Logs
  async getLogs(limit = 100, level?: string): Promise<LogEntry[]> {
    if (USE_MOCK_BACKEND) return mockBackend.getLogs(limit, level);
    const params = new URLSearchParams({ limit: limit.toString() });
    if (level) params.append('level', level);
    return this.request(`/logs?${params}`);
  }

  // Billing
  async getBillingInfo(): Promise<BillingInfo> {
    if (USE_MOCK_BACKEND) return mockBackend.getBillingInfo();
    const data = await this.request('/billing/status');
    return {
      plan: data.plan || 'trial',
      status: data.status || 'trial',
      trialEndsAt: data.trial_end || undefined,
      currentPeriodEnd: data.current_period_end || new Date().toISOString(),
      tradesUsed: 0,
      tradesLimit: 100
    };
  }

  async createCheckoutSession(plan: string): Promise<{ url: string }> {
    if (USE_MOCK_BACKEND) return mockBackend.createCheckoutSession(plan);
    const priceMap: Record<string, string> = {
      'starter': 'price_starter',
      'pro': 'price_pro',
      'elite': 'price_elite'
    };
    const data = await this.request('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({
        price_id: priceMap[plan] || `price_${plan}`,
        success_url: `${window.location.origin}/dashboard?checkout=success`,
        cancel_url: `${window.location.origin}/dashboard?checkout=canceled`
      }),
    });
    return { url: data.url };
  }

  async cancelSubscription(): Promise<void> {
    if (USE_MOCK_BACKEND) return mockBackend.cancelSubscription();
    await this.request('/billing/cancel', {
      method: 'POST',
    });
  }

  // Analytics
  async getKPIs(): Promise<{
    totalTrades: number;
    winRate: number;
    totalPnL: number;
    activePositions: number;
  }> {
    if (USE_MOCK_BACKEND) return mockBackend.getKPIs();
    return this.request('/analytics/kpis');
  }

  async getChartData(timeframe: string): Promise<Array<{
    date: string;
    pnl: number;
    volume: number;
  }>> {
    if (USE_MOCK_BACKEND) return mockBackend.getChartData(timeframe);
    return this.request(`/analytics/chart?timeframe=${timeframe}`);
  }

  // Admin
  async getUsers(): Promise<any[]> {
    if (USE_MOCK_BACKEND) return mockBackend.getUsers();
    return this.request('/admin/users');
  }

  async updateUserRole(userId: string, role: string): Promise<void> {
    if (USE_MOCK_BACKEND) return mockBackend.updateUserRole(userId, role);
    return this.request(`/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
  }

  async getPlatformStats(): Promise<{
    totalUsers: number;
    activeTrades: number;
    revenue: number;
  }> {
    if (USE_MOCK_BACKEND) return mockBackend.getPlatformStats();
    return this.request('/admin/stats');
  }
}

export const apiClient = new ApiClient();
