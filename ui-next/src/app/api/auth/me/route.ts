import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

interface User {
  id: string | number;
  username: string;
  email?: string;
  [key: string]: unknown; // Allow additional user fields from backend
}

interface MeSuccessResponse {
  success: true;
  user: User;
}

interface MeErrorResponse {
  success: false;
  error: string;
}

type MeResponse = MeSuccessResponse | MeErrorResponse;

/**
 * GET /api/auth/me
 * Returns current user info by validating token with backend
 */
export async function GET(): Promise<NextResponse<MeResponse>> {
  try {
    // Get token from cookies
    const cookieStore = await cookies();
    const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;

    if (!token) {
      return NextResponse.json(
        { success: false, error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Verify token with backend /api/auth/me endpoint
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    // Handle authentication failure
    if (backendResponse.status === 401) {
      return NextResponse.json(
        { success: false, error: 'Session expired' },
        { status: 401 }
      );
    }

    if (!backendResponse.ok) {
      return NextResponse.json(
        { success: false, error: 'Failed to fetch user info' },
        { status: backendResponse.status }
      );
    }

    // Return user data
    const user: User = await backendResponse.json();

    return NextResponse.json(
      { success: true, user },
      { status: 200 }
    );

  } catch (error) {
    console.error('Get user error:', error);

    return NextResponse.json(
      { success: false, error: 'Unable to connect to authentication service' },
      { status: 503 }
    );
  }
}
