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
        const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8765";
        const response = await fetch(`${BACKEND_URL}/api/v1/oauth/providers`);
        
        if (!response.ok) {
          // If endpoint doesn't exist or fails, assume no OAuth configured
          setProviders([]);
          setIsLoading(false);
          return;
        }

        const data: OAuthProvidersResponse = await response.json();
        setProviders(data.providers || []);
      } catch {
        // Fail-open: if check fails, assume no OAuth configured
        setProviders([]);
        setError(null); // Don't show error, just no OAuth
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
