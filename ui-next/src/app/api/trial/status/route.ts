/**
 * Trial Status BFF Route
 * Proxies trial information from backend /api/trial/status
 */
import { NextResponse } from "next/server";
import { cookies } from "next/headers";

/**
 * Trial status response type
 */
export interface TrialStatusResponse {
  status: "not_started" | "active" | "expired" | "not_applicable";
  subscription_tier: string;
  trades_remaining: number | null;
  trades_used: number | null;
  trades_limit: number | null;
  days_remaining: number | null;
  hours_remaining: number | null;
  days_limit: number | null;
  trial_started_at: string | null;
  trial_ended_at: string | null;
  is_expired: boolean;
}

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  if (!token) {
    // Return null trial info for unauthenticated users (graceful degradation)
    return NextResponse.json({
      status: null,
      subscription_tier: null,
      trades_remaining: null,
      trades_used: null,
      trades_limit: null,
      days_remaining: null,
      hours_remaining: null,
      days_limit: null,
      trial_started_at: null,
      trial_ended_at: null,
      is_expired: false,
    });
  }

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8765";

  try {
    const response = await fetch(`${backendUrl}/api/trial/status`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      // Return graceful fallback for backend errors
      if (response.status === 401) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
      }
      console.error(`Trial status backend error: ${response.status}`);
      return NextResponse.json({
        status: null,
        subscription_tier: null,
        trades_remaining: null,
        trades_used: null,
        trades_limit: null,
        days_remaining: null,
        hours_remaining: null,
        days_limit: null,
        trial_started_at: null,
        trial_ended_at: null,
        is_expired: false,
      });
    }

    const data = await response.json();

    // Add computed is_expired field for convenience
    const isExpired = data.status === "expired";

    return NextResponse.json({
      ...data,
      is_expired: isExpired,
    });
  } catch (error) {
    console.error("Trial status API error:", error);
    // Return graceful fallback on network errors
    return NextResponse.json({
      status: null,
      subscription_tier: null,
      trades_remaining: null,
      trades_used: null,
      trades_limit: null,
      days_remaining: null,
      hours_remaining: null,
      days_limit: null,
      trial_started_at: null,
      trial_ended_at: null,
      is_expired: false,
    });
  }
}
