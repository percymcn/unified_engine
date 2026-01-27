/**
 * Symbol Aliases API Client
 *
 * Frontend API functions for symbol alias management.
 * Communicates with /api/v1/symbol-aliases backend endpoints.
 */

import {
  SymbolAlias,
  SymbolAliasGroup,
  CreateSymbolAliasRequest,
  UpdateSymbolAliasRequest,
} from '@/types/symbol-alias';

/**
 * API error response type.
 */
interface ApiError {
  detail: string;
}

/**
 * Get all symbol aliases for the current user, grouped by broker.
 *
 * @returns Symbol aliases organized by broker type
 * @throws Error if request fails
 */
export async function getSymbolAliases(): Promise<SymbolAliasGroup[]> {
  const response = await fetch('/api/symbol-aliases', {
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch symbol aliases' }));
    throw new Error((error as ApiError).detail || `Failed to fetch symbol aliases: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get symbol aliases for a specific broker.
 *
 * @param brokerType - The broker type (tradelocker, tradovate, mt4, etc.)
 * @returns List of symbol aliases for the broker
 * @throws Error if request fails
 */
export async function getSymbolAliasesByBroker(brokerType: string): Promise<SymbolAlias[]> {
  const response = await fetch(`/api/symbol-aliases/${brokerType}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch symbol aliases' }));
    throw new Error((error as ApiError).detail || `Failed to fetch symbol aliases: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new symbol alias.
 *
 * @param data - The alias data to create
 * @returns The created symbol alias
 * @throws Error if request fails (including duplicate conflicts)
 */
export async function createSymbolAlias(data: CreateSymbolAliasRequest): Promise<SymbolAlias> {
  const response = await fetch('/api/symbol-aliases', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create symbol alias' }));
    throw new Error((error as ApiError).detail || `Failed to create symbol alias: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an existing symbol alias.
 *
 * @param id - The alias ID to update
 * @param data - The updated alias data
 * @returns The updated symbol alias
 * @throws Error if request fails or alias not found
 */
export async function updateSymbolAlias(id: number, data: UpdateSymbolAliasRequest): Promise<SymbolAlias> {
  const response = await fetch(`/api/symbol-aliases/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update symbol alias' }));
    throw new Error((error as ApiError).detail || `Failed to update symbol alias: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a symbol alias.
 *
 * @param id - The alias ID to delete
 * @throws Error if request fails or alias not found
 */
export async function deleteSymbolAlias(id: number): Promise<void> {
  const response = await fetch(`/api/symbol-aliases/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete symbol alias' }));
    throw new Error((error as ApiError).detail || `Failed to delete symbol alias: ${response.statusText}`);
  }
}
