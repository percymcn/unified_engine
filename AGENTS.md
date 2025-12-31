# AGENTS.md - Development Guide for Agentic Coding

This file provides essential information for agentic coding agents working in the Unified Trading Engine repository.

## Project Overview

This is a comprehensive trading system built with FastAPI backend and React frontend, supporting multiple broker integrations (MT4, MT5, TradeLocker, Tradovate, ProjectX). The system features real-time signal processing, WebSocket connections, risk management, and a modern React dashboard.

## Architecture

```
unified_engine/
├── app/                    # FastAPI backend
│   ├── api/               # API routers  
│   ├── core/              # Core configuration and security
│   ├── models/            # Database models and Pydantic schemas
│   ├── services/          # Business logic services
│   ├── brokers/           # Broker integration executors
│   ├── db/                # Database configuration
│   ├── cache/             # Redis client
│   └── main.py           # FastAPI application entry
├── ui/                    # React frontend
│   ├── src/
│   │   ├── pages/        # React page components
│   │   ├── components/   # Reusable components
│   │   ├── services/     # API and WebSocket services
│   │   └── stores/       # State management
├── tests/                 # Test suite
├── alembic/              # Database migrations
└── scripts/              # Utility scripts
```

## Build/Test/Lint Commands

### Backend (Python)
```bash
# Environment setup
source venv/bin/activate  # or: source backend/venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest                          # All tests
pytest tests/test_api.py        # Single test file
pytest tests/test_api.py::TestAuthentication::test_user_login  # Specific test
pytest --cov=app               # With coverage
pytest -v                       # Verbose output

# Code quality (if tools available)
flake8 app/                     # Linting
black app/                      # Formatting
mypy app/                       # Type checking

# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head            # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend (React)
```bash
cd ui/

# Install dependencies
npm install

# Development server
npm run dev                      # Starts on port 3000

# Build for production
npm run build

# Preview build
npm run preview

# Linting
npm run lint                     # ESLint
```

### System Testing
```bash
# Health check
./scripts/verify_green.sh        # Comprehensive system health

# Manual API testing
curl http://localhost:8000/health
curl http://localhost:8000/docs  # API documentation
```

## Code Style Guidelines

### Python (Backend)

#### Import Organization
```python
# Standard library imports first
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Third-party imports
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Local imports
from app.core.config import settings
from app.models.models import User
from app.services.signal_processor import signal_processor
```

#### Naming Conventions
- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase` 
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_underscore_prefix`
- **File names**: `snake_case.py`

#### Type Hints
Always use type hints for function signatures and important variables:
```python
from typing import Dict, List, Optional, Union, Any

async def process_signal(
    signal_data: Dict[str, Any],
    user_id: int,
    db: Session
) -> Optional[SignalResponse]:
    """Process trading signal with proper type hints."""
    pass
```

#### Error Handling
```python
# Use specific exceptions
try:
    result = await broker.execute_order(order_data)
except ConnectionError as e:
    logger.error(f"Broker connection failed: {e}")
    raise HTTPException(status_code=503, detail="Broker unavailable")
except ValueError as e:
    logger.warning(f"Invalid order data: {e}")
    raise HTTPException(status_code=400, detail=str(e))

# Always log errors with context
logger.error(f"Signal processing failed for signal {signal_id}: {error}", exc_info=True)
```

#### Async/Await Patterns
- Use `async/await` for I/O operations
- Database calls should be async where possible
- Always handle async context managers properly:

```python
async def get_user_accounts(user_id: int, db: Session) -> List[Account]:
    """Get user accounts with async database operations."""
    try:
        accounts = db.query(Account).filter(Account.user_id == user_id).all()
        return accounts
    except Exception as e:
        logger.error(f"Failed to get accounts for user {user_id}: {e}")
        return []
```

#### Configuration
Use the centralized settings from `app.core.config`:
```python
from app.core.config import settings

# Use settings for all configuration
database_url = settings.DATABASE_URL
redis_url = settings.REDIS_URL
api_timeout = settings.SIGNAL_TIMEOUT
```

### JavaScript/React (Frontend)

#### Import Organization
```javascript
// React imports first
import React, { useState, useEffect } from 'react'

// Third-party libraries
import { 
  Box, 
  Button, 
  Typography,
  useTheme 
} from '@mui/material'
import { useNavigate } from 'react-router-dom'

// Local imports
import { useAuthStore } from '../stores/authStore'
import { apiClient } from '../services/api'
import DashboardLayout from '../layout/DashboardLayout'
```

#### Component Structure
```javascript
// Functional components with hooks
const Dashboard = () => {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const theme = useTheme()
  const { user } = useAuthStore()
  
  useEffect(() => {
    fetchDashboardData()
  }, [])
  
  const fetchDashboardData = async () => {
    setLoading(true)
    try {
      const response = await apiClient.get('/dashboard')
      setData(response.data)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4">Dashboard</Typography>
      {/* Component JSX */}
    </Box>
  )
}

export default Dashboard
```

#### State Management
Use Zustand for global state:
```javascript
// stores/authStore.js
import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  login: (userData) => set({ user: userData, isAuthenticated: true }),
  logout: () => set({ user: null, isAuthenticated: false }),
}))
```

#### API Calls
Use the centralized API client:
```javascript
import { apiClient } from '../services/api'

const fetchAccounts = async () => {
  try {
    const response = await apiClient.get('/accounts')
    return response.data
  } catch (error) {
    throw new Error(`Failed to fetch accounts: ${error.message}`)
  }
}
```

## Testing Guidelines

### Backend Testing
- Use `pytest` for all backend tests
- Mock external dependencies (brokers, databases)
- Test both success and failure scenarios
- Use descriptive test names and docstrings

```python
class TestSignalProcessor:
    """Test signal processing functionality."""
    
    @pytest.fixture
    def mock_broker(self):
        """Create mock broker for testing."""
        broker = AsyncMock()
        broker.execute_order.return_value = {"success": True, "order_id": "123"}
        return broker
    
    async def test_process_signal_success(self, mock_broker):
        """Test successful signal processing."""
        processor = SignalProcessor()
        processor.brokers["test"] = mock_broker
        
        signal_data = {"symbol": "EURUSD", "side": "BUY"}
        result = await processor.process_signal(signal_data, "test")
        
        assert result.success is True
        assert result.order_id == "123"
```

### Frontend Testing
- Test component rendering and user interactions
- Mock API calls
- Test error states and loading states

## Database Patterns

### Models
Use SQLAlchemy models with proper relationships:
```python
class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    broker = Column(Enum(BrokerType), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    positions = relationship("Position", back_populates="account")
```

### Pydantic Schemas
Use Pydantic for request/response validation:
```python
class AccountCreate(BaseModel):
    broker: BrokerType
    account_id: str
    account_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    
    class Config:
        from_attributes = True
```

## Security Guidelines

- Never commit secrets or API keys
- Use environment variables for sensitive configuration
- Validate all input data using Pydantic schemas
- Use JWT tokens for authentication
- Implement proper error handling without exposing sensitive information

## Performance Considerations

- Use database connection pooling
- Implement Redis caching for frequently accessed data
- Use async/await for I/O operations
- Implement pagination for large data sets
- Use WebSocket for real-time updates instead of polling

## Common Patterns

### Error Response Format
```python
# Standardized error responses
return JSONResponse(
    status_code=400,
    content={
        "error": "Validation failed",
        "details": {"field": "Invalid value"},
        "timestamp": datetime.utcnow().isoformat()
    }
)
```

### Success Response Format
```python
# Standardized success responses
return {
    "success": True,
    "data": result_data,
    "message": "Operation completed successfully",
    "timestamp": datetime.utcnow().isoformat()
}
```

### Database Session Pattern
```python
def get_db():
    """Database dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Environment Variables

Always use the centralized settings system:
```python
from app.core.config import settings

# Access configuration
database_url = settings.DATABASE_URL
debug_mode = settings.DEBUG
broker_config = settings.get_broker_config("mt4")
```

## WebSocket Usage

For real-time features, use the WebSocket manager:
```python
from app.core.websocket_manager import ws_manager

# Send real-time updates
await ws_manager.broadcast_to_user(user_id, {
    "type": "position_update",
    "data": position_data
})
```

## Important Notes

- All broker integrations should implement the base executor interface
- Use proper logging throughout the application
- Database migrations should be reversible
- API endpoints should follow RESTful conventions
- Frontend should handle loading and error states gracefully
- Always use the provided test database for testing
- Never run production code with DEBUG=True

## Testing Single Components

To test a specific component:
```bash
# Backend specific test
pytest tests/test_signal_processor.py -v

# Frontend component test (if Jest is set up)
npm test -- Dashboard.test.js
```

This guide should help agentic coding agents understand the codebase structure, conventions, and proper ways to make changes while maintaining code quality and consistency.