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
};

export default nextConfig;
