import { NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

// Default test symbols - crypto available 24/7
const DEFAULT_SYMBOLS = ['XAUUSD', 'BTCUSD', 'ETHUSD', 'EURUSD'];

/**
 * POST /api/webhooks/test
 * BFF route to send a test signal through the webhook system.
 * Opens a test position, waits briefly, then closes it.
 * Accepts optional body: { symbol?: string, close_delay_ms?: number }
 */
export async function POST(request: Request) {
  try {
    const token = await getTokenFromCookies();

    // Parse optional body for symbol selection
    let testSymbol = 'XAUUSD';
    let closeDelay = 3000; // 3 second delay before close
    try {
      const body = await request.json().catch(() => ({}));
      if (body.symbol && typeof body.symbol === 'string') {
        testSymbol = body.symbol.toUpperCase();
      }
      if (body.close_delay_ms && typeof body.close_delay_ms === 'number') {
        closeDelay = Math.min(Math.max(body.close_delay_ms, 1000), 10000); // 1-10s
      }
    } catch {
      // Use defaults if no body
    }

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
    const accountsResponse = await fetch(`${BACKEND_URL}/api/v1/accounts/`, {
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
        // Prioritize: 1) signal-enabled accounts, 2) any account with webhook_key
        const signalEnabledAccount = accounts.find(
          (account) => account.webhook_key && account.is_signal_enabled
        );
        const accountWithKey = signalEnabledAccount || accounts.find((account) => account.webhook_key);
        accountWebhookKey = accountWithKey?.webhook_key;
      }
    }

    const profileWebhookKey = profile?.primary_webhook_key;
    // Prefer profile webhook key (uses WebhookConfig routing with default_account_id)
    // Fall back to account-specific key if profile key not available
    const executeWebhookKey = profileWebhookKey || accountWebhookKey;

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
      symbol: testSymbol,
      quantity: 0.01, // Minimum size for test
      comment: 'Test signal from dashboard (will auto-close)',
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
    const openSignalId = data.signal_id || data.webhook_id;

    // If open was successful, wait then close the position
    if (data.success !== false && openSignalId) {
      // Wait before closing (give broker time to execute)
      await new Promise(resolve => setTimeout(resolve, closeDelay));

      // Send close signal
      const closePayload = {
        webhook_key: executeWebhookKey,
        action: 'close',
        symbol: testSymbol,
        comment: 'Auto-close test position',
        strategy_id: 'dashboard-test',
        timestamp: new Date().toISOString(),
      };

      try {
        const closeResponse = await fetch(`${BACKEND_URL}/api/v1/webhook/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(closePayload),
        });

        const closeData = await closeResponse.json().catch(() => ({}));
        const closeSuccess = closeResponse.ok && closeData.success !== false;

        return NextResponse.json({
          success: true,
          message: closeSuccess
            ? 'Test complete: Position opened and closed successfully'
            : 'Test partial: Position opened but close may have failed',
          signal_id: openSignalId,
          close_signal_id: closeData.signal_id || closeData.webhook_id,
          symbol: testSymbol,
          phases: {
            open: { success: true, signal_id: openSignalId },
            close: { success: closeSuccess, signal_id: closeData.signal_id },
          },
        });
      } catch (closeError) {
        console.warn('Close signal failed:', closeError);
        return NextResponse.json({
          success: true,
          message: 'Test partial: Position opened but close signal failed',
          signal_id: openSignalId,
          symbol: testSymbol,
          warning: 'Position may still be open - check manually',
        });
      }
    }

    return NextResponse.json({
      success: data.success ?? true,
      message: data.message || 'Test signal received (single action)',
      signal_id: openSignalId,
      symbol: testSymbol,
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
