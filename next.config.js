/** @type {import('next').NextConfig} */

const nextConfig: import('next').NextConfig = {
  // CORS Configuration
  allowedDevOrigins: [
    'http://localhost:3000',
    'http://localhost:3456', 
    'http://localhost:8765',
  ],

  // Environment Configuration
  env: {
    NEXT_PUBLIC_FRONTEND_URL: process.env.NEXT_PUBLIC_FRONTEND_URL,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
    NEXT_PUBLIC_WEBHOOK_BASE_URL: process.env.NEXT_PUBLIC_WEBHOOK_BASE_URL,
  },

  // Performance Optimizations
  experimental: {
    optimizePackageImports: true,
  },
  
  // Security Headers
  async headers() {
    const headers = new Headers();
    
    // Security headers
    headers.set('X-DNS-Prefetch-Control', 'off');
    headers.set('X-Frame-Options', 'DENY');
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    
    // Add CORS for dev
    if (process.env.NODE_ENV !== 'production') {
      headers.set('Access-Control-Allow-Origin', '*');
      headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
      headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    }
    
    return headers;
  },

  // Webpack Configuration
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        fs: false,
      };
    }
    return config;
  },
};

export default nextConfig;