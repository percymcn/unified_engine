import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * POST /api/accounts/connect/metaapi
 * BFF pattern: Connect an existing MT4/MT5 account via MetaApi Cloud (BYOA)
 *
 * Security: Password is sent to backend which sends it to MetaApi.
 * Password is NEVER stored in our database.
 */
export async function POST(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();

    // Validate required fields
    if (!body.platform || !['mt4', 'mt5'].includes(body.platform.toLowerCase())) {
      return NextResponse.json(
        { error: 'Platform must be "mt4" or "mt5"' },
        { status: 400 }
      );
    }

    if (!body.login || !body.password || !body.server) {
      return NextResponse.json(
        { error: 'Login, password, and server are required' },
        { status: 400 }
      );
    }

    // Call backend MetaApi connect endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/accounts/connect/metaapi`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        platform: body.platform.toLowerCase(),
        login: body.login,
        password: body.password,
        server: body.server,
        nickname: body.nickname,
        account_type: body.account_type || 'funded',
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const detail = (errorData as { detail?: string }).detail;

      return NextResponse.json(
        {
          error: detail || 'Failed to connect MetaApi account',
          details: errorData,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error connecting MetaApi account:', error);

    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        { error: 'Cannot reach backend service. Check your network connection.' },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: 'An unexpected error occurred while connecting the account.' },
      { status: 500 }
    );
  }
}
