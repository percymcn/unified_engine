import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * Test connection response from backend
 */
interface TestConnectionResponse {
  success: boolean;
  status: 'connected' | 'failed' | 'timeout';
  message: string;
  details?: Record<string, unknown>;
}

/**
 * POST /api/accounts/test-connection
 * BFF pattern: Proxy connection test to backend
 *
 * Tests broker credentials without creating an account.
 * Returns detailed success/failure information.
 */
export async function POST(request: NextRequest) {
  try {
    // Extract token from httpOnly cookie
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Parse request body
    const body = await request.json();

    if (!body.broker) {
      return NextResponse.json(
        { error: 'Broker type is required' },
        { status: 400 }
      );
    }

    if (!body.credentials || typeof body.credentials !== 'object') {
      return NextResponse.json(
        { error: 'Credentials are required' },
        { status: 400 }
      );
    }

    // Call backend test-connection endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/accounts/test-connection`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        broker: body.broker,
        credentials: body.credentials,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));

      // Map specific backend errors to user-friendly messages
      const errorMessage = mapBackendError(response.status, errorData);

      return NextResponse.json(
        {
          success: false,
          status: 'failed',
          message: errorMessage,
          details: errorData,
        },
        { status: response.status >= 500 ? 502 : response.status }
      );
    }

    const data: TestConnectionResponse = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error testing connection:', error);

    // Handle network errors specifically
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        {
          success: false,
          status: 'failed',
          message: 'Cannot reach broker service. Check your network connection.',
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        status: 'failed',
        message: 'An unexpected error occurred while testing the connection.',
      },
      { status: 500 }
    );
  }
}

/**
 * Map backend errors to user-friendly messages
 */
function mapBackendError(status: number, errorData: Record<string, unknown>): string {
  const detail = errorData.detail as string | undefined;

  // Handle common error patterns
  if (status === 400) {
    if (detail?.includes('Invalid broker')) {
      return 'Unsupported broker type. Please select a valid broker.';
    }
    if (detail?.includes('credentials')) {
      return 'Missing or invalid credentials. Please check your input.';
    }
    return detail || 'Invalid request. Please check your credentials.';
  }

  if (status === 401) {
    return 'Authentication failed. Your API key or password may be incorrect.';
  }

  if (status === 403) {
    return 'Access denied. Your account may not have API access enabled.';
  }

  if (status === 404) {
    return 'Broker server not found. Check the server address.';
  }

  if (status === 408 || detail?.includes('timeout')) {
    return 'Connection timed out. The broker server may be slow or unavailable.';
  }

  if (status >= 500) {
    return 'Broker service error. Please try again later.';
  }

  return detail || 'Connection test failed. Please verify your credentials.';
}
