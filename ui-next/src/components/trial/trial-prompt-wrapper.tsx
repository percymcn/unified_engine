"use client";

import { useEffect, useState } from "react";
import { UpgradePrompt } from "./upgrade-prompt";

interface TrialStatus {
  status: "not_started" | "active" | "expired" | "not_applicable" | null;
  trades_remaining: number | null;
  is_expired: boolean;
}

/**
 * Wrapper component that fetches trial status and conditionally renders UpgradePrompt
 * Used in dashboard layout to show prompts when trial is low/expired
 */
export function TrialPromptWrapper() {
  const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTrialStatus() {
      try {
        const response = await fetch("/api/trial/status");
        if (response.ok) {
          const data = await response.json();
          setTrialStatus(data);
        }
      } catch (error) {
        console.error("Error fetching trial status:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchTrialStatus();
  }, []);

  // Don't render anything while loading or if status is null
  if (loading || !trialStatus) return null;

  // Don't render for paid users
  if (trialStatus.status === "not_applicable") return null;

  // Only show for expired or low trades
  const isExpired = trialStatus.is_expired || trialStatus.status === "expired";
  const tradesRemaining = trialStatus.trades_remaining ?? 100;
  const isLowTrades = tradesRemaining > 0 && tradesRemaining <= 10;

  if (!isExpired && !isLowTrades) return null;

  return (
    <UpgradePrompt
      isExpired={isExpired}
      tradesRemaining={tradesRemaining}
    />
  );
}
