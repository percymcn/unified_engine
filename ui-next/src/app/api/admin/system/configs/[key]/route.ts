import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';
import { fetchWithTimeout, isTimeoutError } from '@/lib/fetch-utils';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

// PUT - Update a config by key
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

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/admin/system/configs/${encodeURIComponent(key)}`, {
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
    console.error('Update config error:', error);
    return NextResponse.json({ error: 'Failed to update config' }, { status: 500 });
  }
}

// DELETE - Delete a config by key
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ key: string }> }
) {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { key } = await params;

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/admin/system/configs/${encodeURIComponent(key)}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
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
    console.error('Delete config error:', error);
    return NextResponse.json({ error: 'Failed to delete config' }, { status: 500 });
  }
}
