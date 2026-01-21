import { NextRequest, NextResponse } from 'next/server';
import { AUTH_COOKIE_NAME } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

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
      return NextResponse.json<LoginErrorResponse>(
        { success: false as const, error: 'Username and password are required' },
        { status: 400 }
      );
    }

    // Backend expects query parameters
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    // Proxy request to backend with query params
    const backendResponse = await fetch(`${BACKEND_URL}/api/v1/auth/login?${params.toString()}`, {
      method: 'POST',
    });

    // Handle backend errors
    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));

      // Extract error message - handle various formats from backend
      let errorMessage = 'Authentication failed';
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
        // FastAPI validation errors come as array of objects with 'msg' field
        errorMessage = errorData.detail.map((e: { msg?: string }) => e.msg || 'Validation error').join(', ');
      } else if (errorData.error && typeof errorData.error === 'string') {
        errorMessage = errorData.error;
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }

      return NextResponse.json<LoginErrorResponse>(
        { success: false as const, error: errorMessage },
        { status: backendResponse.status }
      );
    }

    // Parse successful response
    const authData: BackendAuthResponse = await backendResponse.json();

    // Create response with success message
    const response = NextResponse.json<LoginSuccessResponse>(
      { success: true as const, message: 'Login successful' },
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
      return NextResponse.json<LoginErrorResponse>(
        { success: false as const, error: 'Invalid request body' },
        { status: 400 }
      );
    }

    return NextResponse.json<LoginErrorResponse>(
      { success: false as const, error: 'Unable to connect to authentication service' },
      { status: 503 }
    );
  }
}
