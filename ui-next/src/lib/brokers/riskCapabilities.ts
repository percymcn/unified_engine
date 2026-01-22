/**
 * Broker Risk Capabilities
 * 
 * Defines broker-specific constraints for risk management inputs:
 * - Stop loss/take profit units and precision
 * - Position size units and step sizes
 * - Min/max values
 * 
 * This is UI-only configuration for input validation and display.
 * Execution logic remains unchanged.
 */

import { BrokerType } from '@/types/account';

/**
 * Stop loss/take profit unit modes
 */
export type StopLossMode = 'pips' | 'points' | 'percent' | 'price';

/**
 * Position size unit types
 */
export type PositionSizeUnit = 'lots' | 'units' | 'contracts';

/**
 * Broker risk capability profile
 */
export interface BrokerRiskProfile {
  /** Broker type */
  broker: BrokerType;
  
  /** Stop loss/take profit configuration */
  stopLoss: {
    /** Unit mode for stop loss */
    mode: StopLossMode;
    /** Decimal precision (0.1, 0.01, 0.001) */
    precision: number;
    /** Minimum value */
    min: number;
    /** Maximum value */
    max: number;
    /** Step size for inputs */
    step: number;
    /** Display label */
    label: string;
    /** Helper text explaining the unit */
    helperText: string;
  };
  
  /** Take profit configuration (may differ from stop loss) */
  takeProfit: {
    mode: StopLossMode;
    precision: number;
    min: number;
    max: number;
    step: number;
    label: string;
    helperText: string;
  };
  
  /** Position size configuration */
  positionSize: {
    /** Unit type */
    unit: PositionSizeUnit;
    /** Minimum position size */
    min: number;
    /** Maximum position size */
    max: number;
    /** Step size for inputs */
    step: number;
    /** Display label */
    label: string;
    /** Helper text */
    helperText: string;
  };
  
  /** Risk percentage configuration */
  riskPercent: {
    min: number;
    max: number;
    step: number;
    precision: number;
  };
}

/**
 * Broker risk capability profiles
 * 
 * Conservative defaults ensure safe trading practices.
 */
export const BROKER_RISK_PROFILES: Record<BrokerType, BrokerRiskProfile> = {
  // TradeLocker: Uses pips for forex, points for indices
  tradelocker: {
    broker: 'tradelocker',
    stopLoss: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 1000,
      step: 1,
      label: 'Stop Loss (pips)',
      helperText: 'Stop loss distance in pips. 1 pip = 0.0001 for most currency pairs.',
    },
    takeProfit: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 2000,
      step: 1,
      label: 'Take Profit (pips)',
      helperText: 'Take profit distance in pips. 1 pip = 0.0001 for most currency pairs.',
    },
    positionSize: {
      unit: 'lots',
      min: 0.01,
      max: 100,
      step: 0.01,
      label: 'Position Size (lots)',
      helperText: 'Position size in standard lots. Minimum: 0.01 lot.',
    },
    riskPercent: {
      min: 0.1,
      max: 10,
      step: 0.1,
      precision: 0.1,
    },
  },
  
  // Tradovate: Futures contracts, uses ticks/points
  tradovate: {
    broker: 'tradovate',
    stopLoss: {
      mode: 'points',
      precision: 0.25,
      min: 0.25,
      max: 500,
      step: 0.25,
      label: 'Stop Loss (points)',
      helperText: 'Stop loss distance in points. 1 point = minimum price movement for the contract.',
    },
    takeProfit: {
      mode: 'points',
      precision: 0.25,
      min: 0.25,
      max: 1000,
      step: 0.25,
      label: 'Take Profit (points)',
      helperText: 'Take profit distance in points. 1 point = minimum price movement for the contract.',
    },
    positionSize: {
      unit: 'contracts',
      min: 1,
      max: 100,
      step: 1,
      label: 'Position Size (contracts)',
      helperText: 'Number of contracts to trade. Minimum: 1 contract.',
    },
    riskPercent: {
      min: 0.1,
      max: 10,
      step: 0.1,
      precision: 0.1,
    },
  },
  
  // ProjectX/TopStep: Funded account challenges, uses percentage
  projectx: {
    broker: 'projectx',
    stopLoss: {
      mode: 'percent',
      precision: 0.01,
      min: 0.1,
      max: 10,
      step: 0.1,
      label: 'Stop Loss (%)',
      helperText: 'Stop loss as percentage of account balance. Conservative: 1-2%.',
    },
    takeProfit: {
      mode: 'percent',
      precision: 0.01,
      min: 0.1,
      max: 20,
      step: 0.1,
      label: 'Take Profit (%)',
      helperText: 'Take profit as percentage of account balance.',
    },
    positionSize: {
      unit: 'lots',
      min: 0.01,
      max: 50,
      step: 0.01,
      label: 'Position Size (lots)',
      helperText: 'Position size in standard lots. Minimum: 0.01 lot.',
    },
    riskPercent: {
      min: 0.1,
      max: 5, // More conservative for funded accounts
      step: 0.1,
      precision: 0.1,
    },
  },
  
  topstep: {
    broker: 'topstep',
    stopLoss: {
      mode: 'percent',
      precision: 0.01,
      min: 0.1,
      max: 10,
      step: 0.1,
      label: 'Stop Loss (%)',
      helperText: 'Stop loss as percentage of account balance. Conservative: 1-2%.',
    },
    takeProfit: {
      mode: 'percent',
      precision: 0.01,
      min: 0.1,
      max: 20,
      step: 0.1,
      label: 'Take Profit (%)',
      helperText: 'Take profit as percentage of account balance.',
    },
    positionSize: {
      unit: 'lots',
      min: 0.01,
      max: 50,
      step: 0.01,
      label: 'Position Size (lots)',
      helperText: 'Position size in standard lots. Minimum: 0.01 lot.',
    },
    riskPercent: {
      min: 0.1,
      max: 5,
      step: 0.1,
      precision: 0.1,
    },
  },
  
  // MT4: Standard forex broker, uses pips
  mt4: {
    broker: 'mt4',
    stopLoss: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 1000,
      step: 1,
      label: 'Stop Loss (pips)',
      helperText: 'Stop loss distance in pips. 1 pip = 0.0001 for 5-digit brokers, 0.00001 for 5-digit.',
    },
    takeProfit: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 2000,
      step: 1,
      label: 'Take Profit (pips)',
      helperText: 'Take profit distance in pips. 1 pip = 0.0001 for 5-digit brokers.',
    },
    positionSize: {
      unit: 'lots',
      min: 0.01,
      max: 100,
      step: 0.01,
      label: 'Position Size (lots)',
      helperText: 'Position size in standard lots. Minimum: 0.01 lot (micro lot).',
    },
    riskPercent: {
      min: 0.1,
      max: 10,
      step: 0.1,
      precision: 0.1,
    },
  },
  
  // MT5: Similar to MT4 but may support more instruments
  mt5: {
    broker: 'mt5',
    stopLoss: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 1000,
      step: 1,
      label: 'Stop Loss (pips)',
      helperText: 'Stop loss distance in pips. 1 pip = 0.0001 for 5-digit brokers, 0.00001 for 5-digit.',
    },
    takeProfit: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 2000,
      step: 1,
      label: 'Take Profit (pips)',
      helperText: 'Take profit distance in pips. 1 pip = 0.0001 for 5-digit brokers.',
    },
    positionSize: {
      unit: 'lots',
      min: 0.01,
      max: 100,
      step: 0.01,
      label: 'Position Size (lots)',
      helperText: 'Position size in standard lots. Minimum: 0.01 lot (micro lot).',
    },
    riskPercent: {
      min: 0.1,
      max: 10,
      step: 0.1,
      precision: 0.1,
    },
  },
  
  // TruForex: Default to conservative forex settings
  truforex: {
    broker: 'truforex',
    stopLoss: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 1000,
      step: 1,
      label: 'Stop Loss (pips)',
      helperText: 'Stop loss distance in pips. 1 pip = 0.0001 for most currency pairs.',
    },
    takeProfit: {
      mode: 'pips',
      precision: 0.1,
      min: 1,
      max: 2000,
      step: 1,
      label: 'Take Profit (pips)',
      helperText: 'Take profit distance in pips. 1 pip = 0.0001 for most currency pairs.',
    },
    positionSize: {
      unit: 'lots',
      min: 0.01,
      max: 100,
      step: 0.01,
      label: 'Position Size (lots)',
      helperText: 'Position size in standard lots. Minimum: 0.01 lot.',
    },
    riskPercent: {
      min: 0.1,
      max: 10,
      step: 0.1,
      precision: 0.1,
    },
  },
};

/**
 * Get risk profile for a broker
 */
export function getBrokerRiskProfile(broker: BrokerType): BrokerRiskProfile {
  return BROKER_RISK_PROFILES[broker] || BROKER_RISK_PROFILES.tradelocker;
}

/**
 * Format value according to broker precision
 */
export function formatBrokerValue(value: number, precision: number): number {
  const factor = 1 / precision;
  return Math.round(value * factor) / factor;
}

/**
 * Validate value against broker constraints
 */
export function validateBrokerValue(
  value: number,
  min: number,
  max: number,
  step: number
): { valid: boolean; corrected?: number } {
  if (value < min) {
    return { valid: false, corrected: min };
  }
  if (value > max) {
    return { valid: false, corrected: max };
  }
  
  // Check if value is a valid step
  const remainder = (value - min) % step;
  if (remainder > 0.0001 && remainder < step - 0.0001) {
    // Round to nearest valid step
    const corrected = Math.round((value - min) / step) * step + min;
    return { valid: false, corrected };
  }
  
  return { valid: true };
}
