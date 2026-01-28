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
import { Signal, SignalStatus } from '@/types/signal';
import { SignalStatusBadge } from './signal-status-badge';
import { useWebSocketContext } from '@/providers/websocket-provider';
import { SignalUpdateData } from '@/types/websocket';
import { cn } from '@/lib/utils';

interface SignalsTableProps {
  signals: Signal[];
  onSignalUpdate?: (signal: Signal) => void;
}

export function SignalsTable({ signals, onSignalUpdate }: SignalsTableProps) {
  const { subscribeToSignals } = useWebSocketContext();
  const [localSignals, setLocalSignals] = useState<Signal[]>(signals);
  const [recentlyUpdated, setRecentlyUpdated] = useState<Set<number>>(new Set());

  // Sync props to local state
  useEffect(() => {
    setLocalSignals(signals);
  }, [signals]);

  // Handle WebSocket signal updates
  const handleSignalUpdate = useCallback(
    (data: SignalUpdateData) => {
      setLocalSignals((current) => {
        const index = current.findIndex(
          (s) => s.id === data.id || s.signal_id === data.signal_id
        );

        if (index >= 0) {
          // Update existing signal
          const updated = [...current];
          updated[index] = {
            ...updated[index],
            status: data.status as SignalStatus,
            ...(data.symbol && { symbol: data.symbol }),
            ...(data.action && { action: data.action }),
            ...(data.quantity && { quantity: data.quantity }),
            ...(data.price && { price: data.price }),
            ...(data.error_message && { error_message: data.error_message }),
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

          // Notify parent
          onSignalUpdate?.(updated[index]);

          return updated;
        } else {
          // New signal - add to beginning
          const newSignal: Signal = {
            id: data.id,
            signal_id: data.signal_id,
            symbol: data.symbol || '',
            action: data.action || '',
            quantity: data.quantity || 0,
            price: data.price,
            status: data.status as SignalStatus,
            error_message: data.error_message,
            created_at: new Date().toISOString(),
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

          onSignalUpdate?.(newSignal);

          return [newSignal, ...current];
        }
      });
    },
    [onSignalUpdate]
  );

  // Subscribe to WebSocket updates
  useEffect(() => {
    const unsubscribe = subscribeToSignals(handleSignalUpdate);
    return unsubscribe;
  }, [subscribeToSignals, handleSignalUpdate]);

  // Sort by created_at descending (newest first)
  const sortedSignals = [...localSignals].sort((a, b) => {
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

  // Get volume/quantity display value
  const getVolume = (signal: Signal) => {
    return signal.volume ?? signal.quantity ?? 0;
  };

  // Get execution results summary
  const getExecutionSummary = (signal: Signal) => {
    const results = signal.signal_data?.execution_results;
    if (!results) return null;
    return `${results.successful ?? 0}/${results.total_accounts ?? 0}`;
  };

  return (
    <div className="border border-border rounded-md overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Action</TableHead>
            <TableHead className="text-right">Volume</TableHead>
            <TableHead className="text-right">Price</TableHead>
            <TableHead className="text-right">SL</TableHead>
            <TableHead className="text-right">TP</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Execution</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Reason</TableHead>
            <TableHead>Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedSignals.map((signal) => (
            <TableRow
              key={signal.id}
              className={cn(
                'transition-colors duration-300',
                recentlyUpdated.has(signal.id) &&
                  'bg-primary/10 animate-pulse'
              )}
            >
              <TableCell className="font-medium">
                {signal.symbol}
                {recentlyUpdated.has(signal.id) && (
                  <span className="ml-2 text-xs text-primary font-medium">
                    NEW
                  </span>
                )}
              </TableCell>
              <TableCell>
                <span className={cn(
                  'uppercase font-medium',
                  signal.action?.toLowerCase() === 'buy' && 'text-green-500',
                  signal.action?.toLowerCase() === 'sell' && 'text-red-500'
                )}>
                  {signal.action}
                </span>
              </TableCell>
              <TableCell className="text-right font-mono">
                {getVolume(signal)}
              </TableCell>
              <TableCell className="text-right font-mono">
                {signal.price ? signal.price.toFixed(2) : '-'}
              </TableCell>
              <TableCell className="text-right font-mono text-red-400">
                {signal.stop_loss ? signal.stop_loss.toFixed(2) : '-'}
              </TableCell>
              <TableCell className="text-right font-mono text-green-400">
                {signal.take_profit ? signal.take_profit.toFixed(2) : '-'}
              </TableCell>
              <TableCell>
                <SignalStatusBadge status={signal.status} />
              </TableCell>
              <TableCell className="text-center">
                {getExecutionSummary(signal) ? (
                  <span className="text-xs font-mono">
                    {getExecutionSummary(signal)}
                  </span>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell className="text-xs">
                {signal.source || '-'}
              </TableCell>
              <TableCell className="text-xs max-w-[150px] truncate" title={signal.guard_reason || signal.error_message || ''}>
                {signal.guard_reason || signal.error_message || '-'}
              </TableCell>
              <TableCell className="text-xs whitespace-nowrap">
                {new Date(signal.created_at).toLocaleString()}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
