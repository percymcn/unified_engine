"use client";

import { useState, useEffect } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { X, AlertTriangle, TrendingUp, Crown } from "lucide-react";
import Link from "next/link";

interface UpgradePromptProps {
  isExpired: boolean;
  tradesRemaining: number;
}

// Local storage key for dismissal
const DISMISS_KEY = "tradeflow_upgrade_prompt_dismissed";
const DISMISS_EXPIRY_HOURS = 24; // Re-show after 24 hours

/**
 * Check if the prompt was recently dismissed
 */
function wasRecentlyDismissed(): boolean {
  if (typeof window === "undefined") return false;

  const dismissedAt = localStorage.getItem(DISMISS_KEY);
  if (!dismissedAt) return false;

  const dismissedTime = parseInt(dismissedAt, 10);
  const now = Date.now();
  const hoursSinceDismiss = (now - dismissedTime) / (1000 * 60 * 60);

  return hoursSinceDismiss < DISMISS_EXPIRY_HOURS;
}

/**
 * Save dismissal timestamp
 */
function saveDismissal(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(DISMISS_KEY, Date.now().toString());
}

/**
 * Upgrade prompt component
 * Shows when trial is expired or running low on trades
 * Dismissible with X button (stores in localStorage)
 */
export function UpgradePrompt({ isExpired, tradesRemaining }: UpgradePromptProps) {
  const [dismissed, setDismissed] = useState(true); // Start hidden to avoid flash
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Check if recently dismissed
    if (!wasRecentlyDismissed()) {
      setDismissed(false);
    }
  }, []);

  // Don't show if dismissed or not mounted
  if (dismissed || !mounted) return null;

  // Only show if expired or low trades (<10)
  const isLowTrades = tradesRemaining > 0 && tradesRemaining <= 10;
  if (!isExpired && !isLowTrades) return null;

  const handleDismiss = () => {
    saveDismissal();
    setDismissed(true);
  };

  if (isExpired) {
    return (
      <Alert
        variant="destructive"
        className="relative mb-4 border-destructive/50 bg-destructive/10"
      >
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle className="font-semibold">Trial Ended</AlertTitle>
        <AlertDescription className="mt-1">
          <span className="block text-sm">
            Your free trial has ended. Upgrade to continue trading.
          </span>
          <div className="mt-3 flex items-center gap-3">
            <Link href="/dashboard/upgrade">
              <Button size="sm" variant="default">
                <Crown className="h-4 w-4 mr-2" />
                Upgrade Now
              </Button>
            </Link>
            <Link href="/pricing">
              <Button size="sm" variant="outline">
                View Plans
              </Button>
            </Link>
          </div>
        </AlertDescription>
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-2 top-2 h-6 w-6 rounded-full opacity-70 hover:opacity-100"
          onClick={handleDismiss}
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Dismiss</span>
        </Button>
      </Alert>
    );
  }

  // Low trades warning
  return (
    <Alert className="relative mb-4 border-amber-500/50 bg-amber-500/10">
      <TrendingUp className="h-4 w-4 text-amber-500" />
      <AlertTitle className="font-semibold text-amber-600 dark:text-amber-400">
        Running Low on Trades
      </AlertTitle>
      <AlertDescription className="mt-1">
        <span className="block text-sm">
          Only <strong>{tradesRemaining}</strong> trades left in your free trial.
          Upgrade for unlimited trading.
        </span>
        <div className="mt-3 flex items-center gap-3">
          <Link href="/dashboard/upgrade">
            <Button size="sm" variant="default">
              <Crown className="h-4 w-4 mr-2" />
              Upgrade Now
            </Button>
          </Link>
          <Link href="/pricing">
            <Button size="sm" variant="outline">
              View Plans
            </Button>
          </Link>
        </div>
      </AlertDescription>
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-6 w-6 rounded-full opacity-70 hover:opacity-100"
        onClick={handleDismiss}
      >
        <X className="h-4 w-4" />
        <span className="sr-only">Dismiss</span>
      </Button>
    </Alert>
  );
}
