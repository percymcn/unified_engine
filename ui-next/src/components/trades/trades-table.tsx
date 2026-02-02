'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Trade, TradeStatus, CloseReason } from '@/types/trade';
import { TradeStatusBadge } from './trade-status-badge';
import { useWebSocketContext } from '@/providers/websocket-provider';
import { OrderUpdateData, PositionUpdateData } from '@/types/websocket';
import { cn } from '@/lib/utils';

interface TradesTableProps {
  trades: Trade[];
  onTradeUpdate?: (trade: Trade) => void;
}

const BROKER_NAMES: Record<string, string> = {
  mt4: 'MetaTrader 4',
  mt5: 'MetaTrader 5',
  tradelocker: 'TradeLocker',
  tradovate: 'Tradovate',
  projectx: 'TopStep',
};

// Map order status to trade status
const ORDER_STATUS_MAP: Record<string, TradeStatus> = {
  pending: 'pending',
  open: 'open',
  filled: 'open',
  partial: 'open',
  closed: 'closed',
  cancelled: 'cancelled',
  rejected: 'cancelled',
};

export function TradesTable({ trades, onTradeUpdate }: TradesTableProps) {
  const { subscribeToOrders, subscribeToPositions } = useWebSocketContext();
  const [localTrades, setLocalTrades] = useState<Trade[]>(trades);
  const [recentlyUpdated, setRecentlyUpdated] = useState<Set<number>>(new Set());

  // Sync props to local state
  useEffect(() => {
    setLocalTrades(trades);
  }, [trades]);

  // Handle WebSocket order updates
  const handleOrderUpdate = useCallback(
    (data: OrderUpdateData) => {
      setLocalTrades((current) => {
        const index = current.findIndex(
          (t) => t.id === data.id
        );

        if (index >= 0) {
          // Update existing trade
          const updated = [...current];
          const tradeStatus = ORDER_STATUS_MAP[data.status.toLowerCase()] || 'open';

          updated[index] = {
            ...updated[index],
            status: tradeStatus,
            quantity: data.quantity,
            ...(data.price && { entry_price: data.price }),
            ...(data.filled_quantity && { quantity: data.filled_quantity }),
          };

          // Mark as recently updated
          setRecentlyUpdated((prev) => new Set(prev).add(data.id));
          setTimeout(() => {
            setRecentlyUpdated((prev) => {
              const next = new Set(prev);
              next.delete(data.id);
              return next;
            });
          }, 3000);

          onTradeUpdate?.(updated[index]);
          return updated;
        } else {
          // New trade from order - add to beginning
          const newTrade: Trade = {
            id: data.id,
            symbol: data.symbol,
            side: data.side,
            quantity: data.filled_quantity || data.quantity,
            entry_price: data.price || 0,
            status: ORDER_STATUS_MAP[data.status.toLowerCase()] || 'open',
            broker: data.broker,
            account_id: 0, // Will be populated by backend
            opened_at: new Date().toISOString(),
          };

          // Mark as recently updated
          setRecentlyUpdated((prev) => new Set(prev).add(data.id));
          setTimeout(() => {
            setRecentlyUpdated((prev) => {
              const next = new Set(prev);
              next.delete(data.id);
              return next;
            });
          }, 3000);

          onTradeUpdate?.(newTrade);
          return [newTrade, ...current];
        }
      });
    },
    [onTradeUpdate]
  );

  // Handle WebSocket position updates (for P/L and exits)
  const handlePositionUpdate = useCallback(
    (data: PositionUpdateData) => {
      setLocalTrades((current) => {
        const index = current.findIndex(
          (t) => t.symbol === data.symbol && t.broker.toLowerCase() === data.broker.toLowerCase()
        );

        if (index >= 0) {
          // Update existing trade with position data
          const updated = [...current];
          updated[index] = {
            ...updated[index],
            ...(data.current_price && { exit_price: data.current_price }),
            ...(data.unrealized_pnl !== undefined && { profit_loss: data.unrealized_pnl }),
          };

          // Mark as recently updated
          setRecentlyUpdated((prev) => new Set(prev).add(updated[index].id));
          setTimeout(() => {
            setRecentlyUpdated((prev) => {
              const next = new Set(prev);
              next.delete(updated[index].id);
              return next;
            });
          }, 3000);

          onTradeUpdate?.(updated[index]);
          return updated;
        }

        return current;
      });
    },
    [onTradeUpdate]
  );

  // Subscribe to WebSocket updates
  useEffect(() => {
    const unsubscribeOrders = subscribeToOrders(handleOrderUpdate);
    const unsubscribePositions = subscribeToPositions(handlePositionUpdate);
    return () => {
      unsubscribeOrders();
      unsubscribePositions();
    };
  }, [subscribeToOrders, subscribeToPositions, handleOrderUpdate, handlePositionUpdate]);

  // Sort by opened_at descending (newest first)
  const sortedTrades = [...localTrades].sort((a, b) => {
    return new Date(b.opened_at).getTime() - new Date(a.opened_at).getTime();
  });

  if (sortedTrades.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 border border-border rounded-md">
        <div className="text-center">
          <p className="text-muted-foreground">No trades found</p>
          <p className="text-sm text-muted-foreground mt-1">
            Trades will appear here when executed
          </p>
        </div>
      </div>
    );
  }

  const formatPrice = (price: number | undefined) => {
    if (price === undefined || price === null) return '-';
    return price.toFixed(2);
  };

  const formatProfitLoss = (pnl: number | undefined) => {
    if (pnl === undefined || pnl === null) return '-';
    const formatted = pnl.toFixed(2);
    return pnl >= 0 ? `+$${formatted}` : `-$${Math.abs(pnl).toFixed(2)}`;
  };

  const getPnlClass = (pnl: number | undefined) => {
    if (pnl === undefined || pnl === null) return '';
    return pnl >= 0 ? 'text-green-500' : 'text-red-500';
  };

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  const getBrokerName = (broker: string) => {
    return BROKER_NAMES[broker.toLowerCase()] || broker;
  };

  const formatCloseReason = (reason: CloseReason | undefined) => {
    if (!reason) return '-';
    const labels: Record<CloseReason, string> = {
      stop_loss: 'SL Hit',
      take_profit: 'TP Hit',
      trailing_stop: 'Trail SL',
      manual: 'Manual',
      signal: 'Signal',
      margin_call: 'Margin',
    };
    return labels[reason] || reason;
  };

  const getCloseReasonClass = (reason: CloseReason | undefined) => {
    if (!reason) return '';
    switch (reason) {
      case 'stop_loss':
      case 'margin_call':
        return 'text-red-500';
      case 'take_profit':
        return 'text-green-500';
      case 'trailing_stop':
        return 'text-amber-500';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="border border-border rounded-md overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Side</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead className="text-right">Entry</TableHead>
            <TableHead className="text-right">SL</TableHead>
            <TableHead className="text-right">TP</TableHead>
            <TableHead className="text-right">Exit</TableHead>
            <TableHead className="text-right">P/L</TableHead>
            <TableHead>Close Reason</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Broker</TableHead>
            <TableHead>Opened</TableHead>
            <TableHead>Closed</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedTrades.map((trade) => (
            <TableRow
              key={trade.id}
              className={cn(
                'transition-colors duration-300',
                recentlyUpdated.has(trade.id) &&
                  'bg-primary/10 animate-pulse'
              )}
            >
              <TableCell className="font-medium">
                {trade.symbol}
                {recentlyUpdated.has(trade.id) && (
                  <span className="ml-2 text-xs text-primary font-medium">
                    LIVE
                  </span>
                )}
              </TableCell>
              <TableCell
                className={`uppercase font-medium ${
                  trade.side === 'buy' ? 'text-green-500' : 'text-red-500'
                }`}
              >
                {trade.side}
              </TableCell>
              <TableCell className="text-right">{trade.quantity}</TableCell>
              <TableCell className="text-right">
                {formatPrice(trade.entry_price)}
              </TableCell>
              <TableCell className="text-right text-red-400">
                {formatPrice(trade.stop_loss)}
              </TableCell>
              <TableCell className="text-right text-green-400">
                {formatPrice(trade.take_profit)}
              </TableCell>
              <TableCell className="text-right">
                {formatPrice(trade.exit_price)}
              </TableCell>
              <TableCell
                className={`text-right font-medium ${getPnlClass(trade.profit_loss)}`}
              >
                {formatProfitLoss(trade.profit_loss)}
                {trade.profit_loss_pct !== undefined && trade.profit_loss_pct !== null && (
                  <span className="text-xs ml-1 text-muted-foreground">
                    ({trade.profit_loss_pct >= 0 ? '+' : ''}{trade.profit_loss_pct.toFixed(1)}%)
                  </span>
                )}
              </TableCell>
              <TableCell className={getCloseReasonClass(trade.close_reason)}>
                {formatCloseReason(trade.close_reason)}
              </TableCell>
              <TableCell>
                <TradeStatusBadge
                  status={trade.status}
                  profitLoss={trade.profit_loss}
                />
              </TableCell>
              <TableCell>{getBrokerName(trade.broker)}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(trade.opened_at)}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(trade.closed_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
