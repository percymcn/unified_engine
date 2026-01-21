'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from '@/components/ui/sheet';
import { UserNav } from '@/components/user-nav';
import { Sidebar } from '@/components/sidebar';
import { ConnectionStatusIndicator } from '@/components/connection-status';

interface HeaderProps {
  user?: {
    email?: string;
    name?: string;
  };
}

export function Header({ user }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  // Close mobile menu when pathname changes (navigation occurred)
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-4 md:px-6">
      {/* Mobile menu button - only visible on mobile */}
      <div className="md:hidden">
        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Open menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <Sidebar className="border-r-0" />
          </SheetContent>
        </Sheet>
      </div>

      {/* Page title area - can be used for breadcrumbs later */}
      <div className="hidden md:block">
        {/* Empty for now - dashboard pages can add their own title */}
      </div>

      {/* Right side actions */}
      <div className="ml-auto flex items-center gap-4">
        {/* WebSocket connection status indicator */}
        <ConnectionStatusIndicator />

        {/* User navigation */}
        <UserNav user={user} />
      </div>
    </header>
  );
}
