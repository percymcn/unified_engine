import type { BrokerAccount, Position, Order, LogEntry, ApiKey, BillingInfo } from './api-client';

export const mockBrokerAccounts: BrokerAccount[] = [
  {
    id: '1',
    broker: 'TradeLocker',
    accountType: 'live',
    balance: 50000,
    equity: 52340,
    margin: 2500,
    status: 'connected',
    createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '2',
    broker: 'MT5',
    accountType: 'demo',
    balance: 100000,
    equity: 98750,
    margin: 1200,
    status: 'connected',
    createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '3',
    broker: 'Topstep',
    accountType: 'live',
    balance: 150000,
    equity: 151200,
    margin: 3800,
    status: 'connected',
    createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

export const mockPositions: Position[] = [
  {
    id: '1',
    accountId: '1',
    symbol: 'EURUSD',
    side: 'buy',
    size: 1.5,
    entryPrice: 1.0850,
    currentPrice: 1.0875,
    pnl: 375,
    openedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '2',
    accountId: '1',
    symbol: 'GBPUSD',
    side: 'sell',
    size: 1.0,
    entryPrice: 1.2650,
    currentPrice: 1.2625,
    pnl: 250,
    openedAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '3',
    accountId: '2',
    symbol: 'BTCUSD',
    side: 'buy',
    size: 0.5,
    entryPrice: 45000,
    currentPrice: 45800,
    pnl: 400,
    openedAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '4',
    accountId: '3',
    symbol: 'NQ',
    side: 'buy',
    size: 2.0,
    entryPrice: 16500,
    currentPrice: 16525,
    pnl: 1000,
    openedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  },
];

export const mockOrders: Order[] = [
  {
    id: '1',
    accountId: '1',
    symbol: 'EURUSD',
    side: 'buy',
    type: 'limit',
    size: 1.0,
    price: 1.0825,
    status: 'pending',
    createdAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '2',
    accountId: '1',
    symbol: 'GBPUSD',
    side: 'sell',
    type: 'market',
    size: 1.5,
    status: 'filled',
    createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '3',
    accountId: '2',
    symbol: 'BTCUSD',
    side: 'buy',
    type: 'stop',
    size: 0.3,
    price: 44500,
    status: 'pending',
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '4',
    accountId: '3',
    symbol: 'NQ',
    side: 'sell',
    type: 'market',
    size: 1.0,
    status: 'canceled',
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
];

export const mockLogs: LogEntry[] = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    level: 'info',
    message: 'Position opened: EURUSD BUY 1.5 lots @ 1.0850',
    metadata: { accountId: '1', positionId: '1' },
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    level: 'info',
    message: 'Order filled: GBPUSD SELL 1.0 lots @ 1.2650',
    metadata: { accountId: '1', orderId: '2' },
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    level: 'warning',
    message: 'High risk detected: Position size exceeds 2% risk',
    metadata: { accountId: '2', riskPercent: 2.3 },
  },
  {
    id: '4',
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    level: 'info',
    message: 'TradingView webhook received: BTC/USD signal',
    metadata: { symbol: 'BTCUSD', signal: 'BUY' },
  },
  {
    id: '5',
    timestamp: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    level: 'error',
    message: 'Failed to connect to MT5 account: Invalid credentials',
    metadata: { accountId: '2', broker: 'MT5' },
  },
];

export const mockApiKeys: ApiKey[] = [
  {
    id: '1',
    name: 'TradingView Webhook',
    key: 'tfk_live_abc123def456ghi789',
    permissions: ['webhook', 'read'],
    createdAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '2',
    name: 'Mobile App',
    key: 'tfk_live_xyz789uvw456rst123',
    permissions: ['read', 'write'],
    createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

export const mockBillingInfo: BillingInfo = {
  plan: 'pro',
  status: 'trial',
  trialEndsAt: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
  currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  tradesUsed: 45,
  tradesLimit: 100,
};

export const mockKPIs = {
  totalTrades: 127,
  winRate: 68.5,
  totalPnL: 12450,
  activePositions: 4,
};

export const mockChartData = [
  { date: '2025-10-09', pnl: 450, volume: 12 },
  { date: '2025-10-10', pnl: 780, volume: 18 },
  { date: '2025-10-11', pnl: -230, volume: 8 },
  { date: '2025-10-12', pnl: 1200, volume: 22 },
  { date: '2025-10-13', pnl: 340, volume: 14 },
  { date: '2025-10-14', pnl: 920, volume: 16 },
  { date: '2025-10-15', pnl: 560, volume: 11 },
  { date: '2025-10-16', pnl: 1100, volume: 19 },
];

// Helper to generate random data
export function generateRandomPosition(accountId: string): Position {
  const symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'ETHUSD', 'NQ', 'ES'];
  const symbol = symbols[Math.floor(Math.random() * symbols.length)];
  const side = Math.random() > 0.5 ? 'buy' : 'sell';
  const entryPrice = Math.random() * 50000 + 1000;
  const currentPrice = entryPrice * (1 + (Math.random() - 0.5) * 0.02);
  const size = Math.random() * 2 + 0.1;
  const pnl = (currentPrice - entryPrice) * size * (side === 'buy' ? 1 : -1);

  return {
    id: Math.random().toString(36).substr(2, 9),
    accountId,
    symbol,
    side,
    size: parseFloat(size.toFixed(2)),
    entryPrice: parseFloat(entryPrice.toFixed(2)),
    currentPrice: parseFloat(currentPrice.toFixed(2)),
    pnl: parseFloat(pnl.toFixed(2)),
    openedAt: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
  };
}

export function generateRandomOrder(accountId: string): Order {
  const symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'ETHUSD'];
  const types: Array<'market' | 'limit' | 'stop'> = ['market', 'limit', 'stop'];
  const statuses: Array<'pending' | 'filled' | 'canceled' | 'rejected'> = ['pending', 'filled', 'canceled', 'rejected'];

  return {
    id: Math.random().toString(36).substr(2, 9),
    accountId,
    symbol: symbols[Math.floor(Math.random() * symbols.length)],
    side: Math.random() > 0.5 ? 'buy' : 'sell',
    type: types[Math.floor(Math.random() * types.length)],
    size: parseFloat((Math.random() * 2 + 0.1).toFixed(2)),
    price: Math.random() > 0.5 ? parseFloat((Math.random() * 50000 + 1000).toFixed(2)) : undefined,
    status: statuses[Math.floor(Math.random() * statuses.length)],
    createdAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  };
}
