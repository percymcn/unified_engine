import { ApiKey, ApiKeyCreate, ApiKeyCreateResponse } from '@/types/api-key';

export async function getApiKeys(): Promise<ApiKey[]> {
  const response = await fetch('/api/api-keys', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to fetch API keys');
  }

  return response.json();
}

export async function createApiKey(data: ApiKeyCreate): Promise<ApiKeyCreateResponse> {
  const response = await fetch('/api/api-keys', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Failed to create API key');
  }

  return response.json();
}

export async function revokeApiKey(id: number): Promise<void> {
  const response = await fetch(`/api/api-keys/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to revoke API key');
  }
}

export async function getApiKey(id: number): Promise<ApiKey> {
  const response = await fetch(`/api/api-keys/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to fetch API key');
  }

  return response.json();
}
