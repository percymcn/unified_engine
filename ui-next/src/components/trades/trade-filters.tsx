'use client';

import { DateRange } from 'react-day-picker';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { TradeFilters as TradeFiltersType, TradeStatus } from '@/types/trade';
import { X } from 'lucide-react';

interface TradeFiltersProps {
  filters: TradeFiltersType;
  onFiltersChange: (filters: TradeFiltersType) => void;
}

const BROKER_OPTIONS = [
  { value: 'all', label: 'All Brokers' },
  { value: 'mt4', label: 'MetaTrader 4' },
  { value: 'mt5', label: 'MetaTrader 5' },
  { value: 'tradelocker', label: 'TradeLocker' },
  { value: 'tradovate', label: 'Tradovate' },
  { value: 'projectx', label: 'TopStep' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'closed', label: 'Closed' },
  { value: 'pending', label: 'Pending' },
  { value: 'cancelled', label: 'Cancelled' },
];

export function TradeFilters({ filters, onFiltersChange }: TradeFiltersProps) {
  const handleDateRangeChange = (range: DateRange | undefined) => {
    onFiltersChange({
      ...filters,
      dateFrom: range?.from?.toISOString().split('T')[0],
      dateTo: range?.to?.toISOString().split('T')[0],
    });
  };

  const handleBrokerChange = (value: string) => {
    onFiltersChange({
      ...filters,
      broker: value === 'all' ? undefined : value,
    });
  };

  const handleStatusChange = (value: string) => {
    onFiltersChange({
      ...filters,
      status: value as TradeStatus | 'all',
    });
  };

  const handleReset = () => {
    onFiltersChange({});
  };

  const hasActiveFilters =
    filters.dateFrom ||
    filters.dateTo ||
    filters.broker ||
    (filters.status && filters.status !== 'all');

  // Convert string dates back to DateRange for the picker
  const dateRange: DateRange | undefined =
    filters.dateFrom || filters.dateTo
      ? {
          from: filters.dateFrom ? new Date(filters.dateFrom) : undefined,
          to: filters.dateTo ? new Date(filters.dateTo) : undefined,
        }
      : undefined;

  return (
    <div className="flex flex-wrap items-center gap-4">
      <DateRangePicker value={dateRange} onChange={handleDateRangeChange} />

      <Select
        value={filters.broker || 'all'}
        onValueChange={handleBrokerChange}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Select broker" />
        </SelectTrigger>
        <SelectContent>
          {BROKER_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.status || 'all'}
        onValueChange={handleStatusChange}
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="Select status" />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={handleReset}>
          <X className="h-4 w-4 mr-1" />
          Reset
        </Button>
      )}
    </div>
  );
}
