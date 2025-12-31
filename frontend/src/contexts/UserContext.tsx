import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { createClient } from '@supabase/supabase-js';
import { projectId, publicAnonKey } from '../utils/supabase/info';
import { apiClient } from '../utils/api-client';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  plan: 'starter' | 'pro' | 'elite';
  apiKey?: string;
  avatarUrl?: string;
  trialEndsAt?: string;
  tradesCount?: number;
}

interface UserContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  isAdmin: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string, plan: string) => Promise<void>;
  logout: () => void;
  accessToken: string | null;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

const supabase = createClient(
  `https://${projectId}.supabase.co`,
  publicAnonKey
);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Check for existing session on mount
  useEffect(() => {
    checkSession();
  }, []);

  const checkSession = async () => {
    try {
      const { data: { session }, error } = await supabase.auth.getSession();
      
      if (error) throw error;
      
      if (session) {
        setAccessToken(session.access_token);
        await fetchUserProfile(session.user.id, session.access_token);
      }
    } catch (error) {
      console.error('Session check error:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUserProfile = async (userId: string, token: string) => {
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-d751d621/user/profile`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.ok) {
        const profile = await response.json();
        setUser(profile);
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      // Use unified auth service - detect URL based on current origin
      // If accessed via Cloudflare, use same domain (Cloudflare proxies to backend)
      // Otherwise use local IP for development
      const authUrl = process.env.VITE_AUTH_API_URL || 
        (window.location.hostname.includes('fluxeo.net') 
          ? `${window.location.protocol}//${window.location.hostname}`
          : 'http://192.168.1.254:5228');
      const response = await fetch(`${authUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const authData = await response.json();
          setAccessToken(authData.access_token);
          apiClient.setToken(authData.access_token);
          setUser({
            id: authData.user_id || String(authData.user_id) || '',
            email: authData.email,
            name: authData.name || '',
            role: authData.role || 'user',
            plan: authData.plan || 'trial',
          });
          return;
        } else {
          throw new Error('Invalid response format from server');
        }
      } else {
        // Try to parse error response
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          throw new Error(errorData.detail || errorData.error || `Login failed with status ${response.status}`);
        } else {
          throw new Error(`Login failed with status ${response.status}`);
        }
      }
    } catch (error: any) {
      console.warn('Unified auth service error:', error);
      // Only fallback if it's a network error, not an auth error
      if (error.message && error.message.includes('fetch')) {
        console.warn('Network error, falling back to Supabase');
      } else {
        throw error;
      }
    }

    // Fallback to Supabase
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;

    if (data.session) {
      setAccessToken(data.session.access_token);
      apiClient.setToken(data.session.access_token);
      await fetchUserProfile(data.user.id, data.session.access_token);
    }
  };

  const signup = async (email: string, password: string, name: string, plan: string) => {
    try {
      // Use unified auth service - detect URL based on current origin
      // If accessed via Cloudflare, use same domain (Cloudflare proxies to backend)
      // Otherwise use local IP for development
      const authUrl = process.env.VITE_AUTH_API_URL || 
        (window.location.hostname.includes('fluxeo.net') 
          ? `${window.location.protocol}//${window.location.hostname}`
          : 'http://192.168.1.254:5228');
      const response = await fetch(`${authUrl}/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password, name })
      });

      if (response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const authData = await response.json();
          setAccessToken(authData.access_token);
          apiClient.setToken(authData.access_token);
          setUser({
            id: authData.user_id || String(authData.user_id) || '',
            email: authData.email,
            name: authData.name || name,
            role: authData.role || 'user',
            plan: authData.plan || 'trial',
          });
          return;
        } else {
          throw new Error('Invalid response format from server');
        }
      } else {
        // Try to parse error response
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          // Handle validation errors
          if (errorData.detail && Array.isArray(errorData.detail)) {
            const errorMessages = errorData.detail.map((err: any) => err.msg || err.message).join(', ');
            throw new Error(errorMessages || 'Signup validation failed');
          }
          throw new Error(errorData.detail || errorData.error || `Signup failed with status ${response.status}`);
        } else {
          throw new Error(`Signup failed with status ${response.status}`);
        }
      }
    } catch (error: any) {
      console.error('Signup error:', error);
      // Only fallback if it's a network error, not a validation/auth error
      if (error.message && error.message.includes('fetch')) {
        console.warn('Network error, falling back to Supabase');
      } else {
        throw error;
      }
      
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-d751d621/auth/signup`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email, password, name, plan })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Signup failed');
      }

      // After signup, login automatically
      await login(email, password);
    }
  };

  const logout = () => {
    supabase.auth.signOut();
    setUser(null);
    setAccessToken(null);
    apiClient.setToken('');
  };

  const isAdmin = user?.role === 'admin';

  return (
    <UserContext.Provider value={{ 
      user, 
      setUser, 
      isAdmin, 
      loading,
      login,
      signup,
      logout,
      accessToken
    }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
