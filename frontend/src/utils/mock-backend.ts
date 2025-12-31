/**
 * Mock Backend Simulator
 * This simulates the backend API responses when the actual backend is not available
 * Remove this file once connected to real API at http://192.168.1.242:6894/api
 */

import {
  mockBrokerAccounts,
  mockPositions,
  mockOrders,
  mockLogs,
  mockApiKeys,
  mockBillingInfo,
  mockKPIs,
  mockChartData,
  generateRandomPosition,
  generateRandomOrder,
} from './mock-data';
import type { BrokerAccount, Position, Order, ApiKey, RiskSettings } from './api-client';

let accounts = [...mockBrokerAccounts];
let positions = [...mockPositions];
let orders = [...mockOrders];
let logs = [...mockLogs];
let apiKeys = [...mockApiKeys];

export const mockBackend = {
  // Broker Accounts
  async getBrokerAccounts(): Promise<BrokerAccount[]> {
    await delay(300);
    return accounts;
  },

  async addBrokerAccount(data: any): Promise<BrokerAccount> {
    await delay(500);
    const newAccount: BrokerAccount = {
      id: (accounts.length + 1).toString(),
      broker: data.broker,
      accountType: data.accountType,
      balance: 100000,
      equity: 100000,
      margin: 0,
      status: 'connected',
      createdAt: new Date().toISOString(),
    };
    accounts.push(newAccount);
    return newAccount;
  },

  async updateBrokerAccount(id: string, data: Partial<BrokerAccount>): Promise<BrokerAccount> {
    await delay(300);
    const index = accounts.findIndex(a => a.id === id);
    if (index === -1) throw new Error('Account not found');
    accounts[index] = { ...accounts[index], ...data };
    return accounts[index];
  },

  async deleteBrokerAccount(id: string): Promise<void> {
    await delay(300);
    accounts = accounts.filter(a => a.id !== id);
  },

  async testBrokerConnection(id: string): Promise<{ status: string; latency: number }> {
    await delay(800);
    return {
      status: 'success',
      latency: Math.floor(Math.random() * 200) + 50,
    };
  },

  // Positions
  async getPositions(accountId?: string): Promise<Position[]> {
    await delay(200);
    if (accountId) {
      return positions.filter(p => p.accountId === accountId);
    }
    return positions;
  },

  async closePosition(id: string): Promise<{ success: boolean; pnl: number }> {
    await delay(400);
    const position = positions.find(p => p.id === id);
    if (!position) throw new Error('Position not found');
    
    positions = positions.filter(p => p.id !== id);
    
    return {
      success: true,
      pnl: position.pnl,
    };
  },

  // Orders
  async getOrders(accountId?: string, status?: string): Promise<Order[]> {
    await delay(200);
    let filtered = orders;
    if (accountId) {
      filtered = filtered.filter(o => o.accountId === accountId);
    }
    if (status) {
      filtered = filtered.filter(o => o.status === status);
    }
    return filtered;
  },

  async placeOrder(data: any): Promise<Order> {
    await delay(500);
    const newOrder: Order = {
      id: (orders.length + 1).toString(),
      accountId: data.accountId,
      symbol: data.symbol,
      side: data.side,
      type: data.type,
      size: data.size,
      price: data.price,
      status: 'filled',
      createdAt: new Date().toISOString(),
    };
    orders.push(newOrder);
    
    // Also create a position if market order
    if (data.type === 'market') {
      const newPosition = generateRandomPosition(data.accountId);
      newPosition.symbol = data.symbol;
      newPosition.side = data.side;
      newPosition.size = data.size;
      positions.push(newPosition);
    }
    
    return newOrder;
  },

  async cancelOrder(id: string): Promise<void> {
    await delay(300);
    const index = orders.findIndex(o => o.id === id);
    if (index === -1) throw new Error('Order not found');
    orders[index].status = 'canceled';
  },

  // Risk Settings
  async getRiskSettings(accountId: string): Promise<RiskSettings> {
    await delay(200);
    return {
      accountId,
      maxRiskPercent: 2.0,
      defaultStopLoss: 1.5,
      defaultTakeProfit: 3.0,
      maxPositionSize: 10.0,
    };
  },

  async updateRiskSettings(accountId: string, data: Partial<RiskSettings>): Promise<RiskSettings> {
    await delay(300);
    return {
      accountId,
      maxRiskPercent: data.maxRiskPercent ?? 2.0,
      defaultStopLoss: data.defaultStopLoss ?? 1.5,
      defaultTakeProfit: data.defaultTakeProfit ?? 3.0,
      maxPositionSize: data.maxPositionSize ?? 10.0,
    };
  },

  async calculatePositionSize(data: any): Promise<{ lotSize: number; riskAmount: number }> {
    await delay(200);
    const riskAmount = data.accountBalance * (data.riskPercent / 100);
    const lotSize = riskAmount / data.stopLossPips;
    return {
      lotSize: parseFloat(lotSize.toFixed(2)),
      riskAmount: parseFloat(riskAmount.toFixed(2)),
    };
  },

  // API Keys
  async getApiKeys(): Promise<ApiKey[]> {
    await delay(200);
    return apiKeys;
  },

  async generateApiKey(data: { name: string; permissions: string[] }): Promise<ApiKey> {
    await delay(500);
    const key = `tfk_${Math.random().toString(36).substr(2, 16)}_${Date.now().toString(36)}`;
    const newKey: ApiKey = {
      id: (apiKeys.length + 1).toString(),
      name: data.name,
      key,
      secret: `tfs_${Math.random().toString(36).substr(2, 32)}`,
      permissions: data.permissions,
      createdAt: new Date().toISOString(),
    };
    apiKeys.push(newKey);
    return newKey;
  },

  async revokeApiKey(id: string): Promise<void> {
    await delay(300);
    apiKeys = apiKeys.filter(k => k.id !== id);
  },

  async getWebhookUrl(keyId: string): Promise<{ url: string; signature: string }> {
    await delay(200);
    const key = apiKeys.find(k => k.id === keyId);
    if (!key) throw new Error('API key not found');
    
    return {
      url: `https://api.tradeflow.io/webhook/${key.key}`,
      signature: 'HMAC-SHA256',
    };
  },

  // Logs
  async getLogs(limit: number, level?: string): Promise<any[]> {
    await delay(200);
    let filtered = logs;
    if (level) {
      filtered = filtered.filter(l => l.level === level);
    }
    return filtered.slice(0, limit);
  },

  // Billing
  async getBillingInfo(): Promise<any> {
    await delay(200);
    return mockBillingInfo;
  },

  async createCheckoutSession(plan: string): Promise<{ url: string }> {
    await delay(500);
    return {
      url: `https://checkout.stripe.com/session_mock_${plan}_${Date.now()}`,
    };
  },

  async cancelSubscription(): Promise<void> {
    await delay(500);
  },

  // Analytics
  async getKPIs(): Promise<any> {
    await delay(200);
    return mockKPIs;
  },

  async getChartData(timeframe: string): Promise<any> {
    await delay(200);
    return mockChartData;
  },

  // Admin
  async getUsers(): Promise<any[]> {
    await delay(300);
    return [
      {
        id: '1',
        email: 'user1@example.com',
        name: 'John Doe',
        role: 'user',
        plan: 'pro',
        status: 'active',
      },
      {
        id: '2',
        email: 'user2@example.com',
        name: 'Jane Smith',
        role: 'user',
        plan: 'elite',
        status: 'active',
      },
    ];
  },

  async updateUserRole(userId: string, role: string): Promise<void> {
    await delay(300);
  },

  async getPlatformStats(): Promise<any> {
    await delay(300);
    return {
      totalUsers: 247,
      activeTrades: 1453,
      revenue: 9840,
    };
  },
};

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
