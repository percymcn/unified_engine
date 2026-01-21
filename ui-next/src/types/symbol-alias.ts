/**
 * Symbol Alias Types
 *
 * TypeScript types for symbol alias management.
 * Maps TradingView symbols to broker-specific formats.
 */

/**
 * A single symbol alias mapping.
 */
export interface SymbolAlias {
  id: number;
  sourceSymbol: string;
  brokerType: string;
  targetSymbol: string;
  isAutoDetected: boolean;
  createdAt: string;
}

/**
 * Symbol aliases grouped by broker.
 */
export interface SymbolAliasGroup {
  brokerType: string;
  brokerName: string;
  aliases: SymbolAlias[];
}

/**
 * Request to create a new symbol alias.
 */
export interface CreateSymbolAliasRequest {
  sourceSymbol: string;
  brokerType: string;
  targetSymbol: string;
}

/**
 * Request to update an existing symbol alias.
 */
export interface UpdateSymbolAliasRequest {
  targetSymbol: string;
}
