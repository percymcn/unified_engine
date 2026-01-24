/**
 * Broker Credential Schemas
 *
 * Single source of truth for broker credential field mappings.
 * Maps UI field names to backend API field names and storage locations.
 *
 * Generated from backend code analysis - DO NOT MODIFY without updating backend.
 *
 * Note: Only includes brokers with confirmed backend executor/test connection support.
 * Other brokers (e.g., truforex) may exist in types but are not supported here.
 *
 * BACKEND CONTRACT API:
 * The canonical broker schemas are also available via API:
 *   GET /api/v1/brokers/contracts
 * See: docs/BROKER_CONTRACTS.md for documentation
 *
 * Future enhancement: This file could be replaced by fetching from the API,
 * but the schemas here are kept in sync with app/contracts/brokers.json.
 */

// Supported brokers only (with backend executors)
export type SupportedBrokerType = 'tradelocker' | 'tradovate' | 'projectx' | 'topstep' | 'mt4' | 'mt5';

// Accept any broker type (from account.ts) but only return schemas for supported ones
export type BrokerType = SupportedBrokerType | string;

/**
 * Credential field definition
 */
export interface CredentialField {
  /** UI field name (camelCase) */
  name: string;
  /** Backend API field name (snake_case) */
  backendName: string;
  /** Whether field is required */
  required: boolean;
  /** Field type */
  type: 'string' | 'number' | 'password' | 'select';
  /** Human-readable label */
  label: string;
  /** Help text/description */
  description?: string;
  /** Options for select fields */
  options?: Array<{ value: string; label: string }>;
  /** Where field is stored: 'trading_accounts' table or 'credentials' table */
  storageLocation: 'trading_accounts' | 'credentials';
  /** Storage column name in database */
  storageColumn: string;
}

/**
 * Broker credential schema
 */
export interface BrokerCredentialSchema {
  /** Broker type */
  broker: SupportedBrokerType;
  /** Display name */
  displayName: string;
  /** Required fields */
  requiredFields: CredentialField[];
  /** Optional fields */
  optionalFields: CredentialField[];
  /** Test connection endpoint */
  testConnectionEndpoint: string;
  /** Create account endpoint */
  createAccountEndpoint: string;
  /** Notes about authentication modes */
  notes?: string;
}

/**
 * TradeLocker Credential Schema
 * 
 * Supports two authentication modes:
 * 1. SDK mode (preferred): Uses username/password/server
 * 2. Brand API mode (fallback/required for some brokers): Uses API key
 * 
 * Note: Some brokers (e.g., GATESFX) require Brand API and don't support SDK mode.
 */
export const TRADELOCKER_SCHEMA: BrokerCredentialSchema = {
  broker: 'tradelocker',
  displayName: 'TradeLocker',
  requiredFields: [
    // SDK mode fields (required unless Brand API is required)
    {
      name: 'username',
      backendName: 'username',
      required: true,
      type: 'string',
      label: 'Email/Username',
      description: 'Your TradeLocker account email or username',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'password',
      backendName: 'password',
      required: true,
      type: 'password',
      label: 'Password',
      description: 'Your TradeLocker account password',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'server',
      backendName: 'server',
      required: true,
      type: 'string',
      label: 'Server',
      description: 'TradeLocker server name (e.g., "Demo Server", "Live Server", "GATESFX")',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
  ],
  optionalFields: [
    {
      name: 'environment',
      backendName: 'environment',
      required: false,
      type: 'string',
      label: 'Environment URL',
      description: 'TradeLocker environment URL (defaults to https://demo.tradelocker.com)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    // Brand API mode field
    {
      name: 'apiKey',
      backendName: 'api_key',
      required: false,
      type: 'password',
      label: 'API Key (Brand API Mode)',
      description: 'TradeLocker Brand API key. Required for brokers like GATESFX. Alternative to username/password.',
      storageLocation: 'trading_accounts',
      storageColumn: 'api_key',
    },
    {
      name: 'environment_url',
      backendName: 'environment_url',
      required: false,
      type: 'string',
      label: 'Environment URL (Brand API)',
      description: 'Environment URL for Brand API mode (e.g., https://live.tradelocker.com)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
  ],
  testConnectionEndpoint: '/api/v1/accounts/test-connection',
  createAccountEndpoint: '/api/v1/accounts/',
  notes: 'Provide either (username, password, server) for SDK mode or (api_key) for Brand API mode. Some brokers (e.g., GATESFX) require Brand API.',
};

/**
 * ProjectX/TopStep Credential Schema
 */
export const PROJECTX_SCHEMA: BrokerCredentialSchema = {
  broker: 'projectx',
  displayName: 'ProjectX / TopStep',
  requiredFields: [
    {
      name: 'username',
      backendName: 'username',
      required: true,
      type: 'string',
      label: 'Username',
      description: 'Your TopStep/ProjectX username',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'apiKey',
      backendName: 'api_key',
      required: true,
      type: 'password',
      label: 'API Key',
      description: 'Your TopStep/ProjectX API key',
      storageLocation: 'trading_accounts',
      storageColumn: 'api_key',
    },
  ],
  optionalFields: [],
  testConnectionEndpoint: '/api/v1/accounts/test-connection',
  createAccountEndpoint: '/api/v1/accounts/',
  notes: 'API key is stored encrypted in trading_accounts.api_key. JWT token stored in access_token after authentication.',
};

/**
 * TopStep Credential Schema (alias for ProjectX)
 */
export const TOPSTEP_SCHEMA: BrokerCredentialSchema = {
  ...PROJECTX_SCHEMA,
  broker: 'topstep',
  displayName: 'TopStep',
};

/**
 * Tradovate Credential Schema
 * 
 * Supports OAuth 2.0 (preferred) and password authentication modes.
 */
export const TRADOVATE_SCHEMA: BrokerCredentialSchema = {
  broker: 'tradovate',
  displayName: 'Tradovate',
  requiredFields: [
    {
      name: 'userId',
      backendName: 'user_id',
      required: true,
      type: 'string',
      label: 'User ID / Username',
      description: 'Your Tradovate user ID or username',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'password',
      backendName: 'password',
      required: true,
      type: 'password',
      label: 'Password',
      description: 'Your Tradovate password',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
  ],
  optionalFields: [
    {
      name: 'environment',
      backendName: 'environment',
      required: false,
      type: 'select',
      label: 'Environment',
      description: 'Tradovate environment',
      options: [
        { value: 'demo', label: 'Demo' },
        { value: 'live', label: 'Live' },
      ],
      storageLocation: 'trading_accounts',
      storageColumn: 'oauth_environment',
    },
    {
      name: 'appId',
      backendName: 'app_id',
      required: false,
      type: 'string',
      label: 'App ID',
      description: 'Tradovate application ID (optional)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'cid',
      backendName: 'cid',
      required: false,
      type: 'string',
      label: 'Client ID',
      description: 'Tradovate client ID (optional)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'sec',
      backendName: 'sec',
      required: false,
      type: 'password',
      label: 'Secret',
      description: 'Tradovate secret (optional)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
  ],
  testConnectionEndpoint: '/api/v1/accounts/test-connection',
  createAccountEndpoint: '/api/v1/accounts/',
  notes: 'OAuth authentication is recommended for production. Access tokens stored in trading_accounts.access_token and refresh_token.',
};

/**
 * MT4 Credential Schema
 * 
 * Supports two authentication modes:
 * 1. MetaAPI SDK mode (preferred): Uses MetaAPI token and account ID
 * 2. Manager API mode (fallback): Uses manager login/password
 */
export const MT4_SCHEMA: BrokerCredentialSchema = {
  broker: 'mt4',
  displayName: 'MetaTrader 4',
  requiredFields: [
    // MetaAPI mode fields
    {
      name: 'metaapiToken',
      backendName: 'metaapi_token',
      required: true,
      type: 'password',
      label: 'MetaAPI Token',
      description: 'Your MetaAPI cloud token',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'metaapiAccountId',
      backendName: 'metaapi_account_id',
      required: true,
      type: 'string',
      label: 'MetaAPI Account ID',
      description: 'Your MetaAPI account ID',
      storageLocation: 'trading_accounts',
      storageColumn: 'extra_metadata',
    },
  ],
  optionalFields: [
    // Manager API mode fields
    {
      name: 'managerLogin',
      backendName: 'manager_login',
      required: false,
      type: 'string',
      label: 'Manager Login (Manager API Mode)',
      description: 'MT4 Manager API login (alternative to MetaAPI)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'managerPassword',
      backendName: 'manager_password',
      required: false,
      type: 'password',
      label: 'Manager Password (Manager API Mode)',
      description: 'MT4 Manager API password (alternative to MetaAPI)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
  ],
  testConnectionEndpoint: '/api/v1/accounts/test-connection',
  createAccountEndpoint: '/api/v1/accounts/',
  notes: 'Provide either (metaapi_token, metaapi_account_id) for MetaAPI mode or (manager_login, manager_password) for Manager API mode.',
};

/**
 * MT5 Credential Schema
 * 
 * Supports two authentication modes:
 * 1. MetaAPI SDK mode (preferred): Uses MetaAPI token and account ID
 * 2. Manager API mode (fallback): Uses manager login/password
 */
export const MT5_SCHEMA: BrokerCredentialSchema = {
  broker: 'mt5',
  displayName: 'MetaTrader 5',
  requiredFields: [
    // MetaAPI mode fields
    {
      name: 'metaapiToken',
      backendName: 'metaapi_token',
      required: true,
      type: 'password',
      label: 'MetaAPI Token',
      description: 'Your MetaAPI cloud token',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'metaapiAccountId',
      backendName: 'metaapi_account_id',
      required: true,
      type: 'string',
      label: 'MetaAPI Account ID',
      description: 'Your MetaAPI account ID',
      storageLocation: 'trading_accounts',
      storageColumn: 'extra_metadata',
    },
  ],
  optionalFields: [
    // Manager API mode fields
    {
      name: 'managerLogin',
      backendName: 'manager_login',
      required: false,
      type: 'string',
      label: 'Manager Login (Manager API Mode)',
      description: 'MT5 Manager API login (alternative to MetaAPI)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
    {
      name: 'managerPassword',
      backendName: 'manager_password',
      required: false,
      type: 'password',
      label: 'Manager Password (Manager API Mode)',
      description: 'MT5 Manager API password (alternative to MetaAPI)',
      storageLocation: 'credentials',
      storageColumn: 'encrypted_data',
    },
  ],
  testConnectionEndpoint: '/api/v1/accounts/test-connection',
  createAccountEndpoint: '/api/v1/accounts/',
  notes: 'Provide either (metaapi_token, metaapi_account_id) for MetaAPI mode or (manager_login, manager_password) for Manager API mode.',
};

/**
 * All broker credential schemas
 * 
 * Only includes brokers with confirmed backend support:
 * - TradeLocker, Tradovate, ProjectX, TopStep, MT4, MT5
 */
export const BROKER_CREDENTIAL_SCHEMAS: Record<SupportedBrokerType, BrokerCredentialSchema> = {
  tradelocker: TRADELOCKER_SCHEMA,
  tradovate: TRADOVATE_SCHEMA,
  projectx: PROJECTX_SCHEMA,
  topstep: TOPSTEP_SCHEMA,
  mt4: MT4_SCHEMA,
  mt5: MT5_SCHEMA,
};

/**
 * Get credential schema for a broker
 * 
 * Returns null if broker is not supported (no backend executor/test connection)
 */
export function getBrokerCredentialSchema(broker: BrokerType): BrokerCredentialSchema | null {
  // Type guard: check if broker is in supported list
  if (broker in BROKER_CREDENTIAL_SCHEMAS) {
    return BROKER_CREDENTIAL_SCHEMAS[broker as SupportedBrokerType];
  }
  return null;
}

/**
 * Get all required fields for a broker
 * Returns empty array if broker is not supported
 */
export function getRequiredFields(broker: BrokerType): CredentialField[] {
  const schema = getBrokerCredentialSchema(broker);
  return schema?.requiredFields || [];
}

/**
 * Get all optional fields for a broker
 * Returns empty array if broker is not supported
 */
export function getOptionalFields(broker: BrokerType): CredentialField[] {
  const schema = getBrokerCredentialSchema(broker);
  return schema?.optionalFields || [];
}

/**
 * Get all fields (required + optional) for a broker
 * Returns empty array if broker is not supported
 */
export function getAllFields(broker: BrokerType): CredentialField[] {
  const schema = getBrokerCredentialSchema(broker);
  if (!schema) return [];
  return [...schema.requiredFields, ...schema.optionalFields];
}

/**
 * Map UI credential object to backend API format
 */
export function mapCredentialsToBackend(
  broker: BrokerType,
  credentials: Record<string, unknown>
): Record<string, unknown> {
  const allFields = getAllFields(broker);
  const mapped: Record<string, unknown> = {};

  for (const field of allFields) {
    const value = credentials[field.name];
    if (value !== undefined && value !== null && value !== '') {
      mapped[field.backendName] = value;
    }
  }

  return mapped;
}

/**
 * Map backend API credential object to UI format
 * Returns empty object if broker is not supported
 */
export function mapCredentialsFromBackend(
  broker: BrokerType,
  credentials: Record<string, unknown>
): Record<string, unknown> {
  const allFields = getAllFields(broker);
  if (allFields.length === 0) return {};
  
  const mapped: Record<string, unknown> = {};

  for (const field of allFields) {
    const value = credentials[field.backendName];
    if (value !== undefined && value !== null && value !== '') {
      mapped[field.name] = value;
    }
  }

  return mapped;
}
