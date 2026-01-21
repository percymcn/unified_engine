'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  Signal,
  History,
  Activity,
  Key,
  Webhook,
  GitBranch,
  CreditCard,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Signals', href: '/signals', icon: Signal },
  { name: 'Trades', href: '/trades', icon: History },
];

const settingsNavigation = [
  { name: 'Accounts', href: '/settings/accounts', icon: Users },
  { name: 'Signal Routing', href: '/settings/routing', icon: GitBranch },
  { name: 'API Keys', href: '/settings/api-keys', icon: Key },
  { name: 'Webhooks', href: '/settings/webhooks', icon: Webhook },
  { name: 'Billing', href: '/settings/billing', icon: CreditCard },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();

  return (
    <div
      className={cn(
        'flex h-full w-64 flex-col border-r border-border bg-card',
        className
      )}
    >
      {/* Logo / App Name */}
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        <Activity className="h-6 w-6 text-primary" />
        <span className="text-lg font-semibold text-foreground">
          Tradeflow
        </span>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {/* Main Navigation */}
        {navigation.map((item) => {
          const fullHref = `/dashboard${item.href === '/' ? '' : item.href}`;
          // Improved active detection: exact match or nested route
          const isActive = item.href === '/'
            ? pathname === '/dashboard' || pathname === '/dashboard/'
            : pathname === fullHref || pathname.startsWith(fullHref + '/');
          return (
            <Link
              key={item.name}
              href={fullHref || '/dashboard'}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <item.icon className="h-5 w-5 pointer-events-none" />
              {item.name}
            </Link>
          );
        })}

        {/* Settings Section */}
        <div className="pt-4">
          <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Settings
          </p>
          {settingsNavigation.map((item) => {
            const fullHref = `/dashboard${item.href}`;
            // Active if exact match or nested route (e.g., /settings/accounts/edit)
            const isActive = pathname === fullHref || pathname.startsWith(fullHref + '/');
            return (
              <Link
                key={item.name}
                href={fullHref}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                <item.icon className="h-5 w-5 pointer-events-none" />
                {item.name}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-4">
        <p className="text-xs text-muted-foreground">
          Tradeflow v1.1
        </p>
      </div>
    </div>
  );
}
