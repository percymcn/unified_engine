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
