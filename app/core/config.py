"""
Unified Configuration for Trading Engine
Supports all broker configurations and environment settings
"""
import os
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Unified Trading Engine"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/trading_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 3600
    REDIS_SESSION_TTL: int = 86400
    
    # API
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/trading_engine.log"
    LOG_MAX_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    @field_validator("LOG_MAX_SIZE", mode="before")
    @classmethod
    def parse_log_max_size(cls, v):
        """Parse LOG_MAX_SIZE from string format like '100MB' to bytes"""
        if isinstance(v, str):
            v = v.upper().strip()
            if v.endswith('MB'):
                return int(v[:-2]) * 1024 * 1024
            elif v.endswith('GB'):
                return int(v[:-2]) * 1024 * 1024 * 1024
            elif v.endswith('KB'):
                return int(v[:-2]) * 1024
            elif v.endswith('B'):
                return int(v[:-1])
            else:
                # Assume it's already in bytes
                return int(v)
        return v
    
    # TradeLocker Configuration
    TRADELOCKER_API_KEY: Optional[str] = None
    TRADELOCKER_API_URL: str = "https://api.tradelocker.com"
    TRADELOCKER_WS_URL: str = "wss://api.tradelocker.com/brand-api/socket.io/"
    TRADELOCKER_ENV: str = "LIVE"  # LIVE or DEMO
    
    # Tradovate Configuration
    TRADOVATE_API_URL: str = "https://demo.tradovate.com/api/v1"
    TRADOVATE_WS_URL: str = "wss://demo.tradovate.com/api/v1/websocket"
    TRADOVATE_USER_ID: Optional[str] = None
    TRADOVATE_PASSWORD: Optional[str] = None
    TRADOVATE_APP_ID: str = "TradingEngine"
    TRADOVATE_APP_VERSION: str = "1.0.0"
    TRADOVATE_CID: str = "TradingEngine"
    TRADOVATE_SEC: str = "TradingEngine"
    
    # ProjectX/TopStep Configuration
    PROJECTX_API_URL: str = "https://gateway.projectx.com/api/v1"
    PROJECTX_WS_URL: str = "wss://gateway.projectx.com/ws"
    PROJECTX_API_TOKEN: Optional[str] = None
    PROJECTX_ENV: str = "LIVE"  # LIVE or DEMO
    
    # MT4 Configuration
    MT4_API_URL: str = "http://localhost:8080/api"
    MT4_MANAGER_HOST: str = "localhost"
    MT4_MANAGER_PORT: int = 443
    MT4_MANAGER_LOGIN: int = 1
    MT4_MANAGER_PASSWORD: str = "manager"
    
    # MT5 Configuration
    MT5_API_URL: str = "http://localhost:8081/api"
    MT5_MANAGER_HOST: str = "localhost"
    MT5_MANAGER_PORT: int = 443
    MT5_MANAGER_LOGIN: int = 1
    MT5_MANAGER_PASSWORD: str = "manager"
    
    # Signal Processing
    SIGNAL_PROCESSING_ENABLED: bool = True
    SIGNAL_RETRY_ATTEMPTS: int = 3
    SIGNAL_RETRY_DELAY: int = 5
    SIGNAL_TIMEOUT: int = 30
    
    # Risk Management
    MAX_POSITION_SIZE: float = 100.0
    MAX_DAILY_LOSS: float = 1000.0
    MAX_LEVERAGE: int = 50
    RISK_MANAGEMENT_ENABLED: bool = True
    
    # Monitoring
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 60
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v):
        if v == "your-secret-key-change-in-production" and os.getenv("ENVIRONMENT") == "production":
            raise ValueError("SECRET_KEY must be changed in production")
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }
        
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"
    
    def get_broker_config(self, broker_name: str) -> Dict[str, Any]:
        """Get broker-specific configuration"""
        broker_configs = {
            "tradelocker": {
                "api_url": self.TRADELOCKER_API_URL,
                "ws_url": self.TRADELOCKER_WS_URL,
                "api_key": self.TRADELOCKER_API_KEY,
                "environment": self.TRADELOCKER_ENV
            },
            "tradovate": {
                "api_url": self.TRADOVATE_API_URL,
                "ws_url": self.TRADOVATE_WS_URL,
                "user_id": self.TRADOVATE_USER_ID,
                "password": self.TRADOVATE_PASSWORD,
                "app_id": self.TRADOVATE_APP_ID,
                "app_version": self.TRADOVATE_APP_VERSION,
                "cid": self.TRADOVATE_CID,
                "sec": self.TRADOVATE_SEC
            },
            "projectx": {
                "api_url": self.PROJECTX_API_URL,
                "ws_url": self.PROJECTX_WS_URL,
                "api_token": self.PROJECTX_API_TOKEN,
                "environment": self.PROJECTX_ENV
            },
            "mt4": {
                "api_url": self.MT4_API_URL,
                "manager_host": self.MT4_MANAGER_HOST,
                "manager_port": self.MT4_MANAGER_PORT,
                "manager_login": self.MT4_MANAGER_LOGIN,
                "manager_password": self.MT4_MANAGER_PASSWORD
            },
            "mt5": {
                "api_url": self.MT5_API_URL,
                "manager_host": self.MT5_MANAGER_HOST,
                "manager_port": self.MT5_MANAGER_PORT,
                "manager_login": self.MT5_MANAGER_LOGIN,
                "manager_password": self.MT5_MANAGER_PASSWORD
            }
        }
        
        return broker_configs.get(broker_name.lower(), {})
    
    def get_webhook_config(self) -> Dict[str, Any]:
        """Get webhook configuration"""
        return {
            "timeout": self.SIGNAL_TIMEOUT,
            "retry_attempts": self.SIGNAL_RETRY_ATTEMPTS,
            "retry_delay": self.SIGNAL_RETRY_DELAY,
            "enabled": self.SIGNAL_PROCESSING_ENABLED
        }

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Global settings instance
settings = get_settings()