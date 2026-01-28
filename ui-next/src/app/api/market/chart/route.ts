import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

/**
 * GET /api/market/chart
 * Proxy chart data request to backend market data API
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol');
    const interval = searchParams.get('interval') || '5';
    const days = searchParams.get('days') || '1';
    const accountId = searchParams.get('account_id');

    if (!symbol) {
      return NextResponse.json(
        { error: 'Symbol is required' },
        { status: 400 }
      );
    }

    // If no account_id provided, get user's first ProjectX account
    let effectiveAccountId = accountId;
    if (!effectiveAccountId) {
      const accountsRes = await fetch(`${BACKEND_URL}/api/v1/accounts/`, {
        headers: { 'Authorization': `Bearer ${token}` },
        cache: 'no-store',
      });

      if (accountsRes.ok) {
        const accountsData = await accountsRes.json();
        const accounts = Array.isArray(accountsData) ? accountsData : (accountsData?.accounts || []);
        const projectxAccount = accounts.find(
          (a: { broker: string; is_active: boolean }) =>
            (a.broker === 'projectx' || a.broker === 'PROJECTX' || a.broker === 'topstep') && a.is_active
        );
        effectiveAccountId = projectxAccount?.id?.toString();
      }
    }

    if (!effectiveAccountId) {
      // Return mock data if no ProjectX account available
      return NextResponse.json({
        symbol,
        interval: `${interval}m`,
        bars: generateMockBars(parseInt(interval)),
        indicators: generateMockIndicators(),
        contract_info: null,
        mock: true,
      });
    }

    // Fetch from backend
    const response = await fetch(
      `${BACKEND_URL}/api/v1/market/chart/${symbol}?account_id=${effectiveAccountId}&interval=${interval}&days=${days}&include_indicators=true`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        cache: 'no-store',
      }
    );

    if (!response.ok) {
      // Parse error to provide meaningful feedback
      let errorMessage = 'Market data unavailable';
      try {
        const errorData = await response.json();
        if (errorData.detail?.includes('credentials')) {
          errorMessage = 'ProjectX credentials not configured';
        }
      } catch {}

      // Return mock data with error context
      return NextResponse.json({
        symbol,
        interval: `${interval}m`,
        bars: generateMockBars(parseInt(interval)),
        indicators: generateMockIndicators(),
        contract_info: null,
        mock: true,
        error: errorMessage,
      });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    // Return mock data silently on error
    return NextResponse.json({
      symbol: 'MNQ',
      interval: '5m',
      bars: generateMockBars(5),
      indicators: generateMockIndicators(),
      contract_info: null,
      mock: true,
    });
  }
}

/**
 * Generate mock OHLCV bars for demo/fallback
 */
function generateMockBars(interval: number) {
  const bars = [];
  const now = new Date();
  let price = 21500 + Math.random() * 100;

  for (let i = 50; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * interval * 60 * 1000);
    const change = (Math.random() - 0.5) * 20;
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * 10;
    const low = Math.min(open, close) - Math.random() * 10;
    const volume = Math.floor(Math.random() * 1000) + 100;

    bars.push({
      timestamp: timestamp.toISOString(),
      open: Math.round(open * 100) / 100,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close: Math.round(close * 100) / 100,
      volume,
    });

    price = close;
  }

  return bars;
}

/**
 * Generate mock indicators for demo/fallback
 */
function generateMockIndicators() {
  return {
    rsi: Math.round((30 + Math.random() * 40) * 100) / 100,
    macd: {
      macd: Math.round((Math.random() - 0.5) * 20 * 100) / 100,
      signal: Math.round((Math.random() - 0.5) * 15 * 100) / 100,
      histogram: Math.round((Math.random() - 0.5) * 10 * 100) / 100,
    },
    ema_20: 21500 + Math.random() * 50,
    ema_50: 21480 + Math.random() * 50,
    atr: Math.round((10 + Math.random() * 20) * 100) / 100,
    adx: Math.round((20 + Math.random() * 30) * 100) / 100,
    stoch_k: Math.round((20 + Math.random() * 60) * 100) / 100,
    stoch_d: Math.round((25 + Math.random() * 50) * 100) / 100,
  };
}
