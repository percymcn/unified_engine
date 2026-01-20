import { NextRequest, NextResponse } from 'next/server';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

interface LoginRequest {
  username: string;
  password: string;
}

interface BackendAuthResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

interface LoginSuccessResponse {
  success: true;
  message: string;
}

interface LoginErrorResponse {
  success: false;
  error: string;
}

type LoginResponse = LoginSuccessResponse | LoginErrorResponse;

/**
 * POST /api/auth/login
 * BFF proxy for authentication - accepts JSON, proxies to backend
 */
export async function POST(request: NextRequest): Promise<NextResponse<LoginResponse>> {
  try {
    // Parse JSON body
    const body: LoginRequest = await request.json();
    const { username, password } = body;

    // Validate required fields
    if (!username || !password) {
      return NextResponse.json(
        { success: false, error: 'Username and password are required' },
        { status: 400 }
      );
    }

    // Backend expects form data or query params
    // Using URLSearchParams for form-urlencoded format
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    // Proxy request to backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    // Handle backend errors
    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      const errorMessage = errorData.detail || errorData.message || 'Authentication failed';

      return NextResponse.json(
        { success: false, error: errorMessage },
        { status: backendResponse.status }
      );
    }

    // Parse successful response
    const authData: BackendAuthResponse = await backendResponse.json();

    // Create response with success message
    const response = NextResponse.json(
      { success: true, message: 'Login successful' },
      { status: 200 }
    );

    // Calculate cookie max age (default 24 hours if not specified)
    const maxAge = authData.expires_in || 86400;

    // Set httpOnly cookie with JWT token
    response.cookies.set(AUTH_COOKIE_NAME, authData.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge,
    });

    return response;

  } catch (error) {
    // Handle network errors or unexpected issues
    console.error('Login error:', error);

    if (error instanceof SyntaxError) {
      return NextResponse.json(
        { success: false, error: 'Invalid request body' },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { success: false, error: 'Unable to connect to authentication service' },
      { status: 503 }
    );
  }
}
