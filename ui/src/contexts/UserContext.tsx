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
    // Use Supabase authentication
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;

    if (data.session) {
      setAccessToken(data.session.access_token);
      apiClient.setToken(data.session.access_token);
      // Set basic user info from Supabase
      setUser({
        id: data.user.id,
        email: data.user.email || email,
        name: data.user.user_metadata?.name || email.split('@')[0],
        role: 'user',
        plan: 'starter',
      });
    }
  };

  const signup = async (email: string, password: string, name: string, plan: string) => {
    // Use Supabase authentication
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          name,
          plan,
        }
      }
    });

    if (error) throw error;

    if (data.session) {
      setAccessToken(data.session.access_token);
      apiClient.setToken(data.session.access_token);
      setUser({
        id: data.user.id,
        email: data.user.email || email,
        name: name,
        role: 'user',
        plan: plan as 'starter' | 'pro' | 'elite',
      });
    } else {
      // Email confirmation may be required
      throw new Error('Please check your email to confirm your account');
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
