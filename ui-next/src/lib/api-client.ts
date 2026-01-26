// JWT Token Management Utility for Frontend

export interface AuthToken {
  token: string;
  expires_at: string;
  user: {
    id: number;
    email: string;
    username: string;
  };
}

export interface AuthState {
  token: string | null;
  user: any | null;
  isLoading: boolean;
  error: string | null;
}

const TOKEN_KEY = 'tradeflow_auth_token';
const USER_KEY = 'tradeflow_auth_user';

export const getStoredToken = (): string | null => {
  if (typeof window !== 'undefined') {
    try {
      const tokenData = localStorage.getItem(TOKEN_KEY);
      return tokenData;
    } catch (error) {
      console.error('Failed to get stored token:', error);
      return null;
    }
  }
  return null;
};

export const getStoredUser = (): any | null => {
  if (typeof window !== 'undefined') {
    try {
      const userData = localStorage.getItem(USER_KEY);
      if (userData) {
        return JSON.parse(userData);
      }
    } catch (error) {
      console.error('Failed to get stored user:', error);
      return null;
    }
  }
  return null;
};

export const setAuthData = (token: string, user: any): void => {
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (error) {
      console.error('Failed to store auth data:', error);
    }
  }
};

export const clearAuthData = (): void => {
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }
};

export const isTokenExpired = (token: string): boolean => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp;
    const now = Date.now() / 1000;
    return exp < now;
  } catch {
    return true; // Assume expired if can't parse
  }
};

// API client wrapper with automatic token handling
class ApiClient {
  private baseURL: string;
  
  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765') {
    this.baseURL = baseURL;
  }
  
  private async getAuthHeaders(): Promise<HeadersInit> {
    const token = getStoredToken();
    
    if (!token) {
      return {};
    }
    
    if (isTokenExpired(token)) {
      console.log('Token expired, clearing auth data');
      clearAuthData();
      window.location.href = '/login';
      throw new Error('Authentication expired');
    }
    
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }
  
  async get<T>(endpoint: string): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const headers = await this.getAuthHeaders();
    
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers,
      });
      
      if (response.status === 401) {
        console.log('401 Unauthorized, clearing auth data');
        clearAuthData();
        window.location.href = '/login';
        throw new Error('Authentication required');
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error.message === 'Authentication required') {
        throw error; // Re-throw for auth errors
      }
      console.error('API request failed:', error);
      throw error;
    }
  }
  
  async post<T>(endpoint: string, data?: any): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const headers = await this.getAuthHeaders();
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: data ? JSON.stringify(data) : undefined,
      });
      
      if (response.status === 401) {
        console.log('401 Unauthorized, clearing auth data');
        clearAuthData();
        window.location.href = '/login';
        throw new Error('Authentication required');
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error.message === 'Authentication required') {
        throw error; // Re-throw for auth errors
      }
      console.error('API request failed:', error);
      throw error;
    }
  }
}

export default new ApiClient();