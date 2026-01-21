import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/accounts
 * BFF pattern: Proxy accounts list request to backend
 * Uses auth_token cookie for authorization
 */
export async function GET() {
  try {
    // Extract token from httpOnly cookie
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Fetch accounts from backend
    const response = await fetch(`${BACKEND_URL}/api/v1/accounts/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const accounts = await response.json();

    return NextResponse.json(accounts);
  } catch (error) {
    console.error('Error fetching accounts:', error);
    return NextResponse.json(
      { error: 'Failed to fetch accounts' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/accounts
 * BFF pattern: Proxy account creation to backend
 * Expects JSON body with account creation data
 *
 * Supports both credential-based and OAuth-based account creation:
 * - Standard: { account_id, broker, account_type, api_key, api_secret, ... }
 * - OAuth: { account_id, broker, account_type, oauth_tokens: { access_token, refresh_token, expires_in, environment } }
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

    // Build account data, preserving oauth_tokens if provided
    const accountData = {
      account_id: body.account_id,
      broker: body.broker,
      account_type: body.account_type,
      currency: body.currency,
      leverage: body.leverage,
      // Credential-based fields
      ...(body.api_key && { api_key: body.api_key }),
      ...(body.api_secret && { api_secret: body.api_secret }),
      ...(body.login && { login: body.login }),
      ...(body.password && { password: body.password }),
      ...(body.server && { server: body.server }),
      // OAuth tokens for Tradovate
      ...(body.oauth_tokens && { oauth_tokens: body.oauth_tokens }),
      // Additional broker config
      ...(body.broker_config && { broker_config: body.broker_config }),
    };

    // Create account in backend
    const response = await fetch(`${BACKEND_URL}/api/v1/accounts/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(accountData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || 'Failed to create account' },
        { status: response.status }
      );
    }

    const account = await response.json();

    return NextResponse.json(account);
  } catch (error) {
    console.error('Error creating account:', error);
    return NextResponse.json(
      { error: 'Failed to create account' },
      { status: 500 }
    );
  }
}
