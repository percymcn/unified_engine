import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8765";

interface PlanInfo {
  id: string;
  name: string;
  monthly_price: number; // cents
  price_display: string;
  features: string[];
  stripe_price_id: string | null;
  broker_limit: number;
}

interface PlansResponse {
  plans: PlanInfo[];
  current_tier: string;
  current_tier_name: string;
}

/**
 * GET /api/billing/plans
 *
 * Proxies to backend /api/billing/plans endpoint (single source of truth).
 * Returns all pricing tiers with the user's current tier (if authenticated).
 * Used by both landing page, upgrade page, and billing page.
 *
 * Response:
 * {
 *   plans: [{ id, name, monthly_price, price_display, features, stripe_price_id, broker_limit }],
 *   current_tier: string,
 *   current_tier_name: string
 * }
 */
export async function GET() {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("token")?.value;

    // Proxy to backend (single source of truth)
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${BACKEND_URL}/api/billing/plans`, {
      headers,
      // Don't cache authenticated requests
      cache: token ? "no-store" : "default",
    });

    if (!response.ok) {
      // If backend fails, return empty plans (fail-open)
      console.error("Backend plans endpoint failed:", response.status);
      return NextResponse.json(
        {
          plans: [],
          current_tier: "free",
          current_tier_name: "Free",
        },
        { status: 200 } // Return 200 with empty plans to avoid breaking UI
      );
    }

    const data: PlansResponse = await response.json();

    return NextResponse.json(data, {
      headers: {
        // Cache for 1 hour for unauthenticated requests
        // But always revalidate for authenticated requests
        "Cache-Control": token
          ? "private, no-store"
          : "public, s-maxage=3600, stale-while-revalidate=86400",
      },
    });
  } catch (error) {
    // Fail-open: return empty plans on error
    console.error("Error fetching plans:", error);
    return NextResponse.json(
      {
        plans: [],
        current_tier: "free",
        current_tier_name: "Free",
      },
      { status: 200 }
    );
  }
}
