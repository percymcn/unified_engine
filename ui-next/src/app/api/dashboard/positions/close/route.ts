import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const TIMEOUT_MS = 30000; // 30 second timeout for broker operations

interface ClosePositionRequest {
  position_id: string;
  account_id: number;
  volume?: number;
}

interface ClosePositionResponse {
  success: boolean;
  message?: string;
  position_id: string;
  pnl?: number;
}

/**
 * POST /api/dashboard/positions/close
 * BFF route to close a position on any connected broker
 */
export async function POST(request: Request) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body: ClosePositionRequest = await request.json();

    if (!body.position_id || !body.account_id) {
      return NextResponse.json(
        { success: false, message: 'Missing position_id or account_id' },
        { status: 400 }
      );
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const response = await fetch(`${BACKEND_URL}/api/v1/dashboard/positions/close`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const data: ClosePositionResponse = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { success: false, message: data.message || 'Failed to close position' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error closing position:', error);

    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { success: false, message: 'Request timed out - broker may be slow' },
        { status: 504 }
      );
    }

    return NextResponse.json(
      { success: false, message: 'Failed to close position' },
      { status: 500 }
    );
  }
}
