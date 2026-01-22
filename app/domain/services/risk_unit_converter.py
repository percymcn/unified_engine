"""
Risk Unit Converter Service

Converts broker-specific risk units (pips/points/percent) to absolute price values
for execution compatibility.

This service bridges the gap between UI inputs (which use broker-specific units)
and backend execution (which requires absolute prices).
"""

import logging
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RiskUnitMode(str, Enum):
    """Risk unit modes supported by the system"""
    PIPS = "pips"
    POINTS = "points"
    PERCENT = "percent"
    PRICE = "price"  # Already absolute price


class RiskUnitConverter:
    """
    Converts broker-specific risk units to absolute prices.
    
    Conversion formulas:
    - Pips: price = entryPrice ± (pips × pipSize)
    - Points: price = entryPrice ± (points × tickSize)
    - Percent: price = entryPrice × (1 ± percent/100)
    """

    @staticmethod
    def convert_pips_to_price(
        pips: float,
        entry_price: float,
        is_buy: bool,
        is_stop_loss: bool,
        digits: int = 5
    ) -> float:
        """
        Convert pips to absolute price.
        
        Args:
            pips: Stop loss/take profit in pips
            entry_price: Entry price for the trade
            is_buy: True for buy orders, False for sell orders
            is_stop_loss: True for stop loss, False for take profit
            digits: Symbol precision (4 for JPY pairs, 5 for most forex)
            
        Returns:
            Absolute price value
            
        Raises:
            ValueError: If calculated price is invalid
        """
        if pips <= 0:
            raise ValueError(f"Pips value must be positive, got {pips}")
        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")
        
        # Determine pip size based on symbol precision
        # 4-digit brokers (JPY pairs): pip = 0.01
        # 5-digit brokers (most forex): pip = 0.0001
        if digits == 4:
            pip_size = 0.01
        elif digits == 3:
            pip_size = 0.01  # JPY pairs typically use 3 digits
        else:
            pip_size = 0.0001  # Standard 5-digit forex
        
        # Calculate price distance
        price_distance = pips * pip_size
        
        # Calculate absolute price based on direction
        # For buy orders:
        #   - Stop loss: entryPrice - priceDistance (below entry)
        #   - Take profit: entryPrice + priceDistance (above entry)
        # For sell orders:
        #   - Stop loss: entryPrice + priceDistance (above entry)
        #   - Take profit: entryPrice - priceDistance (below entry)
        
        if is_buy:
            absolute_price = entry_price - price_distance if is_stop_loss else entry_price + price_distance
        else:
            absolute_price = entry_price + price_distance if is_stop_loss else entry_price - price_distance
        
        # Validate: price must be positive
        if absolute_price <= 0:
            raise ValueError(
                f"Calculated price {absolute_price} is invalid (must be positive). "
                f"Entry: {entry_price}, Pips: {pips}, Distance: {price_distance}"
            )
        
        # Validate: SL must be on correct side of entry
        if is_stop_loss:
            if is_buy and absolute_price >= entry_price:
                raise ValueError(
                    f"Stop loss {absolute_price} must be below entry price {entry_price} for buy orders"
                )
            if not is_buy and absolute_price <= entry_price:
                raise ValueError(
                    f"Stop loss {absolute_price} must be above entry price {entry_price} for sell orders"
                )
        
        # Validate: TP must be on correct side of entry
        if not is_stop_loss:
            if is_buy and absolute_price <= entry_price:
                raise ValueError(
                    f"Take profit {absolute_price} must be above entry price {entry_price} for buy orders"
                )
            if not is_buy and absolute_price >= entry_price:
                raise ValueError(
                    f"Take profit {absolute_price} must be below entry price {entry_price} for sell orders"
                )
        
        return absolute_price

    @staticmethod
    def convert_points_to_price(
        points: float,
        entry_price: float,
        is_buy: bool,
        is_stop_loss: bool,
        tick_size: float = 0.25
    ) -> float:
        """
        Convert points to absolute price.
        
        Args:
            points: Stop loss/take profit in points
            entry_price: Entry price for the trade
            is_buy: True for buy orders, False for sell orders
            is_stop_loss: True for stop loss, False for take profit
            tick_size: Minimum price movement (tick size) for the contract
            
        Returns:
            Absolute price value
            
        Raises:
            ValueError: If calculated price is invalid
        """
        if points <= 0:
            raise ValueError(f"Points value must be positive, got {points}")
        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")
        if tick_size <= 0:
            raise ValueError(f"Tick size must be positive, got {tick_size}")
        
        # Calculate price distance
        price_distance = points * tick_size
        
        # Calculate absolute price based on direction
        if is_buy:
            absolute_price = entry_price - price_distance if is_stop_loss else entry_price + price_distance
        else:
            absolute_price = entry_price + price_distance if is_stop_loss else entry_price - price_distance
        
        # Validate: price must be positive
        if absolute_price <= 0:
            raise ValueError(
                f"Calculated price {absolute_price} is invalid (must be positive). "
                f"Entry: {entry_price}, Points: {points}, Distance: {price_distance}"
            )
        
        # Validate: SL must be on correct side of entry
        if is_stop_loss:
            if is_buy and absolute_price >= entry_price:
                raise ValueError(
                    f"Stop loss {absolute_price} must be below entry price {entry_price} for buy orders"
                )
            if not is_buy and absolute_price <= entry_price:
                raise ValueError(
                    f"Stop loss {absolute_price} must be above entry price {entry_price} for sell orders"
                )
        
        # Validate: TP must be on correct side of entry
        if not is_stop_loss:
            if is_buy and absolute_price <= entry_price:
                raise ValueError(
                    f"Take profit {absolute_price} must be above entry price {entry_price} for buy orders"
                )
            if not is_buy and absolute_price >= entry_price:
                raise ValueError(
                    f"Take profit {absolute_price} must be below entry price {entry_price} for sell orders"
                )
        
        return absolute_price

    @staticmethod
    def convert_percent_to_price(
        percent: float,
        entry_price: float,
        is_buy: bool,
        is_stop_loss: bool
    ) -> float:
        """
        Convert percentage to absolute price.
        
        Args:
            percent: Stop loss/take profit as percentage
            entry_price: Entry price for the trade
            is_buy: True for buy orders, False for sell orders
            is_stop_loss: True for stop loss, False for take profit
            
        Returns:
            Absolute price value
            
        Raises:
            ValueError: If calculated price is invalid
        """
        if percent <= 0:
            raise ValueError(f"Percent value must be positive, got {percent}")
        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")
        
        # Calculate price distance as percentage of entry price
        price_distance = (entry_price * percent) / 100.0
        
        # Calculate absolute price based on direction
        if is_buy:
            absolute_price = entry_price - price_distance if is_stop_loss else entry_price + price_distance
        else:
            absolute_price = entry_price + price_distance if is_stop_loss else entry_price - price_distance
        
        # Validate: price must be positive
        if absolute_price <= 0:
            raise ValueError(
                f"Calculated price {absolute_price} is invalid (must be positive). "
                f"Entry: {entry_price}, Percent: {percent}%, Distance: {price_distance}"
            )
        
        # Validate: SL must be on correct side of entry
        if is_stop_loss:
            if is_buy and absolute_price >= entry_price:
                raise ValueError(
                    f"Stop loss {absolute_price} must be below entry price {entry_price} for buy orders"
                )
            if not is_buy and absolute_price <= entry_price:
                raise ValueError(
                    f"Stop loss {absolute_price} must be above entry price {entry_price} for sell orders"
                )
        
        # Validate: TP must be on correct side of entry
        if not is_stop_loss:
            if is_buy and absolute_price <= entry_price:
                raise ValueError(
                    f"Take profit {absolute_price} must be above entry price {entry_price} for buy orders"
                )
            if not is_buy and absolute_price >= entry_price:
                raise ValueError(
                    f"Take profit {absolute_price} must be below entry price {entry_price} for sell orders"
                )
        
        return absolute_price

    @staticmethod
    def convert_risk_unit_to_price(
        value: float,
        mode: RiskUnitMode,
        entry_price: float,
        is_buy: bool,
        is_stop_loss: bool,
        digits: int = 5,
        tick_size: float = 0.25
    ) -> float:
        """
        Main conversion function that handles all broker types.
        
        Args:
            value: Risk value in broker-specific unit (pips/points/percent)
            mode: Unit mode (pips/points/percent/price)
            entry_price: Entry price for the trade
            is_buy: True for buy orders, False for sell orders
            is_stop_loss: True for stop loss, False for take profit
            digits: Symbol precision (for pips conversion)
            tick_size: Tick size (for points conversion)
            
        Returns:
            Absolute price value
            
        Raises:
            ValueError: If conversion fails or calculated price is invalid
        """
        if mode == RiskUnitMode.PRICE:
            # Already in absolute price, return as-is (but validate)
            if value <= 0:
                raise ValueError(f"Price value must be positive, got {value}")
            return value
        
        if mode == RiskUnitMode.PIPS:
            return RiskUnitConverter.convert_pips_to_price(
                value, entry_price, is_buy, is_stop_loss, digits
            )
        elif mode == RiskUnitMode.POINTS:
            return RiskUnitConverter.convert_points_to_price(
                value, entry_price, is_buy, is_stop_loss, tick_size
            )
        elif mode == RiskUnitMode.PERCENT:
            return RiskUnitConverter.convert_percent_to_price(
                value, entry_price, is_buy, is_stop_loss
            )
        else:
            raise ValueError(f"Unsupported risk unit mode: {mode}")

    @staticmethod
    def get_default_tick_size(broker_type: str) -> float:
        """
        Get default tick size for a broker.
        
        Args:
            broker_type: Broker type (tradovate, projectx, etc.)
            
        Returns:
            Default tick size
        """
        # Tradovate futures typically use 0.25 tick size
        # This should ideally come from contract specs, but we provide defaults
        defaults = {
            "tradovate": 0.25,
            "projectx": 0.25,
            "topstep": 0.25,
        }
        return defaults.get(broker_type.lower(), 0.0001)  # Default for forex (1 pip)

    @staticmethod
    def get_default_digits(broker_type: str) -> int:
        """
        Get default symbol precision for a broker.
        
        Args:
            broker_type: Broker type (tradelocker, mt4, mt5, etc.)
            
        Returns:
            Default symbol precision (digits)
        """
        # Most forex brokers use 5 digits (0.00001)
        # JPY pairs use 3-4 digits (0.01)
        # This should ideally come from symbol specs, but we provide defaults
        defaults = {
            "tradelocker": 5,
            "mt4": 5,
            "mt5": 5,
            "truforex": 5,
        }
        return defaults.get(broker_type.lower(), 5)
