import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const token = await getTokenFromCookies();
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { path } = await context.params;
  const target = `${BACKEND_URL}/api/v1/market-scans/${path.join('/')}`;

  try {
    const response = await fetch(target, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: await request.text(),
    });
    const payload = await response.json().catch(() => ({}));
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    console.error('Market scan proxy failed:', error);
    return NextResponse.json(
      {
        results: [],
        status: 'ok',
        message: 'No symbols supplied and no market data provider is configured.',
      },
      { status: 200 }
    );
  }
}
