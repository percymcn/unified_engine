import {
  Account,
  AccountCreate,
  AccountBalance,
  BrokerType,
  AccountSettings,
  AccountSettingsUpdate,
  AccountGroup,
  CreateAccountGroupRequest,
  UpdateAccountGroupRequest,
  PositionSizingMode,
} from '@/types/account';

export class ApiError extends Error {
  status: number;
  payload?: Record<string, unknown>;

  constructor(message: string, status: number, payload?: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

/**
 * Response from connection test
 */
export interface TestConnectionResult {
  success: boolean;
  status: 'connected' | 'failed' | 'timeout';
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Discovered account from broker - standardized format
 */
export interface DiscoveredAccount {
  broker_account_id: string;
  account_number: string | null;
  display_name: string;
  status: 'active' | 'inactive' | 'blown' | 'unknown';
  account_type: 'eval' | 'funded' | 'demo' | 'unknown';
  broker: string;
  meta: Record<string, unknown>;
  // Legacy fields for backward compatibility
  id?: string;
  name?: string | null;
  currency?: string;
  is_live?: boolean;
  balance?: number;
  equity?: number;
}

/**
 * Response from account discovery
 */
export interface DiscoverAccountsResult {
  accounts: DiscoveredAccount[];
  message?: string | null;
}

export interface AccountSettingsResponse extends AccountSettings {
  account?: Account;
}

const buildApiError = async (response: Response, fallback: string) => {
  const payload = await response.json().catch(() => ({}));
  const message =
    (payload as { error?: string; detail?: string }).error ||
    (payload as { error?: string; detail?: string }).detail ||
    fallback;
  return new ApiError(message, response.status, payload as Record<string, unknown>);
};

interface ApiAccountSettingsData {
  account_id: number;
  position_sizing: {
    mode: string;
    fixed_lot_size: number | null;
    percent_of_balance: number | null;
    percent_of_equity: number | null;
    risk_percent_per_trade: number | null;
  };
  risk_limits: {
    max_position_size: number | null;
    max_daily_loss: number | null;
    max_daily_loss_pct: number | null;
    max_drawdown_pct: number | null;
    max_open_positions: number | null;
    max_daily_trades: number | null;
    trade_cooldown_seconds: number | null;
    default_stop_loss?: number | null;
    default_take_profit?: number | null;
  };
  grouping: {
    group_id: number | null;
    group_name: string | null;
    group_color: string | null;
  };
  routing: {
    is_signal_enabled: boolean;
    signal_priority: number;
  };
  account?: Account;
}

const mapAccountSettingsResponse = (data: ApiAccountSettingsData): AccountSettingsResponse => ({
  accountId: data.account_id,
  positionSizing: {
    mode: data.position_sizing.mode as PositionSizingMode,
    fixedLotSize: data.position_sizing.fixed_lot_size ?? 0,
    percentOfBalance: data.position_sizing.percent_of_balance ?? 0,
    percentOfEquity: data.position_sizing.percent_of_equity ?? 0,
    riskPercentPerTrade: data.position_sizing.risk_percent_per_trade ?? 0,
  },
  riskLimits: {
    maxPositionSize: data.risk_limits.max_position_size,
    maxDailyLoss: data.risk_limits.max_daily_loss,
    maxDailyLossPct: data.risk_limits.max_daily_loss_pct,
    maxDrawdownPct: data.risk_limits.max_drawdown_pct,
    maxOpenPositions: data.risk_limits.max_open_positions,
    maxDailyTrades: data.risk_limits.max_daily_trades,
    tradeCooldownSeconds: data.risk_limits.trade_cooldown_seconds,
    defaultStopLoss: data.risk_limits.default_stop_loss ?? null,
    defaultTakeProfit: data.risk_limits.default_take_profit ?? null,
  },
  grouping: {
    groupId: data.grouping.group_id,
    groupName: data.grouping.group_name,
    groupColor: data.grouping.group_color,
  },
  routing: {
    isSignalEnabled: data.routing.is_signal_enabled,
    signalPriority: data.routing.signal_priority,
  },
  account: data.account,
});

/**
 * Get all accounts for the authenticated user
 */
export async function getAccounts(): Promise<Account[]> {
  const response = await fetch('/api/accounts');

  if (!response.ok) {
    throw new Error(`Failed to fetch accounts: ${response.statusText}`);
  }

  const data = await response.json();
  if (Array.isArray(data)) {
    return data;
  }
  return data.accounts || [];
}

/**
 * Create a new broker account
 */
export async function createAccount(data: AccountCreate): Promise<Account> {
  const response = await fetch('/api/accounts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create account: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an existing account
 */
export async function updateAccount(
  id: number,
  data: Partial<AccountCreate>
): Promise<Account> {
  const response = await fetch(`/api/accounts/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update account: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete an account
 */
export async function deleteAccount(id: number): Promise<void> {
  const response = await fetch(`/api/accounts/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete account: ${response.statusText}`);
  }
}

/**
 * Sync account data with broker
 */
export async function syncAccount(id: number): Promise<Account> {
  const response = await fetch(`/api/accounts/${id}/sync`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to sync account: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get account balance from broker
 */
export async function getAccountBalance(id: number): Promise<AccountBalance> {
  const response = await fetch(`/api/accounts/${id}/balance`);

  if (!response.ok) {
    throw new Error(`Failed to fetch account balance: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Test broker connection with credentials before saving
 * Does not create an account - just validates credentials
 */
export async function testConnection(
  broker: BrokerType,
  credentials: Record<string, string>
): Promise<TestConnectionResult> {
  const response = await fetch('/api/accounts/test-connection', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ broker, credentials }),
  });

  // Always parse response - error info is in the body
  const result = await response.json();

  // Return the result regardless of status - it contains success/failure info
  return result as TestConnectionResult;
}

/**
 * Discover available accounts from broker using credentials
 * READ-ONLY operation - does not save credentials or create accounts
 */
export async function discoverAccounts(
  broker: BrokerType,
  credentials: Record<string, string>
): Promise<DiscoverAccountsResult> {
  const response = await fetch('/api/accounts/discover', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ broker, credentials }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to discover accounts' }));
    throw new Error(error.message || `Failed to discover accounts: ${response.statusText}`);
  }

  return response.json() as Promise<DiscoverAccountsResult>;
}

/**
 * Refresh discovered broker accounts for an account
 */
export async function refreshBrokerAccounts(accountId: number): Promise<DiscoverAccountsResult> {
  const response = await fetch(`/api/accounts/${accountId}/refresh-accounts`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to refresh accounts' }));
    throw new Error(error.message || `Failed to refresh accounts: ${response.statusText}`);
  }

  return response.json() as Promise<DiscoverAccountsResult>;
}

// ============================================================================
// Account Settings API
// ============================================================================
export async function getAccountSettings(accountId: number): Promise<AccountSettingsResponse> {
  const response = await fetch(`/api/accounts/${accountId}/settings`);

  if (!response.ok) {
    throw await buildApiError(response, 'Failed to fetch account settings');
  }

  const data = await response.json();

  return mapAccountSettingsResponse(data);
}

/**
 * Update account settings (position sizing, risk limits, routing)
 */
export async function updateAccountSettings(
  accountId: number,
  settings: AccountSettingsUpdate
): Promise<AccountSettingsResponse> {
  // Transform to API format (snake_case)
  const payload: Record<string, unknown> = {};

  if (settings.positionSizingMode !== undefined) {
    payload.position_sizing_mode = settings.positionSizingMode;
  }
  if (settings.fixedLotSize !== undefined) {
    payload.fixed_lot_size = settings.fixedLotSize;
  }
  if (settings.percentOfBalance !== undefined) {
    payload.percent_of_balance = settings.percentOfBalance;
  }
  if (settings.percentOfEquity !== undefined) {
    payload.percent_of_equity = settings.percentOfEquity;
  }
  if (settings.riskPercentPerTrade !== undefined) {
    payload.risk_percent_per_trade = settings.riskPercentPerTrade;
  }
  if (settings.maxPositionSize !== undefined) {
    payload.max_position_size = settings.maxPositionSize;
  }
  if (settings.maxDailyLoss !== undefined) {
    payload.max_daily_loss = settings.maxDailyLoss;
  }
  if (settings.maxDailyLossPct !== undefined) {
    payload.max_daily_loss_pct = settings.maxDailyLossPct;
  }
  if (settings.maxDrawdownPct !== undefined) {
    payload.max_drawdown_pct = settings.maxDrawdownPct;
  }
  if (settings.maxOpenPositions !== undefined) {
    payload.max_open_positions = settings.maxOpenPositions;
  }
  if (settings.maxDailyTrades !== undefined) {
    payload.max_daily_trades = settings.maxDailyTrades;
  }
  if (settings.tradeCooldownSeconds !== undefined) {
    payload.trade_cooldown_seconds = settings.tradeCooldownSeconds;
  }
  // NOTE: defaultStopLoss and defaultTakeProfit are stored in broker-specific units
  // (pips/points/percent) as they cannot be converted to absolute prices without
  // an entry price. Backend should handle conversion when these defaults are used
  // with a signal that has an entry price. Backend conversion is not yet implemented.
  if (settings.defaultStopLoss !== undefined) {
    payload.default_stop_loss = settings.defaultStopLoss;
  }
  if (settings.defaultTakeProfit !== undefined) {
    payload.default_take_profit = settings.defaultTakeProfit;
  }
  if (settings.groupId !== undefined) {
    payload.group_id = settings.groupId;
  }
  if (settings.isSignalEnabled !== undefined) {
    payload.is_signal_enabled = settings.isSignalEnabled;
  }
  if (settings.signalPriority !== undefined) {
    payload.signal_priority = settings.signalPriority;
  }

  const response = await fetch(`/api/accounts/${accountId}/settings`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await buildApiError(response, 'Failed to update account settings');
  }

  const data = await response.json();

  return mapAccountSettingsResponse(data);
}

// ============================================================================
// Account Groups API
// ============================================================================

/**
 * Get all account groups for the authenticated user
 */
export async function getAccountGroups(): Promise<AccountGroup[]> {
  const response = await fetch('/api/account-groups');

  if (!response.ok) {
    throw new Error(`Failed to fetch account groups: ${response.statusText}`);
  }

  const data = await response.json();

  // Transform API response to frontend format
  return data.map((group: Record<string, unknown>) => ({
    id: group.id,
    name: group.name,
    description: group.description,
    color: group.color,
    icon: group.icon,
    accountCount: group.account_count,
    isActive: group.is_active,
    createdAt: group.created_at,
    updatedAt: group.updated_at,
  }));
}

/**
 * Create a new account group
 */
export async function createAccountGroup(
  data: CreateAccountGroupRequest
): Promise<AccountGroup> {
  const response = await fetch('/api/account-groups', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create account group: ${response.statusText}`);
  }

  // Refetch the group to get full details
  const result = await response.json();
  const groupResponse = await fetch(`/api/account-groups/${result.group_id}`);

  if (!groupResponse.ok) {
    throw new Error(`Failed to fetch created group: ${groupResponse.statusText}`);
  }

  const group = await groupResponse.json();
  return {
    id: group.id,
    name: group.name,
    description: group.description,
    color: group.color,
    icon: group.icon,
    accountCount: group.account_count,
    isActive: group.is_active,
    createdAt: group.created_at,
    updatedAt: group.updated_at,
  };
}

/**
 * Update an existing account group
 */
export async function updateAccountGroup(
  groupId: number,
  data: UpdateAccountGroupRequest
): Promise<AccountGroup> {
  // Transform to API format
  const payload: Record<string, unknown> = {};
  if (data.name !== undefined) payload.name = data.name;
  if (data.description !== undefined) payload.description = data.description;
  if (data.color !== undefined) payload.color = data.color;
  if (data.icon !== undefined) payload.icon = data.icon;
  if (data.isActive !== undefined) payload.is_active = data.isActive;

  const response = await fetch(`/api/account-groups/${groupId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to update account group: ${response.statusText}`);
  }

  // Refetch to get updated details
  const groupResponse = await fetch(`/api/account-groups/${groupId}`);

  if (!groupResponse.ok) {
    throw new Error(`Failed to fetch updated group: ${groupResponse.statusText}`);
  }

  const group = await groupResponse.json();
  return {
    id: group.id,
    name: group.name,
    description: group.description,
    color: group.color,
    icon: group.icon,
    accountCount: group.account_count,
    isActive: group.is_active,
    createdAt: group.created_at,
    updatedAt: group.updated_at,
  };
}

/**
 * Delete an account group
 */
export async function deleteAccountGroup(groupId: number): Promise<void> {
  const response = await fetch(`/api/account-groups/${groupId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete account group: ${response.statusText}`);
  }
}

/**
 * Add an account to a group
 */
export async function addAccountToGroup(
  groupId: number,
  accountId: number
): Promise<void> {
  const response = await fetch(`/api/account-groups/${groupId}/accounts/${accountId}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to add account to group: ${response.statusText}`);
  }
}

/**
 * Remove an account from a group
 */
export async function removeAccountFromGroup(
  groupId: number,
  accountId: number
): Promise<void> {
  const response = await fetch(`/api/account-groups/${groupId}/accounts/${accountId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to remove account from group: ${response.statusText}`);
  }
}
