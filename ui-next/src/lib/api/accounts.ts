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
  PropPhase,
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

// Backend now returns camelCase format
interface ApiAccountSettingsData {
  accountId: number;
  positionSizing: {
    mode: string;
    fixedLotSize: number | null;
    percentOfBalance: number | null;
    percentOfEquity: number | null;
    riskPercentPerTrade: number | null;
  };
  riskLimits: {
    maxPositionSize: number | null;
    maxDailyLoss: number | null;
    maxDailyLossPct: number | null;
    maxDrawdownPct: number | null;
    maxOpenPositions: number | null;
    maxDailyTrades: number | null;
    tradeCooldownSeconds: number | null;
    defaultStopLoss?: number | null;
    defaultTakeProfit?: number | null;
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
  propRules?: {
    isEnabled: boolean;
    provider: string | null;
    phase: string;
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
  account?: Account;
}

const mapAccountSettingsResponse = (data: ApiAccountSettingsData): AccountSettingsResponse => ({
  accountId: data.accountId,
  positionSizing: {
    mode: data.positionSizing.mode as PositionSizingMode,
    fixedLotSize: data.positionSizing.fixedLotSize ?? 0,
    percentOfBalance: data.positionSizing.percentOfBalance ?? 0,
    percentOfEquity: data.positionSizing.percentOfEquity ?? 0,
    riskPercentPerTrade: data.positionSizing.riskPercentPerTrade ?? 0,
  },
  riskLimits: {
    maxPositionSize: data.riskLimits.maxPositionSize,
    maxDailyLoss: data.riskLimits.maxDailyLoss,
    maxDailyLossPct: data.riskLimits.maxDailyLossPct,
    maxDrawdownPct: data.riskLimits.maxDrawdownPct,
    maxOpenPositions: data.riskLimits.maxOpenPositions,
    maxDailyTrades: data.riskLimits.maxDailyTrades,
    tradeCooldownSeconds: data.riskLimits.tradeCooldownSeconds,
    defaultStopLoss: data.riskLimits.defaultStopLoss ?? null,
    defaultTakeProfit: data.riskLimits.defaultTakeProfit ?? null,
  },
  grouping: {
    groupId: data.grouping.groupId,
    groupName: data.grouping.groupName,
    groupColor: data.grouping.groupColor,
  },
  routing: {
    isSignalEnabled: data.routing.isSignalEnabled,
    signalPriority: data.routing.signalPriority,
  },
  propRules: data.propRules ? {
    isEnabled: data.propRules.isEnabled,
    provider: data.propRules.provider,
    phase: (data.propRules.phase || 'none') as PropPhase,
    profitTargetPct: data.propRules.profitTargetPct,
    profitTargetAmount: data.propRules.profitTargetAmount,
    maxDailyLossPct: data.propRules.maxDailyLossPct,
    maxDailyLossAmount: data.propRules.maxDailyLossAmount,
    maxDrawdownPct: data.propRules.maxDrawdownPct,
    maxDrawdownAmount: data.propRules.maxDrawdownAmount,
    trailingDrawdown: data.propRules.trailingDrawdown,
    challengeStartDate: data.propRules.challengeStartDate,
    challengeEndDate: data.propRules.challengeEndDate,
  } : {
    isEnabled: false,
    provider: null,
    phase: 'none' as PropPhase,
    profitTargetPct: null,
    profitTargetAmount: null,
    maxDailyLossPct: null,
    maxDailyLossAmount: null,
    maxDrawdownPct: null,
    maxDrawdownAmount: null,
    trailingDrawdown: false,
    challengeStartDate: null,
    challengeEndDate: null,
  },
  account: data.account,
});

/**
 * Get all accounts for the authenticated user
 */
export async function getAccounts(): Promise<Account[]> {
  const response = await fetch('/api/accounts', {
    credentials: 'include',
  });

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
    credentials: 'include',
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
    credentials: 'include',
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
    credentials: 'include',
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
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.error || errorData.detail || `Sync failed (${response.status})`;
    throw new Error(message);
  }

  return response.json();
}

/**
 * Get account balance from broker
 */
export async function getAccountBalance(id: number): Promise<AccountBalance> {
  const response = await fetch(`/api/accounts/${id}/balance`, {
    credentials: 'include',
  });

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
    credentials: 'include',
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
    credentials: 'include',
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
    credentials: 'include',
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
  const response = await fetch(`/api/accounts/${accountId}/settings`, {
    credentials: 'include',
  });

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
  // Prop rules
  if (settings.propRulesEnabled !== undefined) {
    payload.prop_rules_enabled = settings.propRulesEnabled;
  }
  if (settings.propProvider !== undefined) {
    payload.prop_provider = settings.propProvider;
  }
  if (settings.propPhase !== undefined) {
    payload.prop_phase = settings.propPhase;
  }
  if (settings.propProfitTargetPct !== undefined) {
    payload.prop_profit_target_pct = settings.propProfitTargetPct;
  }
  if (settings.propProfitTargetAmount !== undefined) {
    payload.prop_profit_target_amount = settings.propProfitTargetAmount;
  }
  if (settings.propMaxDailyLossPct !== undefined) {
    payload.prop_max_daily_loss_pct = settings.propMaxDailyLossPct;
  }
  if (settings.propMaxDailyLossAmount !== undefined) {
    payload.prop_max_daily_loss_amount = settings.propMaxDailyLossAmount;
  }
  if (settings.propMaxDrawdownPct !== undefined) {
    payload.prop_max_drawdown_pct = settings.propMaxDrawdownPct;
  }
  if (settings.propMaxDrawdownAmount !== undefined) {
    payload.prop_max_drawdown_amount = settings.propMaxDrawdownAmount;
  }
  if (settings.propTrailingDrawdown !== undefined) {
    payload.prop_trailing_drawdown = settings.propTrailingDrawdown;
  }
  if (settings.propChallengeStartDate !== undefined) {
    payload.prop_challenge_start_date = settings.propChallengeStartDate;
  }
  if (settings.propChallengeEndDate !== undefined) {
    payload.prop_challenge_end_date = settings.propChallengeEndDate;
  }

  const response = await fetch(`/api/accounts/${accountId}/settings`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
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
  const response = await fetch('/api/account-groups', {
    credentials: 'include',
  });

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
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create account group: ${response.statusText}`);
  }

  // Refetch the group to get full details
  const result = await response.json();
  const groupResponse = await fetch(`/api/account-groups/${result.group_id}`, {
    credentials: 'include',
  });

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
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to update account group: ${response.statusText}`);
  }

  // Refetch to get updated details
  const groupResponse = await fetch(`/api/account-groups/${groupId}`, {
    credentials: 'include',
  });

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
    credentials: 'include',
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
    credentials: 'include',
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
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to remove account from group: ${response.statusText}`);
  }
}

// ============================================================================
// MetaApi BYOA (Bring Your Own Account) API
// ============================================================================

/**
 * Request to connect an existing MT4/MT5 account via MetaApi
 */
export interface ConnectMetaApiRequest {
  platform: 'mt4' | 'mt5';
  login: string;
  password: string;
  server: string;
  nickname?: string;
  account_type?: 'demo' | 'live' | 'funded' | 'evaluation';
}

/**
 * Response from MetaApi account connection
 */
export interface ConnectMetaApiResponse {
  account_id: number;
  metaapi_account_id: string;
  status: string;
  platform: string;
  login: string;
  server: string;
  webhook_key: string;
  message: string;
  account_info?: {
    balance?: number;
    equity?: number;
    margin?: number;
    free_margin?: number;
    leverage?: number;
    currency?: string;
  };
}

/**
 * Response from MetaApi status check
 */
export interface MetaApiStatusResponse {
  account_id: number;
  metaapi_account_id: string | null;
  status: 'creating' | 'deploying' | 'connecting' | 'syncing' | 'ready' | 'disconnected' | 'failed' | 'not_provisioned' | 'service_unavailable';
  state?: string;
  connection_status?: string;
  platform: string;
  server?: string;
  last_error?: string;
  last_sync?: string;
}

/**
 * Response from MetaApi reconnect
 */
export interface MetaApiReconnectResponse {
  account_id: number;
  metaapi_account_id: string;
  status: string;
  deployed: boolean;
  message: string;
}

/**
 * Connect an existing MT4/MT5 account via MetaApi Cloud (BYOA).
 *
 * Security: Password is sent to MetaApi only, NEVER stored in our database.
 *
 * @param data Connection request with platform, login, password, server
 * @returns Connected account with metaapi_account_id and webhook_key
 */
export async function connectMetaApiAccount(
  data: ConnectMetaApiRequest
): Promise<ConnectMetaApiResponse> {
  const response = await fetch('/api/accounts/connect/metaapi', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw await buildApiError(response, 'Failed to connect MetaApi account');
  }

  return response.json();
}

/**
 * Get deployment and connection status for a MetaApi-connected account.
 *
 * @param accountId Our database account ID
 * @returns Current status including state, connection_status, last_error
 */
export async function getMetaApiStatus(
  accountId: number
): Promise<MetaApiStatusResponse> {
  const response = await fetch(`/api/accounts/${accountId}/metaapi/status`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw await buildApiError(response, 'Failed to get MetaApi status');
  }

  return response.json();
}

/**
 * Redeploy a MetaApi account that has disconnected.
 *
 * @param accountId Our database account ID
 * @returns Reconnection result
 */
export async function reconnectMetaApiAccount(
  accountId: number
): Promise<MetaApiReconnectResponse> {
  const response = await fetch(`/api/accounts/${accountId}/metaapi/reconnect`, {
    method: 'POST',
    credentials: 'include',
  });

  if (!response.ok) {
    throw await buildApiError(response, 'Failed to reconnect MetaApi account');
  }

  return response.json();
}
