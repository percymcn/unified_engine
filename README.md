# Unified Trading Engine

A comprehensive, production-ready trading system that integrates multiple trading platforms and brokers into a single, unified API.

## 🚀 Features

### Core Functionality
- **Multi-Broker Support**: MT4, MT5, and custom broker integrations
- **Signal Processing**: Real-time signal handling and execution
- **Risk Management**: Advanced position sizing and risk controls
- **Portfolio Management**: Unified account and position tracking
- **Real-time Monitoring**: WebSocket connections for live data
- **Webhook Integration**: External signal source support

### Technical Features
- **FastAPI Backend**: High-performance async API
- **PostgreSQL Database**: Reliable data persistence
- **Redis Caching**: High-speed caching and session management
- **Celery Tasks**: Asynchronous background processing
- **Docker Support**: Containerized deployment
- **Monitoring**: Prometheus metrics and Grafana dashboards

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Docker (optional)

## 🛠️ Installation

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd unified_engine

# Run the installation script
./install.sh

# Configure your environment
cp .env.example .env
# Edit .env with your settings

# Start the engine
./start.sh
```

### Manual Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Create admin user
python scripts/create_admin.py
```

## ⚙️ Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/trading_db

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Brokers
MT4_API_URL=http://localhost:8080
MT5_API_URL=http://localhost:8081
```

### Database Setup
```bash
# Create database
createdb trading_db

# Run migrations
alembic upgrade head
```

## 🌐 API Documentation

Once started, visit:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 📊 Monitoring

### Built-in Monitoring
- **Flower (Celery)**: http://localhost:5555
- **Health Checks**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### External Monitoring
- **Grafana**: http://localhost:3001 (if configured)
- **Prometheus**: http://localhost:9090 (if configured)

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific tests
pytest tests/test_signals.py
```

### Code Quality
```bash
# Linting
flake8 app/
black app/

# Type checking
mypy app/
```

## 📁 Project Structure

```
unified_engine/
├── app/
│   ├── api/                 # API endpoints
│   ├── core/               # Core configuration
│   ├── models/             # Database models
│   ├── services/           # Business logic
│   ├── brokers/            # Broker integrations
│   ├── utils/              # Utilities
│   └── main.py            # FastAPI application
├── alembic/               # Database migrations
├── tests/                 # Test suite
├── docker/               # Docker configuration
├── scripts/              # Utility scripts
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── install.sh           # Installation script
└── start.sh            # Startup script
```

## 🔌 API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - User registration
- `POST /login` - User login
- `GET /me` - Get current user
- `POST /logout` - Logout
- `POST /refresh` - Refresh token
- `PUT /change-password` - Change password

### API Keys (`/api/v1/api-keys`)
- `GET /` - List API keys
- `POST /` - Create API key
- `GET /{id}` - Get API key details
- `DELETE /{id}` - Revoke API key

### Accounts (`/api/v1/accounts`)
- `GET /` - List all accounts
- `GET /{id}` - Get account details
- `POST /` - Create new account
- `PUT /{id}` - Update account
- `DELETE /{id}` - Delete account
- `POST /{id}/sync` - Sync with broker
- `GET /{id}/balance` - Get account balance

### Strategies (`/api/strategies`)
- `GET /top` - Top performing strategies
- `GET /` - List all strategies
- `GET /{id}/stats` - Strategy statistics
- `POST /{id}/enable` - Enable strategy for account
- `POST /{id}/disable` - Disable strategy for account

### Strategy Execution (`/api/v1/strategy-execution`)
- `POST /run` - Run strategy once
- `POST /start-periodic` - Start periodic execution
- `POST /stop-periodic` - Stop periodic execution

### Signals (`/api/v1/signals`)
- `GET /` - List signals
- `POST /` - Create signal
- `GET /{id}` - Get signal details
- `POST /{id}/cancel` - Cancel signal
- `GET /history` - Signal history
- `GET /active` - Active signals
- `POST /execute` - Execute signal

### Positions (`/api/v1/positions`)
- `GET /` - List positions
- `GET /{id}` - Get position
- `POST /{id}/close` - Close position
- `GET /account/{account_id}` - Get account positions

### Trades (`/api/v1/trades`)
- `GET /` - List trades
- `GET /{id}` - Get trade details
- `GET /account/{account_id}` - Get account trades

### Webhooks (`/api/v1/webhooks`)
- `POST /tradingview` - TradingView webhook (supports strategy info)
- `POST /trailhacker` - TrailHacker webhook
- `GET /logs` - Webhook logs
- `GET /logs/{id}` - Get webhook log
- `POST /test` - Test webhook

## 🚀 Deployment

### One-Command Deployment (Recommended)
```bash
# Deploy entire stack
./scripts/deploy_one.sh

# Verify deployment
./scripts/verify_one.sh
```

### Docker Swarm Deployment
```bash
# Deploy stack
docker stack deploy -c docker-stack.yml unified_engine_stack

# View services
docker stack services unified_engine_stack

# View logs
docker service logs unified_engine_stack_api
```

### Docker Compose (Development)
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

### Production Deployment
```bash
# Set production environment
export ENVIRONMENT=production

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 🧪 Testing

### Health Check
```bash
# Check service health
./scripts/verify_green.sh
```

### End-to-End User Flow Test
```bash
# Run smoke test
./scripts/smoke_user_flow.sh
```

### Manual API Testing
```bash
# Health endpoint
curl http://localhost:3012/health

# Login (replace credentials)
curl -X POST "http://localhost:3012/api/v1/auth/login?username=test&password=test"

# Create API key (replace token)
curl -X POST "http://localhost:3012/api/v1/api-keys?name=Test%20Key" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔒 Security

- JWT-based authentication
- API key management
- Rate limiting
- CORS configuration
- Input validation
- SQL injection prevention

## 📈 Performance

- Async/await for high concurrency
- Redis caching for fast responses
- Database connection pooling
- Efficient query optimization
- Background task processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API docs at /docs

## 🔄 Version History

- **v1.0.0** - Initial release with core functionality
- **v1.1.0** - Added webhook support
- **v1.2.0** - Enhanced monitoring capabilities
- **v2.0.0** - Unified architecture with multi-broker support