import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/webhooks/logs/:webhookId
 * BFF proxy for one authenticated webhook log.
 */
export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ webhookId: string }> }
) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { webhookId } = await context.params;
    const response = await fetch(
      `${BACKEND_URL}/api/v1/webhooks/logs/${encodeURIComponent(webhookId)}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (response.status === 401) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Webhook log not found' },
        { status: response.status }
      );
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error('Error fetching webhook log:', error);
    return NextResponse.json({ error: 'Failed to fetch webhook log' }, { status: 500 });
  }
}
