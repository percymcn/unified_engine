import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';
const TIMEOUT_MS = 5000; // 5 second timeout to avoid Cloudflare 524

/**
 * GET /api/account-groups
 * Get all account groups for the current user
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const includeInactive = searchParams.get('include_inactive') === 'true';

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const response = await fetch(
      `${BACKEND_URL}/api/v1/account-groups/?include_inactive=${includeInactive}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        signal: controller.signal,
      }
    );
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch account groups' },
        { status: response.status }
      );
    }

    const groups = await response.json();
    return NextResponse.json(groups);
  } catch (error) {
    console.error('Error fetching account groups:', error);
    // Return empty groups on error (graceful degradation)
    return NextResponse.json([], { status: 200 });
  }
}

/**
 * POST /api/account-groups
 * Create a new account group
 */
export async function POST(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/v1/account-groups/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to create account group' },
        { status: response.status }
      );
    }

    const result = await response.json();
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    console.error('Error creating account group:', error);
    return NextResponse.json(
      { error: 'Failed to create account group' },
      { status: 500 }
    );
  }
}
