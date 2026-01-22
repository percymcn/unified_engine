"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import {
  Check,
  Crown,
  Star,
  Zap,
  ArrowLeft,
  Shield,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { getPaidTiers, formatPrice, type PricingTier } from "@/lib/pricing";

interface BillingStatus {
  tier: string;
  status: string;
  broker_count?: number;
}

interface TrialStatus {
  status: string;
  trades_remaining: number;
  days_remaining: number;
}

export default function UpgradePage() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const router = useRouter();
  const { toast } = useToast();
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  const paidTiers = getPaidTiers();

  useEffect(() => {
    async function fetchStatus() {
      try {
        const [billingRes, trialRes] = await Promise.all([
          fetch("/api/billing/status"),
          fetch("/api/trial/status"),
        ]);

        if (billingRes.ok) {
          setBillingStatus(await billingRes.json());
        }
        if (trialRes.ok) {
          setTrialStatus(await trialRes.json());
        }
      } catch (error) {
        console.error("Error fetching status:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
  }, []);

  const handleSelectTier = async (tier: PricingTier) => {
    if (tier.tier_id === billingStatus?.tier) {
      // Already on this tier
      toast({
        title: "Current Plan",
        description: "You are already on this plan.",
      });
      return;
    }

    setCheckoutLoading(tier.tier_id);

    try {
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier_id: tier.tier_id }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to start checkout");
      }

      const data = await response.json();

      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else if (data.portal_url) {
        // Already has subscription, redirect to portal for upgrade
        window.location.href = data.portal_url;
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (error) {
      console.error("Checkout error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start checkout",
        variant: "destructive",
      });
    } finally {
      setCheckoutLoading(null);
    }
  };

  // Get recommended tier based on broker count
  const getRecommendedTier = (): string => {
    const brokerCount = billingStatus?.broker_count ?? 0;
    if (brokerCount >= 4) return "tier_4";
    if (brokerCount >= 3) return "tier_3";
    if (brokerCount >= 2) return "tier_2";
    return "tier_1";
  };

  const recommendedTier = getRecommendedTier();

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-8 w-20 mt-2" />
              </CardHeader>
              <CardContent className="space-y-3">
                {[1, 2, 3, 4].map((j) => (
                  <Skeleton key={j} className="h-4 w-full" />
                ))}
              </CardContent>
              <CardFooter>
                <Skeleton className="h-10 w-full" />
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const currentTier = billingStatus?.tier || "free";
  const isTrialExpired = trialStatus?.status === "expired";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Upgrade Your Plan</h1>
          <p className="text-muted-foreground">
            Choose the plan that fits your trading needs
          </p>
        </div>
      </div>

      {/* Trial status banner */}
      {isTrialExpired && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-4 flex items-start gap-3">
          <Shield className="h-5 w-5 text-destructive mt-0.5" />
          <div>
            <p className="font-medium text-destructive">Trial Expired</p>
            <p className="text-sm text-muted-foreground">
              Your free trial has ended. Select a plan below to continue trading.
            </p>
          </div>
        </div>
      )}

      {trialStatus?.status === "active" && (
        <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-4 flex items-start gap-3">
          <TrendingUp className="h-5 w-5 text-amber-500 mt-0.5" />
          <div>
            <p className="font-medium text-amber-600 dark:text-amber-400">
              Trial Active
            </p>
            <p className="text-sm text-muted-foreground">
              {trialStatus.trades_remaining} trades and {trialStatus.days_remaining} days remaining.
              Upgrade now to unlock unlimited trading.
            </p>
          </div>
        </div>
      )}

      {/* Pricing grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
        {paidTiers.map((tier) => {
          const isCurrentTier = currentTier === tier.tier_id;
          const isRecommended = recommendedTier === tier.tier_id && !isCurrentTier;
          const isLoading = checkoutLoading === tier.tier_id;

          return (
            <Card
              key={tier.tier_id}
              className={`relative flex flex-col transition-all hover:shadow-lg ${
                isRecommended
                  ? "border-primary ring-2 ring-primary"
                  : isCurrentTier
                    ? "border-green-500 bg-green-500/5"
                    : ""
              }`}
            >
              {/* Badges */}
              {isRecommended && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-primary text-primary-foreground px-3 py-1">
                    <Star className="h-3 w-3 mr-1 fill-current" />
                    Recommended
                  </Badge>
                </div>
              )}
              {isCurrentTier && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-green-500 text-white px-3 py-1">
                    <Check className="h-3 w-3 mr-1" />
                    Current Plan
                  </Badge>
                </div>
              )}

              <CardHeader className="text-center pt-8">
                <CardTitle className="text-xl font-bold">{tier.name}</CardTitle>
                <div className="mt-2">
                  <span className="text-3xl font-bold">
                    {formatPrice(tier.price)}
                  </span>
                  <span className="text-muted-foreground">/month</span>
                </div>
                <Badge variant="secondary" className="mt-3">
                  {tier.brokers} Broker{tier.brokers > 1 ? "s" : ""}
                </Badge>
              </CardHeader>

              <CardContent className="flex-1">
                <ul className="space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                  {/* Standard features */}
                  <li className="flex items-start gap-2 text-sm">
                    <Zap className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                    <span>Unlimited signals</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm">
                    <Zap className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                    <span>Real-time execution</span>
                  </li>
                </ul>
              </CardContent>

              <CardFooter>
                <Button
                  className="w-full"
                  variant={isRecommended ? "default" : isCurrentTier ? "outline" : "secondary"}
                  onClick={() => handleSelectTier(tier)}
                  disabled={isCurrentTier || isLoading}
                >
                  {isLoading ? (
                    "Processing..."
                  ) : isCurrentTier ? (
                    "Current Plan"
                  ) : (
                    <>
                      <Crown className="h-4 w-4 mr-2" />
                      Select Plan
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      {/* Trust indicators */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-8 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            <span>Secure Payment</span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            <span>Instant Activation</span>
          </div>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            <span>Cancel Anytime</span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Payments processed securely via Stripe. Cancel or change plans anytime.
        </p>
      </div>
    </div>
  );
}
