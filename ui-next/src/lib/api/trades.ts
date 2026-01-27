import { Trade, TradeFilters } from '@/types/trade';

export async function getTrades(filters?: TradeFilters): Promise<Trade[]> {
  const params = new URLSearchParams();

  if (filters?.dateFrom) {
    params.append('date_from', filters.dateFrom);
  }
  if (filters?.dateTo) {
    params.append('date_to', filters.dateTo);
  }
  if (filters?.broker && filters.broker !== 'all') {
    params.append('broker', filters.broker);
  }
  if (filters?.status && filters.status !== 'all') {
    params.append('status', filters.status);
  }

  const queryString = params.toString();
  const url = `/api/trades${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch trades: ${response.statusText}`);
  }

  return response.json();
}
