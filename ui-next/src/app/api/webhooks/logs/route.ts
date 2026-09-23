import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { AUTH_COOKIE_NAME, getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * Read the session JWT the rest of the dashboard BFF uses.
 * Primary cookie is `auth-token`. `auth_token` is accepted as a legacy alias.
 */
async function readSessionToken(): Promise<string | undefined> {
  const primary = await getTokenFromCookies();
  if (primary) {
    return primary;
  }
  const cookieStore = await cookies();
  return cookieStore.get('auth_token')?.value || cookieStore.get(AUTH_COOKIE_NAME)?.value;
}

/**
 * GET /api/webhooks/logs
 * BFF: proxy to GET /api/v1/webhooks/logs with the session JWT.
 * The v1 route returns 401 without a Bearer token. The browser only has the
 * httpOnly session cookie, so this route attaches it.
 */
export async function GET(request: NextRequest) {
  try {
    const token = await readSessionToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const skipRaw = searchParams.get('skip') || '0';
    const limitRaw = searchParams.get('limit') || '100';
    const skip = Number.isFinite(Number(skipRaw)) ? String(Math.max(0, Number(skipRaw))) : '0';
    const limitNum = Number(limitRaw);
    const limit = Number.isFinite(limitNum) ? String(Math.min(500, Math.max(1, limitNum))) : '100';

    const response = await fetch(
      `${BACKEND_URL}/api/v1/webhooks/logs?skip=${encodeURIComponent(skip)}&limit=${encodeURIComponent(limit)}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
        cache: 'no-store',
      }
    );

    const text = await response.text();
    let body: unknown = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = { error: text };
      }
    }

    if (!response.ok) {
      const errorBody =
        body && typeof body === 'object'
          ? body
          : { error: 'Failed to fetch webhook logs' };
      return NextResponse.json(errorBody, { status: response.status });
    }

    return NextResponse.json(body ?? []);
  } catch (error) {
    console.error('Error fetching webhook logs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch webhook logs' },
      { status: 502 }
    );
  }
}
