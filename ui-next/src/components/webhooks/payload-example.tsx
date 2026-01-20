'use client';

import { CopyButton } from '@/components/ui/copy-button';

interface PayloadExampleProps {
  payload: Record<string, unknown>;
}

export function PayloadExample({ payload }: PayloadExampleProps) {
  const formattedPayload = JSON.stringify(payload, null, 2);

  return (
    <div className="relative">
      <div className="absolute top-2 right-2 z-10">
        <CopyButton text={formattedPayload} tooltip="Copy payload" />
      </div>
      <pre className="rounded-md bg-muted p-4 overflow-x-auto text-sm">
        <code className="language-json">{formattedPayload}</code>
      </pre>
    </div>
  );
}
