import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

interface RegisterSuccessResponse {
  success: true;
  message: string;
  user: {
    id: number;
    email: string;
    username: string;
  };
}

interface RegisterErrorResponse {
  success: false;
  error: string;
}

type RegisterResponse = RegisterSuccessResponse | RegisterErrorResponse;

/**
 * POST /api/auth/register
 * BFF proxy for user registration - accepts JSON, proxies to backend
 */
export async function POST(request: NextRequest): Promise<NextResponse<RegisterResponse>> {
  try {
    // Parse JSON body
    const body: RegisterRequest = await request.json();
    const { email, username, password, full_name } = body;

    // Validate required fields
    if (!email || !username || !password) {
      return NextResponse.json<RegisterErrorResponse>(
        { success: false as const, error: 'Email, username, and password are required' },
        { status: 400 }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json<RegisterErrorResponse>(
        { success: false as const, error: 'Invalid email format' },
        { status: 400 }
      );
    }

    // Validate password length
    if (password.length < 8) {
      return NextResponse.json<RegisterErrorResponse>(
        { success: false as const, error: 'Password must be at least 8 characters' },
        { status: 400 }
      );
    }

    // Proxy request to backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        username,
        password,
        full_name: full_name || username,
        is_active: true,
      }),
    });

    // Handle backend errors
    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));

      // Extract error message - handle various formats from backend
      let errorMessage = 'Registration failed';
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

      return NextResponse.json<RegisterErrorResponse>(
        { success: false as const, error: errorMessage },
        { status: backendResponse.status }
      );
    }

    // Parse successful response
    const userData = await backendResponse.json();

    return NextResponse.json<RegisterSuccessResponse>(
      {
        success: true as const,
        message: 'Registration successful! Please log in.',
        user: {
          id: userData.id,
          email: userData.email,
          username: userData.username,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    // Handle network errors or unexpected issues
    console.error('Registration error:', error);

    if (error instanceof SyntaxError) {
      return NextResponse.json<RegisterErrorResponse>(
        { success: false as const, error: 'Invalid request body' },
        { status: 400 }
      );
    }

    return NextResponse.json<RegisterErrorResponse>(
      { success: false as const, error: 'Unable to connect to registration service' },
      { status: 503 }
    );
  }
}
