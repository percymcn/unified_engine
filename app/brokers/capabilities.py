"""
Broker Capability Matrix

Defines which brokers support which trading operations and features.
Used to return 501 Not Implemented for unsupported features.
"""

from enum import Enum
from typing import Dict, Set, List
from dataclasses import dataclass


class BrokerType(str, Enum):
    """Supported broker types."""
    TRADELOCKER = "tradelocker"
    TRADOVATE = "tradovate"
    PROJECTX = "projectx"
    TOPSTEP = "topstep"  # Alias for projectx
    MT4 = "mt4"
    MT5 = "mt5"


class Capability(str, Enum):
    """Trading capabilities."""
    # Accounts
    ACCOUNTS_LIST = "accounts.list"
    ACCOUNTS_INFO = "accounts.info"
    
    # Positions
    POSITIONS_OPEN = "positions.open"
    POSITIONS_HISTORY = "positions.history"
    
    # Orders
    ORDERS_LIST = "orders.list"
    ORDERS_PLACE = "orders.place"
    ORDERS_MODIFY = "orders.modify"
    ORDERS_CANCEL = "orders.cancel"
    ORDERS_CANCEL_ALL = "orders.cancel_all"
    ORDERS_BRACKET = "orders.bracket"  # OCO orders
    ORDERS_CHAIN = "orders.chain"
    
    # Market Data
    MARKET_QUOTE = "market.quote"
    MARKET_HISTORY = "market.history"  # OHLCV
    MARKET_ORDERBOOK = "market.orderbook"  # Level 2
    
    # Streaming
    STREAMING_SUBSCRIBE = "streaming.subscribe"
    STREAMING_UNSUBSCRIBE = "streaming.unsubscribe"
    
    # Analytics
    ANALYTICS_PERFORMANCE = "analytics.performance"
    ANALYTICS_SESSION = "analytics.session"
    ANALYTICS_PORTFOLIO = "analytics.portfolio"
    
    # Technical Indicators
    INDICATORS = "indicators"


@dataclass
class BrokerCapabilities:
    """Capabilities for a specific broker."""
    broker: BrokerType
    capabilities: Set[Capability]
    
    def supports(self, capability: Capability) -> bool:
        """Check if broker supports a capability."""
        return capability in self.capabilities
    
    def get_unsupported(self, requested: List[Capability]) -> List[Capability]:
        """Get list of unsupported capabilities from requested list."""
        return [c for c in requested if c not in self.capabilities]


class BrokerCapabilityMatrix:
    """
    Capability matrix for all brokers.
    
    Defines which operations each broker supports based on SDK and API capabilities.
    """
    
    def __init__(self):
        """Initialize capability matrix."""
        self._matrix: Dict[BrokerType, BrokerCapabilities] = {
            BrokerType.TRADELOCKER: BrokerCapabilities(
                broker=BrokerType.TRADELOCKER,
                capabilities={
                    Capability.ACCOUNTS_LIST,
                    Capability.ACCOUNTS_INFO,
                    Capability.POSITIONS_OPEN,
                    Capability.ORDERS_LIST,
                    Capability.ORDERS_PLACE,
                    Capability.ORDERS_MODIFY,
                    Capability.ORDERS_CANCEL,
                    Capability.MARKET_QUOTE,
                    Capability.MARKET_HISTORY,  # get_price_history
                    # Note: cancel_all, bracket, chain not explicitly supported
                    # streaming via WebSocket but not formal subscribe/unsubscribe API
                }
            ),
            BrokerType.TRADOVATE: BrokerCapabilities(
                broker=BrokerType.TRADOVATE,
                capabilities={
                    Capability.ACCOUNTS_LIST,
                    Capability.ACCOUNTS_INFO,
                    Capability.POSITIONS_OPEN,
                    Capability.ORDERS_LIST,
                    Capability.ORDERS_PLACE,
                    Capability.ORDERS_MODIFY,
                    Capability.ORDERS_CANCEL,
                    Capability.ORDERS_BRACKET,  # place_bracket_order implemented
                    Capability.MARKET_QUOTE,
                    Capability.STREAMING_SUBSCRIBE,  # WebSocket subscriptions
                    Capability.STREAMING_UNSUBSCRIBE,
                    # Note: cancel_all, chain, history, orderbook, analytics not explicitly supported
                }
            ),
            BrokerType.PROJECTX: BrokerCapabilities(
                broker=BrokerType.PROJECTX,
                capabilities={
                    Capability.ACCOUNTS_LIST,
                    Capability.ACCOUNTS_INFO,
                    Capability.POSITIONS_OPEN,
                    Capability.POSITIONS_HISTORY,  # get_position_history
                    Capability.ORDERS_LIST,
                    Capability.ORDERS_PLACE,
                    Capability.ORDERS_MODIFY,
                    Capability.ORDERS_CANCEL,
                    Capability.ORDERS_CANCEL_ALL,  # cancel_all_orders implemented
                    Capability.ORDERS_BRACKET,  # place_bracket_order implemented
                    Capability.ORDERS_CHAIN,  # create_order_chain implemented
                    Capability.MARKET_QUOTE,
                    Capability.MARKET_HISTORY,  # get_market_data
                    Capability.MARKET_ORDERBOOK,  # get_orderbook implemented
                    Capability.STREAMING_SUBSCRIBE,  # subscribe_realtime_data
                    Capability.STREAMING_UNSUBSCRIBE,
                    Capability.ANALYTICS_PERFORMANCE,  # get_performance_stats
                    Capability.ANALYTICS_SESSION,  # get_session_statistics
                    Capability.ANALYTICS_PORTFOLIO,  # get_portfolio_metrics
                    Capability.INDICATORS,  # calculate_technical_indicators
                }
            ),
            BrokerType.TOPSTEP: BrokerCapabilities(
                broker=BrokerType.TOPSTEP,
                capabilities=BrokerCapabilities(
                    broker=BrokerType.PROJECTX,
                    capabilities={
                        Capability.ACCOUNTS_LIST,
                        Capability.ACCOUNTS_INFO,
                        Capability.POSITIONS_OPEN,
                        Capability.POSITIONS_HISTORY,
                        Capability.ORDERS_LIST,
                        Capability.ORDERS_PLACE,
                        Capability.ORDERS_MODIFY,
                        Capability.ORDERS_CANCEL,
                        Capability.ORDERS_CANCEL_ALL,
                        Capability.ORDERS_BRACKET,
                        Capability.ORDERS_CHAIN,
                        Capability.MARKET_QUOTE,
                        Capability.MARKET_HISTORY,
                        Capability.MARKET_ORDERBOOK,
                        Capability.STREAMING_SUBSCRIBE,
                        Capability.STREAMING_UNSUBSCRIBE,
                        Capability.ANALYTICS_PERFORMANCE,
                        Capability.ANALYTICS_SESSION,
                        Capability.ANALYTICS_PORTFOLIO,
                        Capability.INDICATORS,
                    }
                ).capabilities  # Same as PROJECTX
            ),
            BrokerType.MT4: BrokerCapabilities(
                broker=BrokerType.MT4,
                capabilities={
                    Capability.ACCOUNTS_LIST,
                    Capability.ACCOUNTS_INFO,
                    Capability.POSITIONS_OPEN,
                    Capability.POSITIONS_HISTORY,  # get_deal_history
                    Capability.ORDERS_LIST,
                    Capability.ORDERS_PLACE,
                    Capability.ORDERS_CANCEL,
                    Capability.MARKET_QUOTE,
                    # Note: modify, cancel_all, bracket, chain, orderbook, analytics, indicators not supported
                }
            ),
            BrokerType.MT5: BrokerCapabilities(
                broker=BrokerType.MT5,
                capabilities={
                    Capability.ACCOUNTS_LIST,
                    Capability.ACCOUNTS_INFO,
                    Capability.POSITIONS_OPEN,
                    Capability.POSITIONS_HISTORY,  # get_deal_history
                    Capability.ORDERS_LIST,
                    Capability.ORDERS_PLACE,
                    Capability.ORDERS_CANCEL,
                    Capability.MARKET_QUOTE,
                    # Note: modify, cancel_all, bracket, chain, orderbook, analytics, indicators not supported
                }
            ),
        }
    
    def get_capabilities(self, broker: BrokerType) -> BrokerCapabilities:
        """
        Get capabilities for a broker.
        
        Args:
            broker: Broker type
            
        Returns:
            BrokerCapabilities object
        """
        # Handle TOPSTEP alias
        if broker == BrokerType.TOPSTEP:
            broker = BrokerType.PROJECTX
        
        return self._matrix.get(broker, BrokerCapabilities(
            broker=broker,
            capabilities=set()  # No capabilities if unknown broker
        ))
    
    def supports(self, broker: BrokerType, capability: Capability) -> bool:
        """
        Check if broker supports a capability.
        
        Args:
            broker: Broker type
            capability: Capability to check
            
        Returns:
            True if supported, False otherwise
        """
        caps = self.get_capabilities(broker)
        return caps.supports(capability)
    
    def get_unsupported(self, broker: BrokerType, requested: List[Capability]) -> List[Capability]:
        """
        Get list of unsupported capabilities for a broker.
        
        Args:
            broker: Broker type
            requested: List of requested capabilities
            
        Returns:
            List of unsupported capabilities
        """
        caps = self.get_capabilities(broker)
        return caps.get_unsupported(requested)
    
    def get_all_capabilities(self) -> Dict[BrokerType, Set[Capability]]:
        """
        Get all capabilities for all brokers.
        
        Returns:
            Dict mapping broker to set of capabilities
        """
        return {
            broker: caps.capabilities
            for broker, caps in self._matrix.items()
        }
    
    def get_capability_matrix_table(self) -> str:
        """
        Generate a markdown table of capabilities.
        
        Returns:
            Markdown table string
        """
        all_caps = sorted(list(Capability))
        brokers = sorted([b for b in BrokerType if b != BrokerType.TOPSTEP])  # Exclude alias
        
        lines = ["| Capability | " + " | ".join(b.value for b in brokers) + " |"]
        lines.append("|" + "---|" * (len(brokers) + 1))
        
        for cap in all_caps:
            row = [cap.value]
            for broker in brokers:
                supported = self.supports(broker, cap)
                row.append("✅" if supported else "❌")
            lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(lines)


# Global instance
_capability_matrix = None


def get_capability_matrix() -> BrokerCapabilityMatrix:
    """Get global capability matrix instance."""
    global _capability_matrix
    if _capability_matrix is None:
        _capability_matrix = BrokerCapabilityMatrix()
    return _capability_matrix
