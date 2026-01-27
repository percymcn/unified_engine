import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/market/symbols
 * Get all tradeable symbols - no auth required (public reference data)
 */
export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/market/symbols`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      // Return default symbols on error
      return NextResponse.json(getDefaultSymbols());
    }

    const symbols = await response.json();
    return NextResponse.json(symbols);
  } catch (error) {
    console.error('Error fetching symbols:', error);
    return NextResponse.json(getDefaultSymbols());
  }
}

/**
 * Default symbols for fallback
 */
function getDefaultSymbols() {
  return [
    { symbol: 'MNQ', name: 'Micro E-mini Nasdaq-100', tick_size: 0.25, tick_value: 0.5 },
    { symbol: 'MES', name: 'Micro E-mini S&P 500', tick_size: 0.25, tick_value: 1.25 },
    { symbol: 'MYM', name: 'Micro E-mini Dow', tick_size: 1.0, tick_value: 0.5 },
    { symbol: 'M2K', name: 'Micro E-mini Russell 2000', tick_size: 0.1, tick_value: 0.5 },
    { symbol: 'NQ', name: 'E-mini Nasdaq-100', tick_size: 0.25, tick_value: 5.0 },
    { symbol: 'ES', name: 'E-mini S&P 500', tick_size: 0.25, tick_value: 12.5 },
    { symbol: 'YM', name: 'E-mini Dow', tick_size: 1.0, tick_value: 5.0 },
    { symbol: 'RTY', name: 'E-mini Russell 2000', tick_size: 0.1, tick_value: 5.0 },
    { symbol: 'MCL', name: 'Micro Crude Oil', tick_size: 0.01, tick_value: 1.0 },
    { symbol: 'MGC', name: 'Micro Gold', tick_size: 0.1, tick_value: 1.0 },
    { symbol: 'CL', name: 'Crude Oil', tick_size: 0.01, tick_value: 10.0 },
    { symbol: 'GC', name: 'Gold', tick_size: 0.1, tick_value: 10.0 },
  ];
}
