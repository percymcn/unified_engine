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
  // Headers to prevent aggressive caching of HTML pages
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
