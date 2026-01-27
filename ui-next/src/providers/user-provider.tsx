'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

/**
 * User type for context
 * Contains user profile information from backend
 */
export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  timezone: string | null;
  subscription_tier: string;
  primary_webhook_key?: string | null;
}

/**
 * User context value type
 */
interface UserContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * User context with default values
 */
const UserContext = createContext<UserContextValue>({
  user: null,
  loading: true,
  error: null,
  refetch: async () => {},
});

/**
 * User provider props
 */
interface UserProviderProps {
  children: ReactNode;
}

/**
 * User provider component
 * Fetches and provides user data throughout the app
 */
export function UserProvider({ children }: UserProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch user profile from BFF API
   */
  const fetchUser = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/users/me/profile', { credentials: 'include' });

      if (!response.ok) {
        // Handle auth errors gracefully - user is not logged in
        if (response.status === 401) {
          setUser(null);
          return;
        }
        throw new Error('Failed to fetch user');
      }

      const data = await response.json();
      setUser(data);
    } catch (err) {
      console.error('Error fetching user:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch user');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Refetch user data - can be called after profile updates
   */
  const refetch = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  // Fetch user on mount
  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return (
    <UserContext.Provider value={{ user, loading, error, refetch }}>
      {children}
    </UserContext.Provider>
  );
}

/**
 * Hook to access user context
 * @returns User context value with user, loading, error, and refetch
 */
export function useUser(): UserContextValue {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
