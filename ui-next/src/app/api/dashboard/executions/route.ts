import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export interface ExecutionAccountInfo {
  broker: string;
  account_id: number | null;
}

export interface ExecutionItem {
  id: number;
  signal_id: string | null;
  account: ExecutionAccountInfo;
  symbol: string;
  action: string;
  volume: number;
  price: number | null;
  status: string;
  execution_time_ms: number | null;
  created_at: string;
}

export interface ExecutionsResponse {
  executions: ExecutionItem[];
  total: number;
}

/**
 * GET /api/dashboard/executions
 * BFF pattern: Fetch recent trade executions for the dashboard
 */
export async function GET(request: Request) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get limit parameter from query string, default to 10
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '10';

    const response = await fetch(
      `${BACKEND_URL}/api/v1/dashboard/executions?limit=${limit}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      console.error('Failed to fetch executions:', response.status);
      // Return empty response on error (graceful degradation)
      return NextResponse.json({ executions: [], total: 0 });
    }

    const data: ExecutionsResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching executions:', error);
    // Return empty response on error (graceful degradation)
    return NextResponse.json({ executions: [], total: 0 });
  }
}
