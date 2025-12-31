# Dynamic Port Finding - Implementation Guide

## Overview

The Unified Trading Engine now supports automatic port finding to prevent conflicts when multiple instances are running or when default ports are already in use.

## Features

- ✅ **Backend**: Automatically finds free port starting from 8000
- ✅ **Frontend**: Automatically finds free port starting from 3000
- ✅ **Environment Variable Support**: Can override with `PORT` env var
- ✅ **Auto-detection**: Frontend automatically detects backend port
- ✅ **Console Output**: Displays assigned ports clearly

---

## Backend Dynamic Ports

### Using `run_backend.py` (Recommended)

```bash
# Automatic port finding (starts from 8000)
python run_backend.py

# Output example:
# 🔍 Found free port: 8000
# 🚀 Starting Unified Trading Engine Backend
# 📍 Server: http://0.0.0.0:8000
# 📚 API Docs: http://0.0.0.0:8000/docs
```

### Using Specific Port

```bash
# Set PORT environment variable
PORT=8001 python run_backend.py

# Output example:
# ✅ Using port from environment: 8001
```

### Traditional Method (Still Supported)

```bash
# Direct uvicorn command
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Frontend Dynamic Ports

### Using `npm run dev:free` (Recommended)

```bash
cd ui/
npm run dev:free

# Output example:
# 🔍 Found free port: 3000
# 🚀 Starting Unified Trading Engine Frontend
# 📍 Frontend: http://localhost:3000
# 🔗 Backend API: http://localhost:8000
```

### Using Specific Port

```bash
# Set PORT environment variable
PORT=3001 npm run dev:free

# Output example:
# ✅ Using port from environment: 3001
```

### Traditional Method (Still Supported)

```bash
# Standard vite command (will auto-increment if port taken)
npm run dev
```

---

## How It Works

### Backend Port Finding

1. Checks `PORT` environment variable first
2. If not set, finds free port starting from 8000
3. Uses socket binding to check port availability
4. Sets `PORT` env var for uvicorn to use
5. Displays assigned port in console

**Implementation:** `run_backend.py`

### Frontend Port Finding

1. Checks `PORT` or `VITE_PORT` environment variable first
2. If not set, finds free port starting from 3000
3. Uses Node.js `net` module to check port availability
4. Sets `PORT` env var for vite to use
5. Auto-detects backend port from `VITE_API_BASE_URL` or `BACKEND_PORT`
6. Updates vite proxy configuration dynamically
7. Displays assigned ports in console

**Implementation:** `ui/scripts/find-port.js`

---

## Configuration

### Environment Variables

#### Backend

```bash
# .env file
PORT=8000          # Optional: specific port (leave unset for auto-find)
HOST=0.0.0.0       # Server host
RELOAD=true        # Auto-reload in development
```

#### Frontend

```bash
# ui/.env.local file
VITE_API_BASE_URL=http://localhost:8000  # Backend URL
VITE_PORT=3000                            # Optional: specific port
BACKEND_PORT=8000                        # Optional: backend port override
PORT=3000                                 # Alternative port setting
```

### Vite Configuration

The `vite.config.js` automatically:
- Uses `PORT` or `VITE_PORT` environment variable
- Falls back to port 3000 if not set
- Allows vite to auto-increment if port is taken (`strictPort: false`)
- Configures proxy to use backend port from environment

---

## Port Conflict Prevention

### Scenario 1: Multiple Backend Instances

```bash
# Terminal 1
python run_backend.py
# Finds port 8000

# Terminal 2
python run_backend.py
# Finds port 8001 (8000 is taken)

# Terminal 3
python run_backend.py
# Finds port 8002 (8000, 8001 are taken)
```

### Scenario 2: Multiple Frontend Instances

```bash
# Terminal 1
cd ui/ && npm run dev:free
# Finds port 3000

# Terminal 2
cd ui/ && npm run dev:free
# Finds port 3001 (3000 is taken)

# Terminal 3
cd ui/ && npm run dev:free
# Finds port 3002 (3000, 3001 are taken)
```

### Scenario 3: Port Already in Use

```bash
# If port 8000 is already used by another service
python run_backend.py
# Automatically finds next available port (8001, 8002, etc.)
```

---

## Integration with Existing Workflows

### Docker

Docker Compose still uses fixed ports as defined in `docker-compose.yml`. Dynamic port finding is primarily for local development.

### CI/CD

In CI/CD pipelines, you can set specific ports:

```yaml
# GitHub Actions example
env:
  PORT: 8000
  VITE_PORT: 3000
```

### Production

In production, use fixed ports configured in your deployment:

```bash
# Production deployment
PORT=8000 python run_backend.py
# Or use gunicorn with fixed port
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Troubleshooting

### Backend Port Issues

**Problem:** `run_backend.py` can't find free port

**Solution:**
```bash
# Check what's using ports
lsof -i :8000-8010

# Kill processes if needed
kill -9 <PID>

# Or use specific port
PORT=9000 python run_backend.py
```

### Frontend Port Issues

**Problem:** `npm run dev:free` fails

**Solution:**
```bash
# Make script executable
chmod +x ui/scripts/find-port.js

# Or use traditional method
npm run dev

# Or use specific port
PORT=3001 npm run dev:free
```

### Backend Connection Issues

**Problem:** Frontend can't connect to backend

**Solution:**
```bash
# Ensure backend port matches frontend config
# Check backend console for assigned port
# Update ui/.env.local:
echo "VITE_API_BASE_URL=http://localhost:<BACKEND_PORT>" > ui/.env.local

# Or set BACKEND_PORT environment variable
BACKEND_PORT=8001 npm run dev:free
```

---

## Benefits

1. **No Manual Port Management**: Automatically finds available ports
2. **Multiple Instances**: Run multiple dev servers without conflicts
3. **Easy Collaboration**: Team members don't need to coordinate ports
4. **Development Speed**: No need to kill processes or change configs
5. **Backward Compatible**: Traditional methods still work

---

## Migration Guide

### From Fixed Ports to Dynamic Ports

**Before:**
```bash
# Backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
npm run dev
```

**After:**
```bash
# Backend
python run_backend.py

# Frontend
npm run dev:free
```

**Benefits:**
- No port conflicts
- Clearer console output
- Automatic port detection
- Better developer experience

---

## Summary

Dynamic port finding eliminates port conflicts and simplifies local development:

- ✅ Backend finds free port starting from 8000
- ✅ Frontend finds free port starting from 3000
- ✅ Frontend auto-detects backend port
- ✅ Environment variables override auto-detection
- ✅ Clear console output shows assigned ports
- ✅ Backward compatible with existing workflows

**Quick Start:**
```bash
# Backend
python run_backend.py

# Frontend (new terminal)
cd ui/ && npm run dev:free
```

---

*Last Updated: 2025-01-27*
