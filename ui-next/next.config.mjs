/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  // Creates minimal production bundle without node_modules
  output: 'standalone',

  // Disable telemetry in production builds
  telemetry: false,
};

export default nextConfig;
