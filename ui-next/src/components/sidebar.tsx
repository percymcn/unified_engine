'use client';

import Link from 'next/link';
import Image from 'next/image';
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
  ArrowRightLeft,
  FolderOpen,
  Shield,
  Settings2,
  UserCircle,
  Wrench,
  Crown,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUser } from '@/providers/user-provider';
import { Badge } from '@/components/ui/badge';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Signals', href: '/signals', icon: Signal },
  { name: 'Trades', href: '/trades', icon: History },
];

const settingsNavigation = [
  { name: 'Profile', href: '/settings/profile', icon: UserCircle },
  { name: 'Accounts', href: '/settings/accounts', icon: Users },
  { name: 'Account Groups', href: '/settings/groups', icon: FolderOpen },
  { name: 'Symbol Mapping', href: '/settings/symbols', icon: ArrowRightLeft },
  { name: 'Signal Routing', href: '/settings/routing', icon: GitBranch },
  { name: 'Broker Tools', href: '/settings/broker-tools', icon: Wrench },
  { name: 'Risk Management', href: '/settings/risk', icon: Shield },
  { name: 'Preferences', href: '/settings/preferences', icon: Settings2 },
  { name: 'API Keys', href: '/settings/api-keys', icon: Key },
  { name: 'Webhooks', href: '/settings/webhooks', icon: Webhook },
  { name: 'Webhook Logs', href: '/settings/webhook-logs', icon: History },
  { name: 'Billing', href: '/settings/billing', icon: CreditCard },
  { name: 'Help & Support', href: '/settings/help', icon: HelpCircle },
];

interface SidebarProps {
  className?: string;
}

// Helper to get tier display info
function getTierDisplay(tier: string): { name: string; color: string; icon: typeof Crown } {
  const t = tier?.toLowerCase() || 'free';
  switch (t) {
    case 'enterprise':
    case 'tier_4':
      return { name: 'Enterprise', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30', icon: Crown };
    case 'pro':
    case 'tier_3':
      return { name: 'Pro', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Crown };
    case 'trader':
    case 'tier_2':
      return { name: 'Trader', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: Sparkles };
    case 'starter':
    case 'tier_1':
      return { name: 'Starter', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: Sparkles };
    default:
      return { name: 'Free', color: 'bg-muted text-muted-foreground', icon: Sparkles };
  }
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useUser();
  const tierDisplay = getTierDisplay(user?.subscription_tier || 'free');
  const TierIcon = tierDisplay.icon;

  return (
    <div
      className={cn(
        'flex h-full w-64 flex-col border-r border-border bg-card',
        className
      )}
    >
      {/* Logo / App Name */}
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        <Image
          src="/logo.png"
          alt="Tradeflow"
          width={28}
          height={28}
          className="rounded-md"
        />
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

      {/* Subscription Status */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-2 mb-2">
          <TierIcon className="h-4 w-4" />
          <span className="text-sm font-medium">Your Plan</span>
        </div>
        <Badge variant="outline" className={cn("text-xs", tierDisplay.color)}>
          {tierDisplay.name}
        </Badge>
        <p className="text-xs text-muted-foreground mt-2">
          Tradeflow v1.1
        </p>
      </div>
    </div>
  );
}
