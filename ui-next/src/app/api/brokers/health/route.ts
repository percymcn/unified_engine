import { NextResponse } from 'next/server';

/**
 * GET /api/brokers/health
 * Proxies health check request to backend /health endpoint
 * No authentication required for health checks
 */
export async function GET() {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

    const res = await fetch(`${backendUrl}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Don't cache health checks
      cache: 'no-store',
    });

    const data = await res.json();

    // Return with same status code as backend
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('Health check error:', error);
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
        redis: 'disconnected',
        brokers: {},
      },
      { status: 503 }
    );
  }
}
