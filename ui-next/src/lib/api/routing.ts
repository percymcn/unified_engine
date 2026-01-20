import { WebhookConfig, WebhookConfigCreate, WebhookConfigUpdate } from '@/types/routing';

/**
 * Get all webhook configurations for the authenticated user
 */
export async function getWebhookConfigs(): Promise<WebhookConfig[]> {
  const response = await fetch('/api/webhook-configs');

  if (!response.ok) {
    throw new Error(`Failed to fetch webhook configs: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new webhook configuration
 */
export async function createWebhookConfig(data: WebhookConfigCreate): Promise<WebhookConfig> {
  const response = await fetch('/api/webhook-configs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create webhook config: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an existing webhook configuration
 */
export async function updateWebhookConfig(
  id: number,
  data: WebhookConfigUpdate
): Promise<WebhookConfig> {
  const response = await fetch(`/api/webhook-configs/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update webhook config: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a webhook configuration
 */
export async function deleteWebhookConfig(id: number): Promise<void> {
  const response = await fetch(`/api/webhook-configs/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete webhook config: ${response.statusText}`);
  }
}

/**
 * Regenerate webhook key for a configuration
 */
export async function regenerateWebhookKey(id: number): Promise<WebhookConfig> {
  const response = await fetch(`/api/webhook-configs/${id}/generate-key`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to regenerate webhook key: ${response.statusText}`);
  }

  return response.json();
}
