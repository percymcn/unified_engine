/**
 * Risk Unit Converter
 * 
 * Converts broker-specific risk units (pips/points/percent) to absolute price values
 * for backend API compatibility.
 * 
 * IMPORTANT: Backend expects absolute price values, not relative units.
 * This module ensures UI inputs are converted before sending to API.
 */

import { BrokerType } from '@/types/account';
import { StopLossMode } from './riskCapabilities';

/**
 * Convert pips to absolute price
 * 
 * Formula: price = entryPrice ± (pips × pipSize)
 * 
 * @param pips - Stop loss/take profit in pips
 * @param entryPrice - Entry price for the trade
 * @param isBuy - True for buy orders, false for sell orders
 * @param digits - Symbol precision (4 for JPY pairs, 5 for most forex)
 * @returns Absolute price value
 */
export function convertPipsToPrice(
  pips: number,
  entryPrice: number,
  isBuy: boolean,
  digits: number = 5
): number {
  // Determine pip size based on symbol precision
  // 4-digit brokers (JPY pairs): pip = 0.01
  // 5-digit brokers (most forex): pip = 0.0001
  const pipSize = digits === 4 ? 0.01 : 0.0001;
  
  // Calculate price distance
  const priceDistance = pips * pipSize;
  
  // For buy orders: SL below entry, TP above entry
  // For sell orders: SL above entry, TP below entry
  // This function is used for both SL and TP, so we need direction
  // For SL: buy = subtract, sell = add
  // For TP: buy = add, sell = subtract
  // We'll handle direction in the calling code
  
  return priceDistance;
}

/**
 * Convert points to absolute price
 * 
 * Formula: price = entryPrice ± (points × tickSize)
 * 
 * @param points - Stop loss/take profit in points
 * @param entryPrice - Entry price for the trade
 * @param tickSize - Minimum price movement (tick size) for the contract
 * @returns Price distance in absolute terms
 */
export function convertPointsToPrice(
  points: number,
  entryPrice: number,
  tickSize: number = 0.25
): number {
  // Calculate price distance
  const priceDistance = points * tickSize;
  
  return priceDistance;
}

/**
 * Convert percentage to absolute price
 * 
 * Formula: price = entryPrice × (1 ± percent/100)
 * OR: priceDistance = entryPrice × percent/100
 * 
 * @param percent - Stop loss/take profit as percentage
 * @param entryPrice - Entry price for the trade
 * @returns Price distance in absolute terms
 */
export function convertPercentToPrice(
  percent: number,
  entryPrice: number
): number {
  // Calculate price distance as percentage of entry price
  const priceDistance = (entryPrice * percent) / 100;
  
  return priceDistance;
}

/**
 * Convert broker-specific risk unit to absolute price
 * 
 * This is the main conversion function that handles all broker types.
 * 
 * @param value - Risk value in broker-specific unit (pips/points/percent)
 * @param mode - Unit mode (pips/points/percent)
 * @param entryPrice - Entry price for the trade
 * @param isBuy - True for buy orders, false for sell orders
 * @param isStopLoss - True for stop loss, false for take profit
 * @param broker - Broker type (for broker-specific defaults)
 * @param digits - Symbol precision (for pips conversion)
 * @param tickSize - Tick size (for points conversion)
 * @returns Absolute price value
 */
export function convertRiskUnitToPrice(
  value: number,
  mode: StopLossMode,
  entryPrice: number,
  isBuy: boolean,
  isStopLoss: boolean,
  broker: BrokerType,
  digits: number = 5,
  tickSize: number = 0.25
): number {
  if (!value || value <= 0) {
    throw new Error('Risk value must be positive');
  }
  
  if (!entryPrice || entryPrice <= 0) {
    throw new Error('Entry price must be positive');
  }
  
  let priceDistance: number;
  
  switch (mode) {
    case 'pips':
      priceDistance = convertPipsToPrice(value, entryPrice, isBuy, digits);
      break;
      
    case 'points':
      priceDistance = convertPointsToPrice(value, entryPrice, tickSize);
      break;
      
    case 'percent':
      priceDistance = convertPercentToPrice(value, entryPrice);
      break;
      
    case 'price':
      // Already in absolute price, return as-is
      return value;
      
    default:
      throw new Error(`Unsupported risk unit mode: ${mode}`);
  }
  
  // Calculate absolute price based on direction
  // For buy orders:
  //   - Stop loss: entryPrice - priceDistance (below entry)
  //   - Take profit: entryPrice + priceDistance (above entry)
  // For sell orders:
  //   - Stop loss: entryPrice + priceDistance (above entry)
  //   - Take profit: entryPrice - priceDistance (below entry)
  
  let absolutePrice: number;
  
  if (isBuy) {
    absolutePrice = isStopLoss 
      ? entryPrice - priceDistance  // SL below entry
      : entryPrice + priceDistance; // TP above entry
  } else {
    absolutePrice = isStopLoss
      ? entryPrice + priceDistance  // SL above entry
      : entryPrice - priceDistance; // TP below entry
  }
  
  // Validate: price must be positive
  if (absolutePrice <= 0) {
    throw new Error(`Calculated price ${absolutePrice} is invalid (must be positive)`);
  }
  
  // Validate: SL must be on correct side of entry
  if (isStopLoss) {
    if (isBuy && absolutePrice >= entryPrice) {
      throw new Error(`Stop loss ${absolutePrice} must be below entry price ${entryPrice} for buy orders`);
    }
    if (!isBuy && absolutePrice <= entryPrice) {
      throw new Error(`Stop loss ${absolutePrice} must be above entry price ${entryPrice} for sell orders`);
    }
  }
  
  // Validate: TP must be on correct side of entry
  if (!isStopLoss) {
    if (isBuy && absolutePrice <= entryPrice) {
      throw new Error(`Take profit ${absolutePrice} must be above entry price ${entryPrice} for buy orders`);
    }
    if (!isBuy && absolutePrice >= entryPrice) {
      throw new Error(`Take profit ${absolutePrice} must be below entry price ${entryPrice} for sell orders`);
    }
  }
  
  return absolutePrice;
}

/**
 * Helper to get default tick size for a broker
 * 
 * @param broker - Broker type
 * @returns Default tick size
 */
export function getDefaultTickSize(broker: BrokerType): number {
  // Tradovate futures typically use 0.25 tick size
  // This should ideally come from contract specs, but we provide defaults
  switch (broker) {
    case 'tradovate':
      return 0.25;
    case 'projectx':
    case 'topstep':
      return 0.25; // Default for futures
    default:
      return 0.0001; // Default for forex (1 pip)
  }
}

/**
 * Helper to get default digits for a broker
 * 
 * @param broker - Broker type
 * @returns Default symbol precision
 */
export function getDefaultDigits(broker: BrokerType): number {
  // Most forex brokers use 5 digits (0.00001)
  // JPY pairs use 4 digits (0.01)
  // This should ideally come from symbol specs, but we provide defaults
  switch (broker) {
    case 'tradelocker':
    case 'mt4':
    case 'mt5':
    case 'truforex':
      return 5; // Standard forex precision
    default:
      return 5;
  }
}
