/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  // Creates minimal production bundle without node_modules
  output: 'standalone',
};

export default nextConfig;
