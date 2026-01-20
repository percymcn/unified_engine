"""
Broker Adapters Package

Contains concrete implementations of BrokerPort for each broker integration:
- TradeLockerAdapter (Plan 05-06)
- TopStepAdapter (Plan 05-07)
- TradovateAdapter (Plan 05-08)
- MT4Adapter (Plan 05-09)
- MT5Adapter (Plan 05-10)

Each adapter:
- Implements app.domain.ports.broker_port.BrokerPort
- Translates domain operations to broker-specific API calls
- Converts broker responses to domain entities
- Handles broker-specific authentication and connection management
"""

# Broker adapter exports
# Will be populated as each broker adapter is implemented

__all__ = [
    # "TradeLockerAdapter",  # Plan 05-06
    # "TopStepAdapter",       # Plan 05-07
    # "TradovateAdapter",     # Plan 05-08
    # "MT4Adapter",           # Plan 05-09
    # "MT5Adapter",           # Plan 05-10
]
