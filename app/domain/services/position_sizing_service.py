"""
Position Sizing Service

Calculates position sizes based on different sizing modes:
- Fixed lot size
- Percentage of balance
- Percentage of equity
- Risk-based (using stop loss distance and risk percentage)
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PositionSizingMode(str, Enum):
    """Position sizing calculation modes"""
    FIXED = "fixed"
    PERCENT_BALANCE = "percent_balance"
    PERCENT_EQUITY = "percent_equity"
    RISK_BASED = "risk_based"


@dataclass
class PositionSizingConfig:
    """Position sizing configuration for an account"""
    mode: PositionSizingMode
    fixed_lot_size: float = 0.01
    percent_of_balance: float = 1.0
    percent_of_equity: float = 1.0
    risk_percent_per_trade: float = 1.0
    max_position_size: Optional[float] = None


@dataclass
class SymbolSpecs:
    """Symbol specifications from broker"""
    min_lot: float = 0.01
    max_lot: float = 100.0
    lot_step: float = 0.01
    contract_size: float = 100000  # Standard forex lot
    pip_value: float = 10.0  # USD per pip for 1 lot
    digits: int = 5


@dataclass
class PositionSizeResult:
    """Result of position size calculation"""
    calculated_size: float  # Raw calculated size
    adjusted_size: float  # Size adjusted to broker specs
    mode_used: str
    calculation_detail: str


class PositionSizingService:
    """
    Calculates position sizes based on account settings and risk parameters.

    Supports four modes:
    1. Fixed: Use configured lot size
    2. Percent Balance: Size as % of account balance
    3. Percent Equity: Size as % of account equity
    4. Risk Based: Size based on risk % and stop loss distance
    """

    def calculate_position_size(
        self,
        config: PositionSizingConfig,
        balance: float,
        equity: float,
        symbol_specs: SymbolSpecs,
        stop_loss_pips: Optional[float] = None
    ) -> PositionSizeResult:
        """
        Calculate position size based on mode and account state.

        Args:
            config: Account position sizing settings
            balance: Current account balance
            equity: Current account equity
            symbol_specs: Symbol specifications from broker
            stop_loss_pips: Stop loss distance in pips (required for risk_based mode)

        Returns:
            PositionSizeResult with calculated and adjusted sizes
        """
        if config.mode == PositionSizingMode.FIXED:
            calculated = config.fixed_lot_size
            detail = f"Fixed lot size: {config.fixed_lot_size}"

        elif config.mode == PositionSizingMode.PERCENT_BALANCE:
            # Calculate lots based on percentage of balance
            # Formula: (balance * percent) / (contract_size)
            risk_amount = balance * (config.percent_of_balance / 100)
            calculated = risk_amount / symbol_specs.contract_size
            detail = f"{config.percent_of_balance}% of ${balance:.2f} balance = ${risk_amount:.2f} = {calculated:.4f} lots"

        elif config.mode == PositionSizingMode.PERCENT_EQUITY:
            # Calculate lots based on percentage of equity
            risk_amount = equity * (config.percent_of_equity / 100)
            calculated = risk_amount / symbol_specs.contract_size
            detail = f"{config.percent_of_equity}% of ${equity:.2f} equity = ${risk_amount:.2f} = {calculated:.4f} lots"

        elif config.mode == PositionSizingMode.RISK_BASED:
            if not stop_loss_pips or stop_loss_pips <= 0:
                # Fall back to fixed if no stop loss provided
                calculated = config.fixed_lot_size
                detail = f"Risk-based fallback to fixed (no SL): {config.fixed_lot_size}"
            else:
                # Risk-based position sizing
                # Formula: (account_risk) / (pip_risk * pip_value)
                account_risk = balance * (config.risk_percent_per_trade / 100)
                pip_risk = stop_loss_pips * symbol_specs.pip_value
                calculated = account_risk / pip_risk if pip_risk > 0 else config.fixed_lot_size
                detail = (
                    f"Risk ${account_risk:.2f} ({config.risk_percent_per_trade}% of ${balance:.2f}) "
                    f"with {stop_loss_pips} pip SL = {calculated:.4f} lots"
                )

        else:
            calculated = config.fixed_lot_size
            detail = f"Unknown mode, fallback to fixed: {config.fixed_lot_size}"

        # Apply max position size limit if configured
        if config.max_position_size and calculated > config.max_position_size:
            calculated = config.max_position_size
            detail += f" (capped at max: {config.max_position_size})"

        # Adjust to broker specifications
        adjusted = self._adjust_to_specs(calculated, symbol_specs)

        return PositionSizeResult(
            calculated_size=calculated,
            adjusted_size=adjusted,
            mode_used=config.mode.value,
            calculation_detail=detail
        )

    def _adjust_to_specs(self, size: float, specs: SymbolSpecs) -> float:
        """Adjust position size to broker specifications"""
        # Round to lot step
        steps = round(size / specs.lot_step)
        adjusted = steps * specs.lot_step

        # Enforce min/max
        adjusted = max(specs.min_lot, adjusted)
        adjusted = min(specs.max_lot, adjusted)

        # Round to reasonable precision
        adjusted = round(adjusted, 2)

        return adjusted

    def calculate_stop_loss_pips(
        self,
        entry_price: float,
        stop_loss_price: float,
        digits: int = 5
    ) -> float:
        """
        Calculate stop loss distance in pips.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            digits: Symbol digits (5 for forex, 2 for indices)

        Returns:
            Stop loss distance in pips
        """
        if digits >= 4:
            # Forex: pip is 0.0001 (4th decimal for JPY pairs, 5th for others)
            pip_size = 0.0001 if digits == 4 else 0.00001
            multiplier = 10 if digits == 5 else 1
        else:
            # Indices/commodities: pip is typically 1 point
            pip_size = 1.0
            multiplier = 1

        distance = abs(entry_price - stop_loss_price)
        pips = (distance / pip_size) * multiplier

        return round(pips, 1)
