import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import {
  getAllTiers,
  type PricingTier,
} from "@/lib/pricing";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8765";

// Cache the tiers response for 1 hour (tiers don't change often)
export const revalidate = 3600;

interface PlansResponse {
  tiers: PricingTier[];
  current_tier: string | null;
  is_authenticated: boolean;
}

/**
 * GET /api/billing/plans
 *
 * Returns all pricing tiers with the user's current tier (if authenticated).
 * Used by both landing page and upgrade page.
 *
 * Response:
 * {
 *   tiers: [...],
 *   current_tier: string | null,
 *   is_authenticated: boolean
 * }
 */
export async function GET() {
  // Get all tiers from centralized config
  const tiers = getAllTiers();

  // Try to get user's current tier if authenticated
  let currentTier: string | null = null;
  let isAuthenticated = false;

  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("token")?.value;

    if (token) {
      // Fetch user's billing status from backend
      const response = await fetch(`${BACKEND_URL}/api/billing/status`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        // Don't cache this - user-specific
        cache: "no-store",
      });

      if (response.ok) {
        const data = await response.json();
        currentTier = data.subscription_tier || data.current_tier || "free";
        isAuthenticated = true;
      } else if (response.status === 401) {
        // Token expired or invalid
        isAuthenticated = false;
        currentTier = null;
      } else {
        // Other error - still return tiers
        console.error(
          "Failed to fetch billing status:",
          response.status,
          await response.text()
        );
      }
    }
  } catch (error) {
    // Continue without user tier on error
    console.error("Error fetching user tier:", error);
  }

  const responseData: PlansResponse = {
    tiers,
    current_tier: currentTier,
    is_authenticated: isAuthenticated,
  };

  return NextResponse.json(responseData, {
    headers: {
      // Cache for 1 hour for unauthenticated requests
      // But always revalidate for authenticated requests
      "Cache-Control": isAuthenticated
        ? "private, no-store"
        : "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
