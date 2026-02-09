'use client';

import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// Telegram support group/bot - can be configured in environment
const TELEGRAM_SUPPORT_LINK = process.env.NEXT_PUBLIC_TELEGRAM_SUPPORT_LINK || 'https://t.me/tradeflowsupport';

interface TelegramSupportButtonProps {
  className?: string;
  variant?: 'floating' | 'inline';
}

export function TelegramSupportButton({
  className,
  variant = 'floating'
}: TelegramSupportButtonProps) {
  const handleClick = () => {
    window.open(TELEGRAM_SUPPORT_LINK, '_blank', 'noopener,noreferrer');
  };

  if (variant === 'inline') {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={handleClick}
        className={cn('gap-2', className)}
      >
        <TelegramIcon className="h-4 w-4" />
        Telegram Support
      </Button>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size="icon"
            onClick={handleClick}
            className={cn(
              'fixed bottom-36 right-4 z-40 h-12 w-12 rounded-full shadow-lg',
              'bg-[#0088cc]/10 border-[#0088cc]/30 hover:bg-[#0088cc]/20',
              'transition-all hover:scale-110',
              className
            )}
          >
            <TelegramIcon className="h-6 w-6 text-[#0088cc]" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="left">
          <p>Quick Telegram Support</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Telegram SVG Icon
function TelegramIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
    >
      <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
    </svg>
  );
}

export { TelegramIcon };
