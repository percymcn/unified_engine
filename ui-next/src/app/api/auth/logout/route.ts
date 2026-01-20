import { NextResponse } from 'next/server';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

interface LogoutResponse {
  success: boolean;
  message: string;
}

/**
 * POST /api/auth/logout
 * Clears the auth cookie to log out the user
 */
export async function POST(): Promise<NextResponse<LogoutResponse>> {
  const response = NextResponse.json(
    { success: true, message: 'Logged out successfully' },
    { status: 200 }
  );

  // Clear the auth cookie by setting it to empty with immediate expiry
  response.cookies.set(AUTH_COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });

  return response;
}
