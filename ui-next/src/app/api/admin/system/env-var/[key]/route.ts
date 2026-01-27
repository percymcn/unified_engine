import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';
import { fetchWithTimeout } from '@/lib/fetch-utils';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

// PUT - Update an env var (stores in database)
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ key: string }> }
) {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { key } = await params;
    const body = await request.json();

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/admin/system/env-var/${encodeURIComponent(key)}`, {
      method: 'PUT',
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
    console.error('Update env var error:', error);
    return NextResponse.json({ error: 'Failed to update environment variable' }, { status: 500 });
  }
}
