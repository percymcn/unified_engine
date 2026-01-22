export type BrokerType = 'tradelocker' | 'tradovate' | 'projectx' | 'topstep' | 'truforex' | 'mt4' | 'mt5';
export type AccountType = 'live' | 'demo' | 'funded' | 'evaluation';

export interface Account {
  id: number;
  account_id: string;
  broker: BrokerType;
  account_type: AccountType;
  currency: string;
  leverage: number;
  is_active: boolean;
  is_connected: boolean;
  balance?: number;
  equity?: number;
  margin?: number;
  free_margin?: number;
  last_sync?: string;
  created_at: string;
}

export interface AccountCreate {
  account_id: string;
  broker: BrokerType;
  account_type: AccountType;
  currency?: string;
  leverage?: number;
  api_key?: string;
  api_secret?: string;
  server?: string;
  login?: number;
  password?: string;
  broker_config?: Record<string, unknown>;
}

export interface AccountUpdate {
  balance?: number;
  equity?: number;
  margin?: number;
  free_margin?: number;
  is_active?: boolean;
  is_connected?: boolean;
  api_key?: string;
  api_secret?: string;
  broker_config?: Record<string, unknown>;
}

export interface AccountBalance {
  account_id: string;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  last_sync?: string;
}

// Broker display names for UI
export const BROKER_DISPLAY_NAMES: Record<BrokerType, string> = {
  tradelocker: 'TradeLocker',
  tradovate: 'Tradovate',
  projectx: 'ProjectX',
  topstep: 'TopStep',
  truforex: 'TruForex',
  mt4: 'MetaTrader 4',
  mt5: 'MetaTrader 5',
};

// Account type display names for UI
export const ACCOUNT_TYPE_DISPLAY_NAMES: Record<AccountType, string> = {
  live: 'Live',
  demo: 'Demo',
  funded: 'Funded',
  evaluation: 'Evaluation',
};

// Broker-specific credential requirements
export interface BrokerCredentialConfig {
  fields: Array<{
    name: string;
    label: string;
    type: 'text' | 'password' | 'number';
    required: boolean;
    placeholder?: string;
  }>;
}

// Position sizing modes for trade size calculation
export type PositionSizingMode = 'fixed' | 'percent_balance' | 'percent_equity' | 'risk_based';

// Account settings for position sizing and risk management
export interface AccountSettings {
  accountId: number;
  positionSizing: {
    mode: PositionSizingMode;
    fixedLotSize: number;
    percentOfBalance: number;
    percentOfEquity: number;
    riskPercentPerTrade: number;
  };
  riskLimits: {
    maxPositionSize: number | null;
    maxDailyLoss: number | null;
    maxDailyLossPct: number | null;
    maxDrawdownPct: number | null;
    maxOpenPositions: number | null;
    maxDailyTrades: number | null;
    tradeCooldownSeconds: number | null;
  };
  grouping: {
    groupId: number | null;
    groupName: string | null;
    groupColor: string | null;
  };
  routing: {
    isSignalEnabled: boolean;
    signalPriority: number;
  };
}

// Request to update account settings
export interface AccountSettingsUpdate {
  positionSizingMode?: PositionSizingMode;
  fixedLotSize?: number;
  percentOfBalance?: number;
  percentOfEquity?: number;
  riskPercentPerTrade?: number;
  maxPositionSize?: number | null;
  maxDailyLoss?: number | null;
  maxDailyLossPct?: number | null;
  maxDrawdownPct?: number | null;
  maxOpenPositions?: number | null;
  maxDailyTrades?: number | null;
  tradeCooldownSeconds?: number | null;
  groupId?: number | null;
  isSignalEnabled?: boolean;
  signalPriority?: number;
}

// Account group for organizing trading accounts
export interface AccountGroup {
  id: number;
  name: string;
  description: string | null;
  color: string;
  icon: string;
  accountCount: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

// Request to create an account group
export interface CreateAccountGroupRequest {
  name: string;
  description?: string;
  color?: string;
  icon?: string;
}

// Request to update an account group
export interface UpdateAccountGroupRequest {
  name?: string;
  description?: string;
  color?: string;
  icon?: string;
  isActive?: boolean;
}

// Extended account type with group and settings info
export interface AccountWithSettings extends Account {
  groupId?: number | null;
  groupName?: string | null;
  groupColor?: string | null;
  isSignalEnabled?: boolean;
  signalPriority?: number;
}

export const BROKER_CREDENTIAL_CONFIG: Record<BrokerType, BrokerCredentialConfig> = {
  tradelocker: {
    fields: [
      { name: 'api_key', label: 'API Key', type: 'text', required: true, placeholder: 'Enter API key' },
      { name: 'api_secret', label: 'API Secret', type: 'password', required: true, placeholder: 'Enter API secret' },
    ],
  },
  tradovate: {
    fields: [
      { name: 'api_key', label: 'API Key', type: 'text', required: true, placeholder: 'Enter API key' },
      { name: 'api_secret', label: 'API Secret', type: 'password', required: true, placeholder: 'Enter API secret' },
    ],
  },
  projectx: {
    fields: [
      { name: 'api_key', label: 'API Key', type: 'text', required: true, placeholder: 'Enter API key' },
    ],
  },
  topstep: {
    fields: [
      { name: 'api_key', label: 'API Key', type: 'text', required: true, placeholder: 'Enter API key' },
    ],
  },
  truforex: {
    fields: [
      { name: 'api_key', label: 'API Key', type: 'text', required: true, placeholder: 'Enter API key' },
      { name: 'api_secret', label: 'API Secret', type: 'password', required: true, placeholder: 'Enter API secret' },
    ],
  },
  mt4: {
    fields: [
      { name: 'login', label: 'Login', type: 'number', required: true, placeholder: 'Account number' },
      { name: 'password', label: 'Password', type: 'password', required: true, placeholder: 'Trading password' },
      { name: 'server', label: 'Server', type: 'text', required: true, placeholder: 'e.g., ICMarkets-Demo' },
    ],
  },
  mt5: {
    fields: [
      { name: 'login', label: 'Login', type: 'number', required: true, placeholder: 'Account number' },
      { name: 'password', label: 'Password', type: 'password', required: true, placeholder: 'Trading password' },
      { name: 'server', label: 'Server', type: 'text', required: true, placeholder: 'e.g., ICMarkets-Demo' },
    ],
  },
};
