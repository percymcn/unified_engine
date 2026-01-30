/**
 * TradingView Widget Error Filter
 *
 * Filters known harmless CORS errors from TradingView's embed widget.
 * These errors come from inside the iframe (tradingview-widget.com) trying
 * to fetch resources that are CORS-restricted. The chart still works.
 *
 * Known harmless errors:
 * - s3.tradingview.com/conversions_en.json - Unit conversion labels
 * - scanner-backend.tradingview.com/...ytm-metrics-plan.json - Metrics config
 * - telemetry.tradingview.com/widget/report - Analytics/tracking
 * - Non-passive event listeners - Performance warning
 * - requestAnimationFrame timing - Performance warning
 */

// Patterns for errors we want to suppress
const TRADINGVIEW_ERROR_PATTERNS = [
  // CORS errors from TradingView domains
  /tradingview\.com.*CORS/i,
  /tradingview-widget\.com.*blocked/i,
  /s3\.tradingview\.com.*conversions/i,
  /scanner-backend\.tradingview\.com/i,
  /telemetry\.tradingview\.com/i,

  // Specific error messages
  /Failed to fetch.*tradingview/i,
  /net::ERR_FAILED.*tradingview/i,

  // Performance warnings from TradingView widget
  /Added non-passive event listener/i,
  /requestAnimationFrame.*violated.*budget/i,
  /Forced reflow while executing JavaScript/i,

  // TradingView prefetch failures
  /prefetch resource.*tradingview/i,
];

// Store original console methods
let originalConsoleError: typeof console.error | null = null;
let originalConsoleWarn: typeof console.warn | null = null;
let isFilterActive = false;

/**
 * Check if a message should be filtered (suppressed)
 */
function shouldFilterMessage(args: any[]): boolean {
  const message = args
    .map(arg => {
      if (typeof arg === 'string') return arg;
      if (arg instanceof Error) return arg.message + ' ' + arg.stack;
      try {
        return JSON.stringify(arg);
      } catch {
        return String(arg);
      }
    })
    .join(' ');

  return TRADINGVIEW_ERROR_PATTERNS.some(pattern => pattern.test(message));
}

/**
 * Install the TradingView error filter
 * Suppresses known harmless CORS/performance errors from TradingView widgets
 */
export function installTradingViewErrorFilter(): void {
  if (typeof window === 'undefined' || isFilterActive) return;

  originalConsoleError = console.error;
  originalConsoleWarn = console.warn;

  console.error = (...args: any[]) => {
    if (!shouldFilterMessage(args)) {
      originalConsoleError?.apply(console, args);
    }
    // Optionally log to debug that we filtered something
    // originalConsoleError?.apply(console, ['[TradingView filter suppressed error]']);
  };

  console.warn = (...args: any[]) => {
    if (!shouldFilterMessage(args)) {
      originalConsoleWarn?.apply(console, args);
    }
  };

  isFilterActive = true;
}

/**
 * Uninstall the TradingView error filter
 * Restores original console methods
 */
export function uninstallTradingViewErrorFilter(): void {
  if (typeof window === 'undefined' || !isFilterActive) return;

  if (originalConsoleError) {
    console.error = originalConsoleError;
    originalConsoleError = null;
  }

  if (originalConsoleWarn) {
    console.warn = originalConsoleWarn;
    originalConsoleWarn = null;
  }

  isFilterActive = false;
}

/**
 * React hook to install/uninstall the error filter when a component mounts/unmounts
 */
export function useTradingViewErrorFilter(): void {
  if (typeof window === 'undefined') return;

  // Install on mount, uninstall on unmount handled by component lifecycle
  if (!isFilterActive) {
    installTradingViewErrorFilter();
  }
}

/**
 * Check if the error filter is currently active
 */
export function isErrorFilterActive(): boolean {
  return isFilterActive;
}

/**
 * Diagnostic function to check TradingView widget health
 * Run this in DevTools console to verify what's failing
 */
export async function diagnoseTradingViewWidget(): Promise<{
  chartRendered: boolean;
  knownIssues: string[];
  recommendations: string[];
}> {
  const result = {
    chartRendered: false,
    knownIssues: [] as string[],
    recommendations: [] as string[],
  };

  // Check if widget container exists
  const widgetContainer = document.querySelector('.tradingview-widget-container');
  const widgetIframe = document.querySelector('iframe[src*="tradingview"]');

  if (widgetContainer && widgetIframe) {
    result.chartRendered = true;
  } else {
    result.chartRendered = false;
    result.knownIssues.push('TradingView widget container or iframe not found');
    result.recommendations.push('Ensure the widget script has loaded properly');
  }

  // Check CSP headers (can't directly check, but we can note it)
  result.recommendations.push(
    'Verify CSP allows: frame-src https://*.tradingview.com https://*.tradingview-widget.com'
  );

  // Note about CORS
  result.knownIssues.push(
    'CORS errors from tradingview-widget.com are expected and harmless - these are internal to the widget iframe'
  );

  return result;
}
