import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * POST /api/webhooks/test
 * BFF route to send a test signal through the webhook system.
 * Uses the backend's test webhook endpoint with a sample payload.
 */
export async function POST() {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const profileResponse = await fetch(`${BACKEND_URL}/api/v1/users/me/profile`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!profileResponse.ok) {
      const error = await profileResponse.json().catch(() => ({ detail: 'Failed to load profile' }));
      return NextResponse.json(
        { success: false, message: error.detail || 'Failed to load profile' },
        { status: 200 }
      );
    }

    const profile = await profileResponse.json();

    const accountsResponse = await fetch(`${BACKEND_URL}/api/v1/accounts`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    let accountWebhookKey: string | undefined;
    let hasAccounts = false;
    if (accountsResponse.ok) {
      const accountsPayload = await accountsResponse.json();
      const accounts = Array.isArray(accountsPayload)
        ? accountsPayload
        : accountsPayload.accounts || [];
      if (Array.isArray(accounts)) {
        hasAccounts = accounts.length > 0;
        const accountWithKey = accounts.find((account) => account.webhook_key);
        accountWebhookKey = accountWithKey?.webhook_key;
      }
    }

    const profileWebhookKey = profile?.primary_webhook_key;
    const executeWebhookKey = accountWebhookKey || profileWebhookKey;

    if (!executeWebhookKey && !profileWebhookKey) {
      return NextResponse.json(
        { success: false, message: 'No webhook key found. Generate one first.' },
        { status: 200 }
      );
    }

    if (!hasAccounts) {
      return NextResponse.json(
        { success: false, message: 'Add an account to test your webhook.' },
        { status: 200 }
      );
    }

    // Create a test payload for the unified webhook execute endpoint
    const testPayload = {
      webhook_key: executeWebhookKey,
      action: 'buy',
      symbol: 'XAUUSD',
      quantity: 0.1,
      comment: 'Test signal from dashboard',
      strategy_id: 'dashboard-test',
      timestamp: new Date().toISOString(),
    };

    // Send to backend execute endpoint (note: v1 prefix required)
    const response = await fetch(`${BACKEND_URL}/api/v1/webhook/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(testPayload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Test webhook failed:', response.status, errorText);
      const normalizedError = errorText.toLowerCase();
      const invalidKey = normalizedError.includes('invalid webhook_key');

      if (invalidKey && profileWebhookKey) {
        const routingResponse = await fetch(
          `${BACKEND_URL}/api/v1/webhooks/signal/${profileWebhookKey}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              action: 'buy',
              symbol: 'XAUUSD',
              quantity: 0.1,
              comment: 'Test signal from dashboard',
              strategy_id: 'dashboard-test',
              timestamp: new Date().toISOString(),
            }),
          }
        );

        if (routingResponse.ok) {
          const routingData = await routingResponse.json();
          if (routingData.success !== false) {
            return NextResponse.json({
              success: routingData.success ?? true,
              message: routingData.message || 'Test signal sent successfully',
              signal_id: routingData.webhook_id || routingData.signal_id,
              payload: testPayload,
            });
          }
          if (routingData.error) {
            return NextResponse.json(
              { success: false, message: routingData.error },
              { status: 200 }
            );
          }
        }
      }

      const friendlyMessage = invalidKey
        ? 'Invalid webhook key. Generate a new key and try again.'
        : `Backend returned ${response.status}`;
      return NextResponse.json(
        {
          success: false,
          message: friendlyMessage,
        },
        { status: 200 } // Return 200 to frontend so it can handle the error gracefully
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: data.success ?? true,
      message: data.message || 'Test signal received successfully',
      signal_id: data.signal_id || data.webhook_id,
      payload: testPayload,
    });
  } catch (error) {
    console.error('Error sending test webhook:', error);
    return NextResponse.json(
      {
        success: false,
        message: error instanceof Error ? error.message : 'Failed to send test webhook',
      },
      { status: 200 } // Return 200 for graceful frontend handling
    );
  }
}
