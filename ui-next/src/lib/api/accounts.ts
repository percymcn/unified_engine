import { Account, AccountCreate, AccountBalance, BrokerType } from '@/types/account';

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
 * Get all accounts for the authenticated user
 */
export async function getAccounts(): Promise<Account[]> {
  const response = await fetch('/api/accounts');

  if (!response.ok) {
    throw new Error(`Failed to fetch accounts: ${response.statusText}`);
  }

  return response.json();
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
