import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';
import { fetchWithTimeout, isTimeoutError } from '@/lib/fetch-utils';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

export async function GET() {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/admin/system/pipeline-status`, {
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
    console.error('Pipeline status error:', error);
    if (isTimeoutError(error)) {
      return NextResponse.json({ error: 'Request timed out' }, { status: 504 });
    }
    return NextResponse.json({ error: 'Failed to fetch pipeline status' }, { status: 500 });
  }
}
