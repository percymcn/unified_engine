import { Badge } from '@/components/ui/badge';
import { SignalStatus } from '@/types/signal';

const statusConfig: Record<SignalStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: { label: 'Pending', variant: 'secondary' },
  processing: { label: 'Processing', variant: 'default' },
  executed: { label: 'Executed', variant: 'default' }, // Will use green styling
  cancelled: { label: 'Cancelled', variant: 'outline' },
  failed: { label: 'Failed', variant: 'destructive' },
};

export function SignalStatusBadge({ status }: { status: SignalStatus }) {
  const config = statusConfig[status] || statusConfig.pending;
  // Custom green for executed
  const className = status === 'executed' ? 'bg-green-600 text-white hover:bg-green-700' : '';

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  );
}
