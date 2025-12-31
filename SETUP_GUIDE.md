# Setup Guide - Unified Trading Engine

## Quick Start - Running UI Locally

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.9+
- PostgreSQL 12+
- Redis 6+

### Step 1: Backend Setup

```bash
# Navigate to project root
cd /home/pharma5/unified_engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and Redis credentials

# Initialize database
alembic upgrade head

# Create admin user (optional)
python scripts/create_admin.py

# Start backend server (recommended: automatic port finding)
python run_backend.py

# Or use specific port:
# PORT=8000 python run_backend.py

# Or use traditional method:
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will automatically find a free port starting from 8000  
The assigned port will be displayed in the console output  
API Documentation: `http://localhost:<PORT>/docs`

### Step 2: Frontend Setup

```bash
# Navigate to UI directory
cd ui/

# Install dependencies
npm install

# Create .env file for frontend (if needed)
# Note: Backend port will be auto-detected if using run_backend.py
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local

# Start development server (recommended: automatic port finding)
npm run dev:free

# Or use specific port:
# PORT=3000 npm run dev:free

# Or use traditional method:
# npm run dev
```

Frontend will automatically find a free port starting from 3000  
The assigned port will be displayed in the console output

### Step 3: Using Docker (Alternative)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Detailed Setup Instructions

### Backend Configuration

#### Environment Variables (.env)

```bash
# Application
APP_NAME=Unified Trading Engine
APP_VERSION=3.0.0
DEBUG=True
ENVIRONMENT=development

# Security
SECRET_KEY=your-secret-key-change-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/trading_db

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Stripe (for subscriptions)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### Database Setup

```bash
# Create PostgreSQL database
createdb trading_db

# Or using psql
psql -U postgres
CREATE DATABASE trading_db;
CREATE USER trading_user WITH PASSWORD 'trading_password';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
\q

# Run migrations
alembic upgrade head

# Verify tables created
psql -U trading_user -d trading_db -c "\dt"
```

#### Redis Setup

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### Frontend Configuration

#### Environment Variables

Create `ui/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

#### Build for Production

```bash
cd ui/
npm run build
npm run preview  # Preview production build locally
```

---

## Development Workflow

### Running Tests

```bash
# Backend tests
pytest
pytest --cov=app  # With coverage
pytest tests/test_api.py -v  # Verbose output

# Frontend tests (if configured)
cd ui/
npm test
```

### Code Quality

```bash
# Backend linting
flake8 app/
black app/  # Formatting
mypy app/   # Type checking

# Frontend linting
cd ui/
npm run lint
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## Troubleshooting

### Backend Issues

**Issue:** Database connection error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection string in .env
# Test connection
psql $DATABASE_URL
```

**Issue:** Redis connection error
```bash
# Check Redis is running
redis-cli ping

# Verify Redis URL in .env
# Test connection
redis-cli -u $REDIS_URL ping
```

**Issue:** Port already in use
```bash
# Option 1: Use run_backend.py which automatically finds free port
python run_backend.py

# Option 2: Find process using port 8000
lsof -i :8000
# Kill process
kill -9 <PID>

# Option 3: Use different port
PORT=8001 python run_backend.py
```

### Frontend Issues

**Issue:** Module not found
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Issue:** API connection error
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check CORS settings in backend
# Verify VITE_API_BASE_URL in .env.local
```

**Issue:** Build errors
```bash
# Clear build cache
rm -rf dist node_modules/.vite
npm run build
```

---

## Production Deployment

### Using Docker Compose

```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-stack.yml unified_engine

# View services
docker stack services unified_engine

# View logs
docker service logs unified_engine_api
```

### Manual Deployment

```bash
# Backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Frontend
cd ui/
npm run build
# Serve dist/ directory with nginx or similar
```

---

## Health Checks

### Backend Health

```bash
# Basic health check (use the port shown in backend console)
# Example: curl http://localhost:8000/health
# Or if backend found port 8001: curl http://localhost:8001/health

# Detailed status
curl http://localhost:<PORT>/status

# Metrics
curl http://localhost:<PORT>/metrics
```

### Frontend Health

```bash
# Check if dev server is running (use the port shown in frontend console)
# Example: curl http://localhost:3000
# Or if frontend found port 3001: curl http://localhost:3001

# Check API connection
# Open browser console and check for API errors
# Frontend will automatically connect to backend port
```

---

## Enterprise Features

### Analytics Dashboard
- Access at `/analytics` (admin/premium only)
- View user signups, subscriptions, revenue, API usage
- Interactive charts and visualizations

### Dark Mode
- Toggle in top bar
- Persistent preference
- Premium glassmorphism effects

### Notifications
- Real-time WebSocket notifications
- Email notifications (configure SMTP)
- User preferences and quiet hours

### Docker Deployment
See [DEPLOYMENT.md](./DEPLOYMENT.md) for:
- Docker Compose setup
- AWS/GCP deployment
- Production configurations

### Testing
```bash
# Backend tests
pytest tests/ -v

# Frontend tests (if configured)
cd ui && npm test
```

## Next Steps

1. ✅ Backend and frontend running locally
2. ✅ Database initialized
3. ✅ Access analytics dashboard (admin/premium)
4. ✅ Configure notifications
5. ✅ Create your first user account
6. ✅ Add broker accounts
7. ✅ Start trading!

For more information, see:
- [API Documentation](http://localhost:8000/docs)
- [Project Analysis](./PROJECT_ANALYSIS.md)
- [Enterprise Features](./ENTERPRISE_FEATURES_COMPLETE.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [AGENTS.md](./AGENTS.md) - Development guide

---

*Last Updated: 2025-01-27*
