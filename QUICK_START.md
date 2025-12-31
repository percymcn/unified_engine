# Quick Start Guide - Running UI Locally

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- PostgreSQL 12+
- Redis 6+

## Step-by-Step Setup

### 1. Backend Setup (Terminal 1)

```bash
# Navigate to project
cd /home/pharma5/unified_engine

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# Initialize database
alembic upgrade head

# Start backend server (with automatic port finding)
python run_backend.py

# Or use specific port:
# PORT=8000 python run_backend.py

# Or use traditional method:
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend will automatically find a free port starting from 8000  
📚 API Docs: `http://localhost:<PORT>/docs`  
💡 The assigned port will be displayed in the console output

### 2. Frontend Setup (Terminal 2)

```bash
# Navigate to UI directory
cd /home/pharma5/unified_engine/ui

# Install dependencies
npm install

# Create environment file (optional)
# Note: Backend port will be auto-detected if using run_backend.py
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local

# Start development server (with automatic port finding)
npm run dev:free

# Or use specific port:
# PORT=3000 npm run dev:free

# Or use traditional method:
# npm run dev
```

✅ Frontend will automatically find a free port starting from 3000  
💡 The assigned port will be displayed in the console output

### 3. Verify Setup

```bash
# Check backend health (use the port shown in console output)
# Example: curl http://localhost:8000/health
# Or if backend found port 8001: curl http://localhost:8001/health

# Check frontend (use the port shown in console output)
# Example: Open http://localhost:3000 in browser
# Or if frontend found port 3001: Open http://localhost:3001
```

💡 **Note:** Both backend and frontend will display their assigned ports in the console.  
💡 **Tip:** The frontend will automatically connect to the backend port shown in the backend console.

## Using Docker (Alternative)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Check Redis is running: `redis-cli ping`
- Verify `.env` file has correct database URL

### Frontend won't start
- Clear node_modules: `rm -rf node_modules && npm install`
- Check port 3000 is available: `lsof -i :3000`
- Verify backend is running (check console for assigned port)
- If using `dev:free`, ensure scripts/find-port.js is executable: `chmod +x ui/scripts/find-port.js`

### Database errors
- Run migrations: `alembic upgrade head`
- Check database exists: `psql -l | grep trading_db`

## Enterprise Features

### Analytics Dashboard
Access the analytics dashboard at `/analytics` (requires admin or premium subscription):
- User signups over time
- Subscription distribution
- Revenue statistics
- API usage metrics

### Dark Mode
Toggle dark/light mode using the theme switcher in the top bar.

### Notifications
- Real-time in-app notifications via WebSocket
- Email notifications (configure SMTP in `.env`)
- Notification preferences in user settings

### Docker Deployment
```bash
# Start all services with Docker
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Next Steps

1. Create a user account via API or admin script
2. Login through the UI
3. Access analytics dashboard (admin/premium)
4. Configure notification preferences
5. Add your first broker account
6. Start trading!

For detailed setup, see [SETUP_GUIDE.md](./SETUP_GUIDE.md)  
For deployment options, see [DEPLOYMENT.md](./DEPLOYMENT.md)  
For enterprise features, see [ENTERPRISE_FEATURES_COMPLETE.md](./ENTERPRISE_FEATURES_COMPLETE.md)
