import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react';
import { BrokerType, ConnectionStatus } from '@/types/broker';
import { cn } from '@/lib/utils';

interface BrokerHealthCardProps {
  name: BrokerType;
  connected: boolean;
  /** Three-state status: connected (green), connecting (amber), disconnected (red) */
  status?: ConnectionStatus;
  loading?: boolean;
  recentlyChanged?: boolean;
  error?: string;
}

// Map broker type to friendly display name
const BROKER_DISPLAY_NAMES: Record<BrokerType, string> = {
  mt4: 'MetaTrader 4',
  mt5: 'MetaTrader 5',
  tradelocker: 'TradeLocker',
  tradovate: 'Tradovate',
  projectx: 'TopStep',
};

// Status configuration for three-state indicators
const STATUS_CONFIG: Record<ConnectionStatus, {
  icon: typeof CheckCircle2;
  iconClass: string;
  textClass: string;
  label: string;
  subtext: string;
}> = {
  connected: {
    icon: CheckCircle2,
    iconClass: 'text-chart-2',
    textClass: 'text-chart-2',
    label: 'Connected',
    subtext: 'Broker online',
  },
  connecting: {
    icon: AlertCircle,
    iconClass: 'text-amber-500',
    textClass: 'text-amber-500',
    label: 'Connecting...',
    subtext: 'Checking connection...',
  },
  disconnected: {
    icon: XCircle,
    iconClass: 'text-destructive',
    textClass: 'text-muted-foreground',
    label: 'Disconnected',
    subtext: 'Broker offline',
  },
};

export function BrokerHealthCard({
  name,
  connected,
  status,
  loading = false,
  recentlyChanged = false,
  error,
}: BrokerHealthCardProps) {
  const displayName = BROKER_DISPLAY_NAMES[name];

  // Determine effective status: explicit status > loading state > connected boolean
  const effectiveStatus: ConnectionStatus = loading
    ? 'connecting'
    : status ?? (connected ? 'connected' : 'disconnected');

  const config = STATUS_CONFIG[effectiveStatus];
  const StatusIcon = loading ? Loader2 : config.icon;

  return (
    <Card
      className={cn(
        'transition-all duration-300',
        recentlyChanged && 'ring-2 ring-primary animate-pulse'
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{displayName}</CardTitle>
        <StatusIcon
          className={cn(
            'h-4 w-4',
            loading ? 'animate-spin text-amber-500' : config.iconClass
          )}
        />
      </CardHeader>
      <CardContent>
        <div className={cn('text-2xl font-bold', config.textClass)}>
          {config.label}
        </div>
        <p className="text-xs text-muted-foreground">
          {error || config.subtext}
        </p>
      </CardContent>
    </Card>
  );
}
