import { Signal } from '@/types/signal';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export async function getSignals(token: string): Promise<Signal[]> {
  const response = await fetch(`${BACKEND_URL}/api/v1/signals`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch signals');
  }

  return response.json();
}
