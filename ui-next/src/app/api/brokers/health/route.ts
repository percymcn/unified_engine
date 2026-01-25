import { NextResponse } from 'next/server';

/**
 * GET /api/brokers/health
 * Proxies health check request to backend /brokers/health endpoint
 * Returns broker connection status for all brokers
 */
export async function GET() {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8765';

    const res = await fetch(`${backendUrl}/api/v1/brokers/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Don't cache health checks
      cache: 'no-store',
    });

    const data = await res.json();

    // Transform backend response to match UI expectations
    const brokers: Record<string, boolean> = {};
    if (data.brokers) {
      Object.entries(data.brokers).forEach(([broker, status]: [string, any]) => {
        brokers[broker] = status.connected || false;
      });
    }

    return NextResponse.json({
      status: data.status || 'unhealthy',
      timestamp: data.timestamp,
      redis: 'connected', // Assume connected if backend responds
      brokers: brokers,
    }, { status: res.status });
  } catch (error) {
    console.error('Health check error:', error);
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
        redis: 'disconnected',
        brokers: {
          mt4: false,
          mt5: false,
          tradelocker: false,
          tradovate: false,
          projectx: false,
        },
      },
      { status: 503 }
    );
  }
}
