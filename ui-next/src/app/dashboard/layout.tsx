'use client';

import { Sidebar } from '@/components/sidebar';
import { Header } from '@/components/header';
import { WebSocketProvider } from '@/providers/websocket-provider';
import { UserProvider } from '@/providers/user-provider';

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
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Header with mobile menu, theme toggle, and user nav */}
            <Header />

            {/* Page content */}
            <main className="flex-1 overflow-auto p-6">{children}</main>
          </div>
        </div>
      </UserProvider>
    </WebSocketProvider>
  );
}
