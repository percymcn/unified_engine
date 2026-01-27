import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';
import { fetchWithTimeout, isTimeoutError } from '@/lib/fetch-utils';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

// GET - List all system configs
export async function GET() {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/admin/system/configs`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (response.status === 403) {
      return NextResponse.json({ error: 'Access denied' }, { status: 403 });
    }

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('List configs error:', error);
    if (isTimeoutError(error)) {
      return NextResponse.json({ error: 'Request timed out' }, { status: 504 });
    }
    return NextResponse.json({ error: 'Failed to fetch configs' }, { status: 500 });
  }
}

// POST - Create a new config
export async function POST(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/admin/system/configs`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (response.status === 403) {
      return NextResponse.json({ error: 'Access denied' }, { status: 403 });
    }

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Create config error:', error);
    return NextResponse.json({ error: 'Failed to create config' }, { status: 500 });
  }
}
