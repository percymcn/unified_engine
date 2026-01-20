import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { BrokerType } from '@/types/broker';
import { cn } from '@/lib/utils';

interface BrokerHealthCardProps {
  name: BrokerType;
  connected: boolean;
  loading?: boolean;
  recentlyChanged?: boolean;
}

// Map broker type to friendly display name
const BROKER_DISPLAY_NAMES: Record<BrokerType, string> = {
  mt4: 'MetaTrader 4',
  mt5: 'MetaTrader 5',
  tradelocker: 'TradeLocker',
  tradovate: 'Tradovate',
  projectx: 'TopStep',
};

export function BrokerHealthCard({
  name,
  connected,
  loading = false,
  recentlyChanged = false,
}: BrokerHealthCardProps) {
  const displayName = BROKER_DISPLAY_NAMES[name];

  return (
    <Card
      className={cn(
        'transition-all duration-300',
        recentlyChanged && 'ring-2 ring-primary animate-pulse'
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{displayName}</CardTitle>
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : connected ? (
          <CheckCircle2 className="h-4 w-4 text-chart-2" />
        ) : (
          <XCircle className="h-4 w-4 text-destructive" />
        )}
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${connected ? 'text-chart-2' : 'text-muted-foreground'}`}>
          {loading ? '...' : connected ? 'Connected' : 'Disconnected'}
        </div>
        <p className="text-xs text-muted-foreground">
          {loading ? 'Checking status...' : connected ? 'Broker online' : 'Broker offline'}
        </p>
      </CardContent>
    </Card>
  );
}
