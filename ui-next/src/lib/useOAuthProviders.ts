"use client";

/**
 * OAuth Provider Check Hook
 * Checks if Google OAuth is configured via backend API
 */

import { useState, useEffect } from "react";

interface OAuthProvider {
  provider: string;
  name: string;
  auth_url: string;
}

interface OAuthProvidersResponse {
  providers: OAuthProvider[];
}

export function useOAuthProviders() {
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProviders() {
      try {
        // Use BFF route to avoid CORS issues and allow redirect_uri override for local dev
        console.log('[OAuth] Fetching providers from BFF: /api/auth/providers');
        const response = await fetch('/api/auth/providers', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        console.log('[OAuth] Response status:', response.status);

        if (!response.ok) {
          console.warn(`[OAuth] Providers endpoint returned ${response.status}`);
          setProviders([]);
          setIsLoading(false);
          return;
        }

        const data: OAuthProvidersResponse = await response.json();
        console.log('[OAuth] Providers received:', data.providers);
        setProviders(data.providers || []);
      } catch (err) {
        console.error('[OAuth] Failed to fetch providers:', err);
        setProviders([]);
        setError(null);
      } finally {
        setIsLoading(false);
      }
    }

    fetchProviders();
  }, []);

  const isGoogleEnabled = providers.some((p) => p.provider === "google");
  const googleAuthUrl = providers.find((p) => p.provider === "google")?.auth_url || null;

  return {
    providers,
    isGoogleEnabled,
    googleAuthUrl,
    isLoading,
    error,
  };
}
