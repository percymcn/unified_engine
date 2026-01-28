/**
 * AI Strategy Suite Type Definitions
 */

// Pine Script Types
export interface PineScript {
  id?: string;
  userId: number;
  name: string;
  code: string;
  version: number;
  lastModified: string;
  isValid: boolean;
  errors?: PineScriptError[];
}

export interface PineScriptError {
  line: number;
  column?: number;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface PineFixRequest {
  code: string;
  errors?: string;
  requirements?: string;
  strategyType?: 'long_only' | 'short_only' | 'both';
  riskManagement?: {
    stopLossType: 'atr' | 'percent' | 'fixed';
    stopLossValue: number;
    takeProfitRatio: number;
  };
}

export interface PineFixResponse {
  success: boolean;
  fixedCode: string;
  explanation?: string;
  warnings?: string[];
  webhookPayload?: WebhookPayload;
}

// TradingView Chart Types
export interface ChartConfig {
  symbol: string;
  interval: string;
  timezone: string;
  theme: 'light' | 'dark';
  style: string;
  locale: string;
  enablePublishing: boolean;
  allowSymbolChange: boolean;
  container: string;
  width: string | number;
  height: string | number;
}

export interface ChartPosition {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  entryPrice: number;
  currentPrice: number;
  stopLoss?: number;
  takeProfit?: number;
  size: number;
  unrealizedPnl: number;
  entryTime: string;
}

// Webhook Types
export interface WebhookPayload {
  webhook_key?: string;
  symbol: string;
  action: 'buy' | 'sell' | 'close' | 'close_long' | 'close_short';
  quantity?: number;
  riskPercent?: number;
  stopLoss?: string | number;
  takeProfit?: string | number;
  comment?: string;
}

export interface AlertTemplate {
  name: string;
  message: string;
  webhookUrl: string;
  payload: WebhookPayload;
}

// Backtest Types
export interface BacktestConfig {
  symbol: string;
  timeframe: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  commission: number;
  slippage: number;
}

export interface BacktestTrade {
  id: string;
  entryTime: string;
  exitTime: string;
  side: 'long' | 'short';
  entryPrice: number;
  exitPrice: number;
  size: number;
  pnl: number;
  pnlPercent: number;
  commission: number;
  exitReason: 'sl' | 'tp' | 'signal' | 'eod';
}

export interface BacktestResults {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  totalPnl: number;
  totalPnlPercent: number;
  maxDrawdown: number;
  maxDrawdownPercent: number;
  sharpeRatio: number;
  sortinoRatio: number;
  profitFactor: number;
  averageWin: number;
  averageLoss: number;
  largestWin: number;
  largestLoss: number;
  averageHoldingPeriod: number;
  equityCurve: EquityPoint[];
  trades: BacktestTrade[];
  monthlyReturns: MonthlyReturn[];
}

export interface EquityPoint {
  date: string;
  equity: number;
  drawdown: number;
}

export interface MonthlyReturn {
  month: string;
  return: number;
  trades: number;
}

// AI Coach Types
export interface StrategyAnalysis {
  biases: BiasDetection[];
  riskIssues: RiskIssue[];
  suggestions: Suggestion[];
  optimizedCode?: string;
  performanceProjection?: PerformanceProjection;
}

export interface BiasDetection {
  type: 'time' | 'day' | 'session' | 'trend';
  description: string;
  severity: 'low' | 'medium' | 'high';
  evidence: string;
}

export interface RiskIssue {
  type: 'no_sl' | 'large_position' | 'correlated' | 'overleverage';
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  recommendation: string;
}

export interface Suggestion {
  type: 'parameter' | 'logic' | 'filter' | 'exit';
  description: string;
  expectedImpact: string;
  codeSnippet?: string;
}

export interface PerformanceProjection {
  currentCagr: number;
  projectedCagr: number;
  currentSharpe: number;
  projectedSharpe: number;
  confidence: number;
}

// AI Coach Chat Types
export interface AICoachMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// State Types
export interface AISuiteState {
  activeTab: 'chart' | 'editor' | 'backtest' | 'coach';
  currentScript: PineScript | null;
  chartConfig: ChartConfig;
  backtestResults: BacktestResults | null;
  isProcessing: boolean;
  error: string | null;
}
