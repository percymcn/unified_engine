import { Sidebar } from '@/components/sidebar';
import { Header } from '@/components/header';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  // Note: User info can be fetched server-side and passed to Header
  // For now, Header will use placeholder until we implement user context

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar - hidden on mobile, visible on md+ */}
      <Sidebar className="hidden md:flex" />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header with mobile menu and user nav */}
        <Header />

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
