import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const REQUEST_TIMEOUT = 30000; // 30 second timeout

/**
 * Fetch with timeout to prevent hanging requests
 */
async function fetchWithTimeout(url: string, options: RequestInit, timeout = REQUEST_TIMEOUT): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * GET /api/accounts/[id]/settings
 * BFF pattern: Proxy account settings request to backend
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/accounts/${id}/settings`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch account settings' },
        { status: response.status }
      );
    }

    const settings = await response.json();

    return NextResponse.json(settings);
  } catch (error) {
    console.error('Error fetching account settings:', error);
    // Handle timeout specifically
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timed out. The server is taking too long to respond.' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to fetch account settings' },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/accounts/[id]/settings
 * BFF pattern: Proxy account settings update to backend
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();

    const response = await fetchWithTimeout(`${BACKEND_URL}/api/v1/accounts/${id}/settings`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to update account settings' },
        { status: response.status }
      );
    }

    const settings = await response.json();

    return NextResponse.json(settings);
  } catch (error) {
    console.error('Error updating account settings:', error);
    // Handle timeout specifically
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timed out. The server is taking too long to respond. Your changes may not have been saved.' },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: 'Failed to update account settings' },
      { status: 500 }
    );
  }
}
