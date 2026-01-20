'use client';

import { useWebSocketContext } from '@/providers/websocket-provider';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { ConnectionStatus } from '@/types/websocket';

// Status indicator colors
const STATUS_COLORS: Record<ConnectionStatus, string> = {
  connected: 'bg-green-500',
  connecting: 'bg-yellow-500 animate-pulse',
  disconnected: 'bg-red-500',
  error: 'bg-red-500',
};

// Status display text
const STATUS_TEXT: Record<ConnectionStatus, string> = {
  connected: 'Connected',
  connecting: 'Connecting...',
  disconnected: 'Disconnected',
  error: 'Error',
};

// Status descriptions
const STATUS_DESCRIPTION: Record<ConnectionStatus, string> = {
  connected: 'Real-time updates are active',
  connecting: 'Establishing connection...',
  disconnected: 'No connection to server',
  error: 'Connection error occurred',
};

export function ConnectionStatusIndicator() {
  const { status, reconnectAttempts, connect } = useWebSocketContext();

  const handleClick = () => {
    if (status === 'disconnected' || status === 'error') {
      connect();
    }
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={handleClick}
            className={cn(
              'flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
              status === 'connected' && 'bg-green-500/10 text-green-500 hover:bg-green-500/20',
              status === 'connecting' && 'bg-yellow-500/10 text-yellow-500',
              (status === 'disconnected' || status === 'error') &&
                'bg-red-500/10 text-red-500 hover:bg-red-500/20 cursor-pointer'
            )}
          >
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                STATUS_COLORS[status]
              )}
            />
            <span className="hidden sm:inline">{STATUS_TEXT[status]}</span>
          </button>
        </TooltipTrigger>
        <TooltipContent>
          <div className="text-sm">
            <p className="font-medium">{STATUS_TEXT[status]}</p>
            <p className="text-muted-foreground">{STATUS_DESCRIPTION[status]}</p>
            {reconnectAttempts > 0 && status !== 'connected' && (
              <p className="text-muted-foreground mt-1">
                Reconnect attempts: {reconnectAttempts}
              </p>
            )}
            {(status === 'disconnected' || status === 'error') && (
              <p className="text-primary mt-1">Click to reconnect</p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
