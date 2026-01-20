import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * POST /api/webhook-configs/[id]/generate-key
 * BFF pattern: Proxy webhook key regeneration to backend
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/webhook-configs/${params.id}/generate-key`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to regenerate webhook key' },
        { status: response.status }
      );
    }

    const config = await response.json();

    return NextResponse.json(config);
  } catch (error) {
    console.error('Error regenerating webhook key:', error);
    return NextResponse.json(
      { error: 'Failed to regenerate webhook key' },
      { status: 500 }
    );
  }
}
