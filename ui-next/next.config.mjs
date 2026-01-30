/** @type {import('next').NextConfig} */
const nextConfig = {
  // Removed standalone output - use standard production mode
  // For Docker deployment, uncomment: output: 'standalone',
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
      // HTML pages and API routes - never cache
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
        ],
      },
    ];
  },
};

export default nextConfig;
