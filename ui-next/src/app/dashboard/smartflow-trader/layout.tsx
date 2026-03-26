import type { ReactNode } from 'react';

interface SmartFlowTraderLayoutProps {
  children: ReactNode;
}

export default function SmartFlowTraderLayout({ children }: SmartFlowTraderLayoutProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold">SmartFlow Trader</h1>
        <p className="text-muted-foreground">
          Real-time performance, signals, and trade execution telemetry.
        </p>
      </div>
      {children}
    </div>
  );
}
