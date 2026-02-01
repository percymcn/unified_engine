/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  eslint: {
    // Disable ESLint during production builds for faster deployment
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Don't fail build on TS errors (already caught in dev)
    ignoreBuildErrors: true,
  },
  // Generate unique build ID to bust cache
  generateBuildId: async () => {
    return `build-${Date.now()}`;
  },
  // Headers to control caching properly
  async headers() {
    // Content Security Policy for TradingView widgets
    // Note: CORS errors inside TradingView's iframe are on their side - this CSP just ensures
    // we don't block the widget from loading
    const cspHeader = [
      "default-src 'self'",
      // Scripts: self + TradingView + inline (needed for widget init)
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.tradingview.com https://s3.tradingview.com https://static.cloudflareinsights.com",
      // Styles: self + inline + TradingView
      "style-src 'self' 'unsafe-inline' https://*.tradingview.com",
      // Images: self + data + blob + TradingView
      "img-src 'self' data: blob: https://*.tradingview.com https://s3.tradingview.com",
      // Fonts: self + data + TradingView
      "font-src 'self' data: https://*.tradingview.com",
      // Connect: self + backend + TradingView endpoints
      "connect-src 'self' http://localhost:* ws://localhost:* https://*.tradingview.com https://s3.tradingview.com wss://*.tradingview.com https://*.mytradeflow.app wss://*.mytradeflow.app",
      // Frames: TradingView widget iframes
      "frame-src 'self' https://*.tradingview.com https://*.tradingview-widget.com",
      // Workers: self + blob (for TradingView)
      "worker-src 'self' blob:",
      // Child frames (for nested iframes)
      "child-src 'self' blob: https://*.tradingview.com https://*.tradingview-widget.com",
    ].join('; ');

    return [
      // Static assets with hashes can be cached forever
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      // HTML pages and API routes - never cache, add CSP
      {
        source: '/((?!_next/static).*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate, max-age=0',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          },
          {
            key: 'Expires',
            value: '0',
          },
          {
            key: 'CDN-Cache-Control',
            value: 'no-store',
          },
          {
            key: 'Cloudflare-CDN-Cache-Control',
            value: 'no-store',
          },
          // Content Security Policy - allows TradingView widgets
          {
            key: 'Content-Security-Policy',
            value: cspHeader,
          },
        ],
      },
      // AI Suite page specifically - ensure TradingView widgets work
      {
        source: '/ai-suite',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspHeader,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
