'use client';

import * as React from 'react';
import { ThemeProvider as NextThemesProvider, useTheme as useNextTheme } from 'next-themes';
import { type ThemeProviderProps } from 'next-themes';
import { usePathname } from 'next/navigation';

// Re-export useTheme for dashboard components
export { useTheme } from 'next-themes';

// Public routes that should always be dark (no user theme)
const PUBLIC_ROUTES = ['/', '/about', '/blog', '/contact', '/pricing', '/privacy', '/terms', '/login', '/register', '/resend-verification', '/verify-email'];

/**
 * Theme Provider with Dashboard-Only Isolation (Patch 1.2.2)
 *
 * Theme applies ONLY to authenticated dashboard routes (/dashboard/*).
 * Public/landing pages always remain dark and ignore user theme preferences.
 * Theme is stored per-user in the database via /api/users/me/preferences.
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  const pathname = usePathname();

  // Check if we're on a dashboard/authenticated route
  const isDashboardRoute = pathname?.startsWith('/dashboard') || pathname?.startsWith('/owner-portal');
  const isPublicRoute = PUBLIC_ROUTES.includes(pathname || '/') || pathname?.startsWith('/verify-email');

  // For public/landing routes, force dark theme without NextThemesProvider
  // This ensures no localStorage/cookie theme leakage
  if (isPublicRoute && !isDashboardRoute) {
    return (
      <ForcedDarkTheme>
        {children}
      </ForcedDarkTheme>
    );
  }

  // Dashboard/authenticated routes - use theme provider with user preferences
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem
      disableTransitionOnChange
      storageKey="tradeflow-dashboard-theme"
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}

/**
 * Component that forces dark theme for public pages
 * Applies dark class directly to document for proper Tailwind dark mode
 */
function ForcedDarkTheme({ children }: { children: React.ReactNode }) {
  React.useEffect(() => {
    // Force dark class on html element for public pages
    const html = document.documentElement;
    const originalClass = html.className;

    // Add dark class, remove light class
    html.classList.add('dark');
    html.classList.remove('light');

    // Cleanup on unmount (when navigating to dashboard)
    return () => {
      // Restore original class if needed
      if (!originalClass.includes('dark')) {
        html.classList.remove('dark');
      }
    };
  }, []);

  return <>{children}</>;
}
