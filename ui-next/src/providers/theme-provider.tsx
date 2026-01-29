'use client';

import * as React from 'react';
import { usePathname } from 'next/navigation';

// Create our own theme context - NO localStorage, backend only
const ThemeContext = React.createContext<{
  theme: string;
  setTheme: (theme: string) => void;
}>({
  theme: 'dark',
  setTheme: () => {},
});

// Export useTheme hook
export function useTheme() {
  return React.useContext(ThemeContext);
}

// Public routes that should always be dark (no user theme)
const PUBLIC_ROUTES = ['/', '/about', '/blog', '/contact', '/pricing', '/privacy', '/terms', '/login', '/register', '/resend-verification', '/verify-email'];

// Valid themes
const VALID_THEMES = ['dark', 'light', 'system', 'ocean'];

/**
 * Theme Provider with Per-User Isolation (Patch 1.3.0)
 *
 * COMPLETE REWRITE - No localStorage, no next-themes for dashboard.
 * Theme is stored ONLY in database per-user.
 *
 * Public pages: Always dark
 * Dashboard: Loaded from backend per-user, no cross-user leakage
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Check if we're on a dashboard/authenticated route
  const isDashboardRoute = pathname?.startsWith('/dashboard') || pathname?.startsWith('/owner-portal');
  const isPublicRoute = PUBLIC_ROUTES.includes(pathname || '/') || pathname?.startsWith('/verify-email');

  // For public/landing routes, force dark theme
  if (isPublicRoute && !isDashboardRoute) {
    return <ForcedDarkTheme>{children}</ForcedDarkTheme>;
  }

  // Dashboard/authenticated routes - use per-user theme from backend
  return <PerUserThemeProvider>{children}</PerUserThemeProvider>;
}

/**
 * Per-user theme provider - loads theme from backend database ONLY
 * No localStorage contamination between users
 */
function PerUserThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState('dark');
  const [loaded, setLoaded] = React.useState(false);

  // Apply theme to document
  const applyTheme = React.useCallback((newTheme: string) => {
    const html = document.documentElement;

    // Remove all theme classes
    html.classList.remove('dark', 'light', 'ocean');

    // Handle system theme
    if (newTheme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      html.classList.add(prefersDark ? 'dark' : 'light');
    } else {
      html.classList.add(newTheme);
    }

    // Set color-scheme for native elements
    html.style.colorScheme = newTheme === 'light' ? 'light' : 'dark';
  }, []);

  // Set theme and save to backend
  const setTheme = React.useCallback(async (newTheme: string) => {
    if (!VALID_THEMES.includes(newTheme)) return;

    setThemeState(newTheme);
    applyTheme(newTheme);

    // Save to backend (fire and forget)
    try {
      await fetch('/api/users/me/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: newTheme }),
        credentials: 'include',
      });
    } catch {
      // Silent fail
    }
  }, [applyTheme]);

  // Load theme from backend on mount
  React.useEffect(() => {
    // Clear ALL localStorage theme keys to prevent any contamination
    const keysToRemove = [
      'theme',
      'tradeflow-theme',
      'tradeflow-dashboard-theme',
      'next-theme',
      'chakra-ui-color-mode'
    ];
    keysToRemove.forEach(key => {
      try { localStorage.removeItem(key); } catch {}
    });

    // Load from backend
    fetch('/api/users/me/preferences', { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(prefs => {
        const userTheme = prefs?.theme || 'dark';
        setThemeState(userTheme);
        applyTheme(userTheme);
        setLoaded(true);
      })
      .catch(() => {
        applyTheme('dark');
        setLoaded(true);
      });
  }, [applyTheme]);

  // Apply dark theme immediately on mount (before backend loads)
  React.useEffect(() => {
    if (!loaded) {
      document.documentElement.classList.add('dark');
    }
  }, [loaded]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Forces dark theme for public pages
 */
function ForcedDarkTheme({ children }: { children: React.ReactNode }) {
  React.useEffect(() => {
    const html = document.documentElement;
    html.classList.remove('light', 'ocean');
    html.classList.add('dark');
    html.style.colorScheme = 'dark';
  }, []);

  return <>{children}</>;
}
