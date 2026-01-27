import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';
import { fetchWithTimeout } from '@/lib/fetch-utils';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export async function POST() {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/admin/system/restart`, {
      method: 'POST',
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
    console.error('Restart backend error:', error);
    return NextResponse.json({ error: 'Failed to restart backend' }, { status: 500 });
  }
}
