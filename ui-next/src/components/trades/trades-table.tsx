'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Trade } from '@/types/trade';
import { TradeStatusBadge } from './trade-status-badge';

interface TradesTableProps {
  trades: Trade[];
}

const BROKER_NAMES: Record<string, string> = {
  mt4: 'MetaTrader 4',
  mt5: 'MetaTrader 5',
  tradelocker: 'TradeLocker',
  tradovate: 'Tradovate',
  projectx: 'TopStep',
};

export function TradesTable({ trades }: TradesTableProps) {
  // Sort by opened_at descending (newest first)
  const sortedTrades = [...trades].sort((a, b) => {
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

  return (
    <div className="border border-border rounded-md">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Side</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead className="text-right">Entry</TableHead>
            <TableHead className="text-right">Exit</TableHead>
            <TableHead className="text-right">P/L</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Broker</TableHead>
            <TableHead>Opened</TableHead>
            <TableHead>Closed</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedTrades.map((trade) => (
            <TableRow key={trade.id}>
              <TableCell className="font-medium">{trade.symbol}</TableCell>
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
              <TableCell className="text-right">
                {formatPrice(trade.exit_price)}
              </TableCell>
              <TableCell
                className={`text-right font-medium ${getPnlClass(trade.profit_loss)}`}
              >
                {formatProfitLoss(trade.profit_loss)}
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
