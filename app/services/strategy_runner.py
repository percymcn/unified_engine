"""
In-House Strategy Runner Service
Runs trading strategies and emits signals using the same schema as webhooks
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import AccountStrategy, Strategy, Account, Signal
from app.models.pydantic_schemas import SignalRequest
from app.services.signal_processor import signal_processor
from app.core.config import settings

logger = logging.getLogger(__name__)

class StrategyRunner:
    """Runs in-house trading strategies"""
    
    def __init__(self):
        self.running_strategies = {}
        self.enabled_accounts = set()
        
    async def initialize(self):
        """Initialize strategy runner"""
        logger.info("Initializing strategy runner...")
        # Load enabled strategies from database
        await self._load_enabled_strategies()
        logger.info("Strategy runner initialized")
    
    async def _load_enabled_strategies(self):
        """Load enabled strategies from database"""
        try:
            db = next(get_db())
            enabled = db.query(AccountStrategy).filter(
                AccountStrategy.is_enabled == True
            ).all()
            
            for account_strategy in enabled:
                account_id = account_strategy.account_id
                strategy = db.query(Strategy).filter(
                    Strategy.id == account_strategy.strategy_id
                ).first()
                
                if strategy and strategy.is_active:
                    self.enabled_accounts.add(account_id)
                    logger.info(f"Loaded enabled strategy {strategy.strategy_id} for account {account_id}")
        except Exception as e:
            logger.error(f"Error loading enabled strategies: {e}")
    
    async def run_strategy(self, strategy_id: str, account_id: int, params: Optional[Dict[str, Any]] = None):
        """Run a specific strategy for an account"""
        try:
            db = next(get_db())
            
            # Verify strategy is enabled for account
            account_strategy = db.query(AccountStrategy).filter(
                AccountStrategy.account_id == account_id,
                AccountStrategy.is_enabled == True
            ).join(Strategy).filter(
                Strategy.strategy_id == strategy_id
            ).first()
            
            if not account_strategy:
                logger.warning(f"Strategy {strategy_id} not enabled for account {account_id}")
                return {"success": False, "error": "Strategy not enabled"}
            
            strategy = db.query(Strategy).filter(
                Strategy.strategy_id == strategy_id
            ).first()
            
            if not strategy or not strategy.is_active:
                return {"success": False, "error": "Strategy not active"}
            
            # Get account
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Run strategy based on type
            if strategy.strategy_id == "ma_cross":
                return await self._run_ma_cross_strategy(account_id, params or {})
            else:
                return {"success": False, "error": f"Unknown strategy: {strategy_id}"}
                
        except Exception as e:
            logger.error(f"Error running strategy {strategy_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _run_ma_cross_strategy(self, account_id: int, params: Dict[str, Any]):
        """Run Moving Average Cross strategy (toy strategy)"""
        try:
            # Default parameters
            fast_period = params.get("fast_period", 10)
            slow_period = params.get("slow_period", 20)
            symbol = params.get("symbol", "EURUSD")
            
            logger.info(f"Running MA Cross strategy for account {account_id}: {symbol}, fast={fast_period}, slow={slow_period}")
            
            # In a real implementation, this would:
            # 1. Fetch historical price data
            # 2. Calculate moving averages
            # 3. Detect crossovers
            # 4. Generate signals
            
            # For now, this is a placeholder that generates a test signal
            # In production, this would connect to market data feeds
            
            # Simulate signal generation
            signal_data = {
                "strategy_id": "ma_cross",
                "strategy_version": "1.0.0",
                "strategy_name": "Moving Average Cross",
                "strategy_source": "inhouse",
                "symbol": symbol,
                "action": "BUY",  # Would be determined by crossover logic
                "volume": params.get("volume", 0.01),
                "price": None,  # Market price
                "stop_loss": params.get("stop_loss"),
                "take_profit": params.get("take_profit"),
                "account_id": account_id,
                "source": "inhouse"
            }
            
            # Emit signal through signal processor
            result = await self._emit_signal(signal_data)
            
            return {
                "success": True,
                "strategy_id": "ma_cross",
                "signal_id": result.get("signal_id"),
                "message": "MA Cross signal generated"
            }
            
        except Exception as e:
            logger.error(f"Error in MA Cross strategy: {e}")
            return {"success": False, "error": str(e)}
    
    async def _emit_signal(self, signal_data: Dict[str, Any]):
        """Emit signal using the same path as webhook execution"""
        try:
            db = next(get_db())
            
            # Create signal request compatible with signal processor
            from app.models.pydantic_schemas import SignalRequest
            
            # Get account to determine broker
            account = db.query(Account).filter(Account.id == signal_data.get("account_id")).first()
            broker = account.broker.value if account else "mt4"
            
            signal_request = SignalRequest(
                broker=broker,
                account_id=signal_data.get("account_id"),
                symbol=signal_data.get("symbol"),
                action=signal_data.get("action", "BUY").lower(),
                quantity=signal_data.get("volume", 0.01),
                price=signal_data.get("price"),
                stop_loss=signal_data.get("stop_loss"),
                take_profit=signal_data.get("take_profit"),
                source="inhouse",
                strategy_id=signal_data.get("strategy_id"),
                strategy_version=signal_data.get("strategy_version"),
                strategy_name=signal_data.get("strategy_name")
            )
            
            # Process signal
            result = await signal_processor.process_signal(signal_request)
            
            return {
                "signal_id": result.signal_id if hasattr(result, "signal_id") else None,
                "success": result.success if hasattr(result, "success") else False
            }
            
        except Exception as e:
            logger.error(f"Error emitting signal: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_periodic_execution(self, strategy_id: str, account_id: int, interval_seconds: int = 60):
        """Start periodic execution of a strategy"""
        task_key = f"{strategy_id}_{account_id}"
        
        if task_key in self.running_strategies:
            logger.warning(f"Strategy {strategy_id} already running for account {account_id}")
            return
        
        async def periodic_task():
            while True:
                try:
                    await self.run_strategy(strategy_id, account_id)
                    await asyncio.sleep(interval_seconds)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in periodic strategy execution: {e}")
                    await asyncio.sleep(interval_seconds)
        
        task = asyncio.create_task(periodic_task())
        self.running_strategies[task_key] = task
        logger.info(f"Started periodic execution of {strategy_id} for account {account_id}")
    
    async def stop_periodic_execution(self, strategy_id: str, account_id: int):
        """Stop periodic execution of a strategy"""
        task_key = f"{strategy_id}_{account_id}"
        
        if task_key in self.running_strategies:
            task = self.running_strategies[task_key]
            task.cancel()
            del self.running_strategies[task_key]
            logger.info(f"Stopped periodic execution of {strategy_id} for account {account_id}")

# Global strategy runner instance
strategy_runner = StrategyRunner()
