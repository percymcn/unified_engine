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

    // Create a test payload similar to TradingView format
    const testPayload = {
      ticker: 'TEST',
      action: 'buy',
      quantity: 1,
      price: 100.00,
      comment: 'Test signal from dashboard',
      strategy_id: 'dashboard-test',
      strategy_name: 'Dashboard Test Signal',
      test: true,
      timestamp: new Date().toISOString(),
    };

    // Send to backend test webhook endpoint
    const response = await fetch(`${BACKEND_URL}/api/webhooks/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(testPayload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Test webhook failed:', response.status, errorText);
      return NextResponse.json(
        {
          success: false,
          message: `Backend returned ${response.status}`,
        },
        { status: 200 } // Return 200 to frontend so it can handle the error gracefully
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: data.success ?? true,
      message: data.message || 'Test webhook received successfully',
      signal_id: data.webhook_id || data.signal_id,
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
