#!/usr/bin/env node
/**
 * Frontend Server Launcher with Dynamic Port Finding
 * Finds a free port starting from 3000 and launches vite
 */
import { createServer } from 'net';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function findFreePort(startPort = 3000, maxAttempts = 100) {
  return new Promise((resolve, reject) => {
    let port = startPort;
    let attempts = 0;

    const tryPort = (currentPort) => {
      if (attempts >= maxAttempts) {
        reject(new Error(`Could not find a free port in range ${startPort}-${startPort + maxAttempts}`));
        return;
      }

      const server = createServer();
      
      server.listen(currentPort, () => {
        server.once('close', () => {
          resolve(currentPort);
        });
        server.close();
      });

      server.on('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          attempts++;
          tryPort(currentPort + 1);
        } else {
          reject(err);
        }
      });
    };

    tryPort(port);
  });
}

async function main() {
  // Get port from environment or find free port
  let port = process.env.PORT ? parseInt(process.env.PORT) : null;

  if (port) {
    // Check if specified port is available
    const server = createServer();
    try {
      await new Promise((resolve, reject) => {
        server.listen(port, () => {
          server.close(() => resolve());
        });
        server.on('error', (err) => {
          if (err.code === 'EADDRINUSE') {
            console.log(`⚠️  Port ${port} from environment is not available, finding free port...`);
            port = null;
            resolve();
          } else {
            reject(err);
          }
        });
      });
    } catch (err) {
      port = null;
    }
  }

  if (!port) {
    port = await findFreePort(3000);
    console.log(`🔍 Found free port: ${port}`);
  } else {
    console.log(`✅ Using port from environment: ${port}`);
  }

  // Get backend port from environment or use default
  const backendPort = process.env.VITE_API_BASE_URL 
    ? new URL(process.env.VITE_API_BASE_URL).port || '8000'
    : process.env.BACKEND_PORT || '8000';

  // Set environment variables
  process.env.PORT = port.toString();
  process.env.VITE_PORT = port.toString();
  
  // Update VITE_API_BASE_URL if not explicitly set
  if (!process.env.VITE_API_BASE_URL) {
    process.env.VITE_API_BASE_URL = `http://localhost:${backendPort}`;
  }

  console.log(`\n🚀 Starting Unified Trading Engine Frontend`);
  console.log(`📍 Frontend: http://localhost:${port}`);
  console.log(`🔗 Backend API: ${process.env.VITE_API_BASE_URL}`);
  console.log(`\n💡 Tip: Set PORT environment variable to use a specific port`);
  console.log(`💡 Tip: Set BACKEND_PORT or VITE_API_BASE_URL to configure backend connection\n`);

  // Launch vite
  const viteProcess = spawn('vite', ['--port', port.toString()], {
    stdio: 'inherit',
    shell: true,
    cwd: join(__dirname, '..'),
  });

  viteProcess.on('error', (err) => {
    console.error(`❌ Error starting vite: ${err.message}`);
    process.exit(1);
  });

  viteProcess.on('exit', (code) => {
    process.exit(code || 0);
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n\n👋 Shutting down server...');
    viteProcess.kill('SIGINT');
  });

  process.on('SIGTERM', () => {
    viteProcess.kill('SIGTERM');
  });
}

main().catch((err) => {
  console.error(`❌ Error: ${err.message}`);
  process.exit(1);
});
