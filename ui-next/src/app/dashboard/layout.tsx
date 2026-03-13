'use client';

import { Sidebar } from '@/components/sidebar';
import { Header } from '@/components/header';
import { WebSocketProvider } from '@/providers/websocket-provider';
import { UserProvider } from '@/providers/user-provider';
import { TrialPromptWrapper } from '@/components/trial/trial-prompt-wrapper';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <WebSocketProvider>
      <UserProvider>
        <div className="flex h-screen bg-background">
          {/* Sidebar - hidden on mobile, visible on md+ */}
          <Sidebar className="hidden md:flex shrink-0 relative z-10" />

          {/* Main content area */}
          <div className="flex flex-1 flex-col min-h-0 overflow-hidden">
            {/* Header with mobile menu, theme toggle, and user nav */}
            <Header />

            {/* Page content - scrollable container */}
            <main className="flex-1 overflow-y-auto overflow-x-hidden">
              <div className="min-h-full p-3 sm:p-4 md:p-6 pb-20 md:pb-6">
                {/* Upgrade prompt when trial is low/expired */}
                <TrialPromptWrapper />
                {children}
              </div>
            </main>
          </div>
        </div>
      </UserProvider>
    </WebSocketProvider>
  );
}
