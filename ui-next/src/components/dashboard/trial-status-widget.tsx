"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Crown,
  Zap,
  ArrowRight,
  AlertTriangle,
  Clock,
  Activity,
} from "lucide-react";
import Link from "next/link";
import { getTierInfo } from "@/lib/pricing";

interface TrialStatus {
  status: "not_started" | "active" | "expired" | "not_applicable" | null;
  subscription_tier: string | null;
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

interface BillingStatus {
  tier: string;
  status: string;
  ends_at: string | null;
  can_manage: boolean;
  broker_count?: number;
  broker_limit?: number;
}

export function TrialStatusWidget() {
  const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(
    null
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStatus() {
      try {
        // Fetch both trial and billing status in parallel
        const [trialRes, billingRes] = await Promise.all([
          fetch("/api/trial/status"),
          fetch("/api/billing/status"),
        ]);

        if (trialRes.ok) {
          const trialData = await trialRes.json();
          setTrialStatus(trialData);
        }

        if (billingRes.ok) {
          const billingData = await billingRes.json();
          setBillingStatus(billingData);
        }
      } catch (error) {
        console.error("Error fetching status:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
  }, []);

  if (loading) {
    return (
      <Card className="glass glass-hover">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Subscription Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-32" />
              </div>
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Determine if user is on a paid tier
  const isPaidUser =
    trialStatus?.status === "not_applicable" ||
    (billingStatus?.tier && billingStatus.tier !== "free");

  // Get tier info for paid users
  const tierInfo = isPaidUser ? getTierInfo(billingStatus?.tier || "free") : null;
  const isCanceling = billingStatus?.status === "canceling";

  // If paid user, show current tier info
  if (isPaidUser && tierInfo) {
    return (
      <Card className="glass glass-hover">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Subscription Status</CardTitle>
            <Badge
              variant="outline"
              className="border-primary text-primary flex items-center gap-1"
            >
              <Crown className="h-3 w-3" />
              {tierInfo.name}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Crown className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">{tierInfo.name} Plan</p>
                <p className="text-xs text-muted-foreground">
                  {isCanceling ? (
                    <>
                      Canceling - Active until{" "}
                      {billingStatus?.ends_at
                        ? new Date(billingStatus.ends_at).toLocaleDateString()
                        : "end of period"}
                    </>
                  ) : (
                    `${tierInfo.brokers} broker connection${tierInfo.brokers > 1 ? "s" : ""}`
                  )}
                </p>
              </div>
            </div>

            {/* Broker usage */}
            {billingStatus?.broker_count !== undefined && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Brokers</span>
                  <span className="font-medium">
                    {billingStatus.broker_count}/{tierInfo.brokers}
                  </span>
                </div>
                <Progress
                  value={
                    (billingStatus.broker_count / tierInfo.brokers) * 100
                  }
                  className="h-2"
                />
              </div>
            )}

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Zap className="h-4 w-4 text-green-500" />
                <span>Priority signal execution</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Zap className="h-4 w-4 text-green-500" />
                <span>Advanced routing rules</span>
              </div>
            </div>

            <Link href="/dashboard/settings/billing">
              <Button variant="outline" size="sm" className="w-full">
                Manage Subscription
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Trial user - show trial status
  const isTrialExpired = trialStatus?.is_expired || trialStatus?.status === "expired";
  const isTrialActive = trialStatus?.status === "active";
  const isTrialNotStarted = trialStatus?.status === "not_started";

  const tradesRemaining = trialStatus?.trades_remaining ?? 0;
  const tradesLimit = trialStatus?.trades_limit ?? 100;
  const tradesUsed = trialStatus?.trades_used ?? 0;
  const daysRemaining = trialStatus?.days_remaining ?? 0;
  const hoursRemaining = trialStatus?.hours_remaining ?? 0;
  const daysLimit = trialStatus?.days_limit ?? 3;

  // Calculate progress percentages (inverted - remaining is what's left)
  const tradesProgress = tradesLimit > 0 ? (tradesUsed / tradesLimit) * 100 : 0;
  const daysElapsed = daysLimit - daysRemaining - (hoursRemaining > 0 ? hoursRemaining / 24 : 0);
  const daysProgress = daysLimit > 0 ? (daysElapsed / daysLimit) * 100 : 0;

  // Determine if trial is running low
  const isLowTrades = tradesRemaining > 0 && tradesRemaining <= 10;
  const isLowDays = daysRemaining <= 1 && !isTrialExpired;

  return (
    <Card className="glass glass-hover">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Trial Status</CardTitle>
          {isTrialExpired && (
            <Badge variant="destructive" className="flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Expired
            </Badge>
          )}
          {isTrialActive && !isTrialExpired && (
            <Badge
              variant="outline"
              className="border-green-500 text-green-600 flex items-center gap-1"
            >
              <Activity className="h-3 w-3" />
              Active
            </Badge>
          )}
          {isTrialNotStarted && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Ready
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isTrialExpired ? (
          // Expired trial view
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-destructive/10 flex items-center justify-center">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <p className="font-medium">Trial Ended</p>
                <p className="text-xs text-muted-foreground">
                  Upgrade to continue trading
                </p>
              </div>
            </div>

            <div className="rounded-lg bg-destructive/5 p-3 border border-destructive/10">
              <p className="text-sm font-medium text-destructive">
                Your free trial has ended
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {tradesUsed} trades used. Upgrade now to unlock unlimited trading.
              </p>
            </div>

            <Link href="/dashboard/upgrade">
              <Button className="w-full">
                <Crown className="h-4 w-4 mr-2" />
                Upgrade Now
              </Button>
            </Link>
          </div>
        ) : isTrialNotStarted ? (
          // Trial not started view
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                <Zap className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-medium">Free Trial Ready</p>
                <p className="text-xs text-muted-foreground">
                  100 trades | 3 days
                </p>
              </div>
            </div>

            <div className="rounded-lg bg-primary/5 p-3 border border-primary/10">
              <p className="text-sm font-medium">Start Trading</p>
              <p className="text-xs text-muted-foreground mt-1">
                Your trial begins when you execute your first signal.
              </p>
            </div>

            <Link href="/dashboard/settings/webhooks">
              <Button variant="outline" className="w-full">
                Set Up Webhooks
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </div>
        ) : (
          // Active trial view
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              {/* Circular Progress Ring */}
              <div className="relative h-16 w-16">
                <svg className="h-16 w-16 -rotate-90" viewBox="0 0 64 64">
                  {/* Background circle */}
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    fill="none"
                    strokeWidth="4"
                    className="stroke-muted"
                  />
                  {/* Progress circle - color shifts based on days remaining */}
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    fill="none"
                    strokeWidth="4"
                    strokeLinecap="round"
                    className={`transition-all duration-500 ${
                      daysRemaining <= 1
                        ? "stroke-red-500"
                        : daysRemaining <= 2
                        ? "stroke-amber-500"
                        : "stroke-green-500"
                    }`}
                    style={{
                      strokeDasharray: `${(1 - daysProgress / 100) * 175.9} 175.9`,
                    }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-lg font-bold ${
                    daysRemaining <= 1
                      ? "text-red-500"
                      : daysRemaining <= 2
                      ? "text-amber-500"
                      : "text-green-500"
                  }`}>
                    {daysRemaining}d
                  </span>
                  <span className="text-[10px] text-muted-foreground">left</span>
                </div>
              </div>
              <div>
                <p className="font-medium">Trial Active</p>
                <p className="text-xs text-muted-foreground">
                  Started{" "}
                  {trialStatus?.trial_started_at
                    ? new Date(trialStatus.trial_started_at).toLocaleDateString()
                    : "recently"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoursRemaining}h remaining today
                </p>
              </div>
            </div>

            {/* Trades remaining */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Trades</span>
                <span
                  className={`font-medium ${isLowTrades ? "text-amber-500" : ""}`}
                >
                  {tradesRemaining} left
                </span>
              </div>
              <Progress
                value={tradesProgress}
                className={`h-2 ${isLowTrades ? "[&>div]:bg-amber-500" : ""}`}
              />
              <p className="text-xs text-muted-foreground text-right">
                {tradesUsed}/{tradesLimit} used
              </p>
            </div>

            {/* Days remaining */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Time</span>
                <span
                  className={`font-medium ${isLowDays ? "text-amber-500" : ""}`}
                >
                  {daysRemaining}d {hoursRemaining}h left
                </span>
              </div>
              <Progress
                value={daysProgress}
                className={`h-2 ${isLowDays ? "[&>div]:bg-amber-500" : ""}`}
              />
            </div>

            {/* Low trial warning */}
            {(isLowTrades || isLowDays) && (
              <div className="rounded-lg bg-amber-500/10 p-3 border border-amber-500/20">
                <p className="text-sm font-medium text-amber-600 dark:text-amber-400">
                  {isLowTrades
                    ? `Only ${tradesRemaining} trades left`
                    : `Only ${daysRemaining} day${daysRemaining !== 1 ? "s" : ""} left`}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Upgrade for unlimited trading.
                </p>
              </div>
            )}

            <Link href="/dashboard/upgrade">
              <Button
                variant={isLowTrades || isLowDays ? "default" : "outline"}
                className="w-full"
              >
                <Crown className="h-4 w-4 mr-2" />
                {isLowTrades || isLowDays ? "Upgrade Now" : "View Plans"}
              </Button>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
