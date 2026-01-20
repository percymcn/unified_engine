'use client';

import { CheckCircle2, XCircle } from 'lucide-react';
import { CopyButton } from '@/components/ui/copy-button';
import { cn } from '@/lib/utils';

interface WebhookUrlDisplayProps {
  url: string;
  isConfigured?: boolean;
  className?: string;
}

export function WebhookUrlDisplay({ url, isConfigured, className }: WebhookUrlDisplayProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex-1 rounded-md bg-muted px-4 py-3 font-mono text-sm break-all">
        {url}
      </div>
      <CopyButton text={url} tooltip="Copy webhook URL" />
      {isConfigured !== undefined && (
        <div className="flex items-center gap-1 text-sm">
          {isConfigured ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span className="text-green-600">Configured</span>
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Not configured</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
