import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export interface EquityDataPoint {
  date: string;
  equity: number;
  balance: number;
}

export interface EquityResponse {
  data: EquityDataPoint[];
  current_equity: number;
  current_balance: number;
  change_percent: number | null;
}

/**
 * GET /api/dashboard/equity
 * BFF pattern: Fetch equity history for the dashboard chart
 */
export async function GET(request: Request) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get days parameter from query string, default to 30
    const { searchParams } = new URL(request.url);
    const days = searchParams.get('days') || '30';

    const response = await fetch(
      `${BACKEND_URL}/api/v1/dashboard/equity?days=${days}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      console.error('Failed to fetch equity history:', response.status);
      // Return empty response on error (graceful degradation)
      return NextResponse.json({
        data: [],
        current_equity: 0,
        current_balance: 0,
        change_percent: null,
      });
    }

    const data: EquityResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching equity history:', error);
    // Return empty response on error (graceful degradation)
    return NextResponse.json({
      data: [],
      current_equity: 0,
      current_balance: 0,
      change_percent: null,
    });
  }
}
