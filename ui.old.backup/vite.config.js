import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get backend port from environment or default to 8000
const getBackendPort = () => {
  // Check VITE_API_BASE_URL first
  if (process.env.VITE_API_BASE_URL) {
    try {
      const url = new URL(process.env.VITE_API_BASE_URL)
      return url.port || '8000'
    } catch {
      // Invalid URL, use default
    }
  }
  // Check BACKEND_PORT
  if (process.env.BACKEND_PORT) {
    return process.env.BACKEND_PORT
  }
  // Default
  return '8000'
}

const backendPort = getBackendPort()
const backendUrl = `http://localhost:${backendPort}`
const backendWsUrl = `ws://localhost:${backendPort}`

export default defineConfig({
  plugins: [react()],
  server: {
    // Port will be set by find-port.js script or vite will auto-increment
    port: parseInt(process.env.PORT || process.env.VITE_PORT || '3000'),
    strictPort: false, // Allow vite to find next available port if specified port is taken
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
      },
      '/ws': {
        target: backendWsUrl,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})