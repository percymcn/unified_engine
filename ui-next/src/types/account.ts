export type BrokerType = 'tradelocker' | 'tradovate' | 'projectx' | 'topstep' | 'truforex' | 'mt4' | 'mt5';
export type AccountType = 'live' | 'demo' | 'funded' | 'evaluation';

export interface Account {
  id: number;
  account_id: string;
  user_id?: number;  // Patch 1.2.1
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
  webhook_key?: string | null;  // Patch 1.2.1
  // Broker account selection (for multi-account brokers)
  enabled_broker_account_ids?: string[];
  default_broker_account_id?: string | null;
  discovered_accounts_cache?: Array<Record<string, unknown>>;
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
  // Broker account selection (for multi-account brokers)
  enabled_broker_account_ids?: string[];
  default_broker_account_id?: string;
  discovered_accounts_cache?: Array<Record<string, unknown>>;
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
  // Broker account selection
  enabled_broker_account_ids?: string[];
  default_broker_account_id?: string;
  discovered_accounts_cache?: Array<Record<string, unknown>>;
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

// Prop firm challenge phases
export type PropPhase = 'evaluation_1' | 'evaluation_2' | 'funded' | 'payout' | 'none';

// Common prop firm providers
export const PROP_PROVIDERS = [
  'FTMO', 'Topstep', 'Apex Trader', 'MyFundedFX', 'The5%ers', 'E8 Funding',
  'True Forex Funds', 'Funded Next', 'SurgeTrader', 'Lux Trading', 'Other'
] as const;

// Account settings for position sizing and risk management
export interface AccountSettings {
  accountId: number;
  account?: Account; // Account details from backend
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
    // Default stop loss/take profit in broker-specific units (pips/points/percent)
    // NOTE: These are stored in broker-specific units because they cannot be converted
    // to absolute prices without an entry price. When used with a signal, the backend
    // should convert them using the signal's entry price. Backend conversion is not
    // yet implemented, so these are stored as metadata for future enhancement.
    defaultStopLoss: number | null;
    defaultTakeProfit: number | null;
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
  // Prop firm specific settings (stored in extra_metadata)
  propRules: {
    isEnabled: boolean;
    provider: string | null;
    phase: PropPhase;
    profitTargetPct: number | null;
    profitTargetAmount: number | null;
    maxDailyLossPct: number | null;
    maxDailyLossAmount: number | null;
    maxDrawdownPct: number | null;
    maxDrawdownAmount: number | null;
    trailingDrawdown: boolean;
    challengeStartDate: string | null;
    challengeEndDate: string | null;
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
  // Default stop loss/take profit in broker-specific units (pips/points/percent)
  // Stored as metadata - backend should convert to absolute prices when used with signals
  defaultStopLoss?: number | null;
  defaultTakeProfit?: number | null;
  groupId?: number | null;
  isSignalEnabled?: boolean;
  signalPriority?: number;
  // Prop firm settings (stored in extra_metadata)
  propRulesEnabled?: boolean;
  propProvider?: string | null;
  propPhase?: PropPhase;
  propProfitTargetPct?: number | null;
  propProfitTargetAmount?: number | null;
  propMaxDailyLossPct?: number | null;
  propMaxDailyLossAmount?: number | null;
  propMaxDrawdownPct?: number | null;
  propMaxDrawdownAmount?: number | null;
  propTrailingDrawdown?: boolean;
  propChallengeStartDate?: string | null;
  propChallengeEndDate?: string | null;
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
