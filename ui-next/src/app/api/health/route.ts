import { NextResponse } from 'next/server'

/**
 * Health check endpoint for Docker health checks
 * GET /api/health returns { status: 'ok', timestamp: ... }
 * No authentication required - used by container orchestration
 */
export async function GET() {
  return NextResponse.json({
    status: 'ok',
    service: 'unified-ui-next',
    timestamp: new Date().toISOString(),
  })
}
