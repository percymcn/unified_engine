import { HealthStatus } from '@/types/broker';

/**
 * Fetch broker health status from backend
 * Proxies through BFF to backend /health endpoint
 */
export async function getBrokerHealth(): Promise<HealthStatus> {
  const res = await fetch('/api/brokers/health', {
    method: 'GET',
    credentials: 'include',
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch broker health: ${res.status}`);
  }

  return res.json();
}
