import { Badge } from '@/components/ui/badge';
import { TradeStatus } from '@/types/trade';

interface TradeStatusBadgeProps {
  status: TradeStatus;
  profitLoss?: number;
}

export function TradeStatusBadge({ status, profitLoss }: TradeStatusBadgeProps) {
  // For closed trades, use profit/loss to determine color
  if (status === 'closed' && profitLoss !== undefined) {
    const isProfit = profitLoss > 0;
    const className = isProfit
      ? 'bg-green-600 text-white hover:bg-green-700'
      : 'bg-red-600 text-white hover:bg-red-700';

    return (
      <Badge variant="default" className={className}>
        Closed
      </Badge>
    );
  }

  // For open trades, use yellow/warning color
  if (status === 'open') {
    return (
      <Badge variant="default" className="bg-yellow-600 text-white hover:bg-yellow-700">
        Open
      </Badge>
    );
  }

  // For pending and cancelled, use gray
  const config: Record<TradeStatus, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
    pending: { label: 'Pending', variant: 'secondary' },
    cancelled: { label: 'Cancelled', variant: 'outline' },
    open: { label: 'Open', variant: 'default' }, // Won't reach here
    closed: { label: 'Closed', variant: 'default' }, // Won't reach here
  };

  const statusConfig = config[status];

  return (
    <Badge variant={statusConfig.variant}>
      {statusConfig.label}
    </Badge>
  );
}
