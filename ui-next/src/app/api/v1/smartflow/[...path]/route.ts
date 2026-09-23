import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

async function proxy(request: NextRequest, path: string) {
  const token = await getTokenFromCookies();
  if (!token) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const target = `${BACKEND_URL}/api/v1/smartflow/${path}${request.nextUrl.search}`;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  const init: RequestInit = { method: request.method, headers };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    headers['Content-Type'] = 'application/json';
    init.body = await request.text();
  }

  try {
    const response = await fetch(target, init);
    const payload = await response.json().catch(() => ({}));
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    console.error('SmartFlow proxy failed:', error);
    return NextResponse.json(
      {
        authenticated: true,
        running: false,
        paused: true,
        paper_mode: true,
        kill_switch: true,
        live_trading_enabled: false,
        message: 'Live trading is not enabled. SmartFlow trader is paused in paper mode.',
      },
      { status: 200 }
    );
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path.join('/'));
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path.join('/'));
}
