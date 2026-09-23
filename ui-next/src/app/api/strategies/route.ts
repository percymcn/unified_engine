import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

function normalizeStrategies(payload: unknown): { strategies: unknown[]; total: number } {
  if (Array.isArray(payload)) {
    return { strategies: payload, total: payload.length };
  }
  if (payload && typeof payload === 'object' && Array.isArray((payload as { strategies?: unknown[] }).strategies)) {
    const strategies = (payload as { strategies: unknown[] }).strategies;
    const total = (payload as { total?: number }).total;
    return { strategies, total: typeof total === 'number' ? total : strategies.length };
  }
  return { strategies: [], total: 0 };
}

export async function GET() {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/api/strategies/`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 401) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    if (!response.ok) {
      return NextResponse.json({ strategies: [], total: 0 });
    }

    return NextResponse.json(normalizeStrategies(await response.json()));
  } catch (error) {
    console.error('Error fetching strategies:', error);
    return NextResponse.json({ strategies: [], total: 0 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const response = await fetch(`${BACKEND_URL}/api/strategies/`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      return NextResponse.json(
        { error: payload.detail || 'Failed to create strategy' },
        { status: response.status }
      );
    }
    return NextResponse.json(payload, { status: 201 });
  } catch (error) {
    console.error('Error creating strategy:', error);
    return NextResponse.json({ error: 'Failed to create strategy' }, { status: 500 });
  }
}
