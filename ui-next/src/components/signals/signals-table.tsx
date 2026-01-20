'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Signal } from '@/types/signal';
import { SignalStatusBadge } from './signal-status-badge';

interface SignalsTableProps {
  signals: Signal[];
}

export function SignalsTable({ signals }: SignalsTableProps) {
  // Sort by created_at descending (newest first)
  const sortedSignals = [...signals].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  if (sortedSignals.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 border border-border rounded-md">
        <div className="text-center">
          <p className="text-muted-foreground">No signals found</p>
          <p className="text-sm text-muted-foreground mt-1">
            Signals will appear here when received
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-border rounded-md">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Action</TableHead>
            <TableHead className="text-right">Quantity</TableHead>
            <TableHead className="text-right">Price</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedSignals.map((signal) => (
            <TableRow key={signal.id}>
              <TableCell className="font-medium">{signal.symbol}</TableCell>
              <TableCell className="uppercase">{signal.action}</TableCell>
              <TableCell className="text-right">{signal.quantity}</TableCell>
              <TableCell className="text-right">
                {signal.price ? signal.price.toFixed(2) : '-'}
              </TableCell>
              <TableCell>
                <SignalStatusBadge status={signal.status} />
              </TableCell>
              <TableCell>{signal.source || '-'}</TableCell>
              <TableCell>
                {new Date(signal.created_at).toLocaleString()}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
