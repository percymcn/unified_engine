'use client';

import { AlertTriangle, Clock, CalendarClock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export interface FuturesInfo {
  contractCode: string;
  symbolRoot: string;
  expirationDate: string;
  rolloverDate: string;
  nextContract: string | null;
  daysUntilExpiration: number;
}

interface ExpirationBadgeProps {
  contract: FuturesInfo;
  showTooltip?: boolean;
  className?: string;
}

/**
 * Badge showing futures contract expiration status.
 *
 * Shows warning indicators when contracts are expiring soon:
 * - Red (destructive): 3 days or less
 * - Amber (warning): 4-7 days
 * - Hidden: more than 7 days
 */
export function ExpirationBadge({
  contract,
  showTooltip = true,
  className,
}: ExpirationBadgeProps) {
  const { daysUntilExpiration, contractCode, nextContract } = contract;

  // Don't show badge if more than 7 days out
  if (daysUntilExpiration > 7) {
    return null;
  }

  // Determine variant and icon based on urgency
  const isCritical = daysUntilExpiration <= 3;
  const Icon = isCritical ? AlertTriangle : Clock;

  // Format expiration text
  const expirationText =
    daysUntilExpiration <= 0
      ? 'Expires today!'
      : daysUntilExpiration === 1
      ? 'Expires tomorrow'
      : `Expires in ${daysUntilExpiration} days`;

  const badge = (
    <Badge
      variant={isCritical ? 'destructive' : 'outline'}
      className={cn(
        'gap-1',
        !isCritical && 'border-amber-500 text-amber-600 dark:text-amber-400',
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {expirationText}
    </Badge>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <div className="space-y-1">
            <p className="font-semibold">{contractCode} Expiring</p>
            <p className="text-sm text-muted-foreground">
              This futures contract expires on{' '}
              {new Date(contract.expirationDate).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </p>
            {nextContract && (
              <p className="text-sm">
                <span className="text-muted-foreground">Roll to: </span>
                <span className="font-medium">{nextContract}</span>
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface ExpirationAlertProps {
  alerts: FuturesInfo[];
  onRollover?: (contract: FuturesInfo) => void;
}

/**
 * Dashboard card showing contract expiration alerts.
 *
 * Displays all contracts expiring within 7 days with
 * rollover suggestions.
 */
export function ExpirationAlerts({ alerts, onRollover }: ExpirationAlertProps) {
  if (!alerts || alerts.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div
          key={`${alert.contractCode}-${alert.expirationDate}`}
          className={cn(
            'flex items-center justify-between p-3 rounded-lg border',
            alert.daysUntilExpiration <= 3
              ? 'border-destructive/50 bg-destructive/10'
              : 'border-amber-500/50 bg-amber-50 dark:bg-amber-950/20'
          )}
        >
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'p-2 rounded-full',
                alert.daysUntilExpiration <= 3
                  ? 'bg-destructive/20'
                  : 'bg-amber-500/20'
              )}
            >
              <CalendarClock
                className={cn(
                  'h-4 w-4',
                  alert.daysUntilExpiration <= 3
                    ? 'text-destructive'
                    : 'text-amber-600 dark:text-amber-400'
                )}
              />
            </div>
            <div>
              <p className="font-medium">{alert.contractCode}</p>
              <p className="text-sm text-muted-foreground">
                Expires{' '}
                {new Date(alert.expirationDate).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                })}
                {' '}
                ({alert.daysUntilExpiration <= 0
                  ? 'today'
                  : `in ${alert.daysUntilExpiration} day${alert.daysUntilExpiration !== 1 ? 's' : ''}`})
              </p>
            </div>
          </div>
          {alert.nextContract && onRollover && (
            <button
              onClick={() => onRollover(alert)}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                'border hover:bg-accent',
                alert.daysUntilExpiration <= 3
                  ? 'border-destructive text-destructive hover:bg-destructive/10'
                  : 'border-amber-500 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10'
              )}
            >
              Roll to {alert.nextContract}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

/**
 * Compact list of expiring contracts for sidebar/summary views.
 */
export function ExpirationList({ contracts }: { contracts: FuturesInfo[] }) {
  const expiring = contracts.filter((c) => c.daysUntilExpiration <= 7);

  if (expiring.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
        <AlertTriangle className="h-3 w-3" />
        Expiring Contracts ({expiring.length})
      </h4>
      <ul className="space-y-1">
        {expiring.map((contract) => (
          <li
            key={contract.contractCode}
            className="flex items-center justify-between text-sm"
          >
            <span className="font-mono">{contract.contractCode}</span>
            <ExpirationBadge contract={contract} showTooltip={false} />
          </li>
        ))}
      </ul>
    </div>
  );
}
