'use client';

import * as React from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { type ThemeProviderProps } from 'next-themes';
import { usePathname } from 'next/navigation';

export { useTheme } from 'next-themes';

/**
 * Theme Provider with Dashboard-Only Isolation (Patch 1.2.1)
 * 
 * Theme applies ONLY to dashboard routes (/dashboard/*).
 * Landing page (/app/page.tsx) always remains dark and ignores theme cookie.
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  const pathname = usePathname();
  
  // Check if we're on a dashboard route
  const isDashboardRoute = pathname?.startsWith('/dashboard') || pathname?.startsWith('/app');
  
  // For dashboard routes, use theme provider
  // For landing/public routes, force dark theme
  if (!isDashboardRoute) {
    // Landing page - force dark, ignore theme cookie
    return (
      <div className="dark" suppressHydrationWarning>
        {children}
      </div>
    );
  }
  
  // Dashboard route - use theme provider with cookie support
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
