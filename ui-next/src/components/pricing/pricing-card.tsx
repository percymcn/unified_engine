"use client";

import { Check, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { type PricingTier, formatPrice } from "@/lib/pricing";

interface PricingCardProps {
  tier: PricingTier;
  isPopular?: boolean;
  isCurrent?: boolean;
  isAuthenticated?: boolean;
  onSelect?: (tier: PricingTier) => void;
}

export function PricingCard({
  tier,
  isPopular = false,
  isCurrent = false,
  isAuthenticated = false,
  onSelect,
}: PricingCardProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (onSelect) {
      onSelect(tier);
      return;
    }

    // Free tier - redirect to register
    if (tier.tier_id === "free") {
      router.push("/register");
      return;
    }

    // If not authenticated, redirect to register with tier
    if (!isAuthenticated) {
      router.push(`/register?tier=${tier.tier_id}`);
      return;
    }

    // Current tier - go to billing management
    if (isCurrent) {
      router.push("/dashboard/settings/billing");
      return;
    }

    // Paid tier - initiate checkout
    setLoading(true);
    try {
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier_id: tier.tier_id }),
      });

      if (response.status === 401) {
        // Not logged in - redirect to register with tier
        router.push(`/register?tier=${tier.tier_id}`);
        return;
      }

      const data = await response.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else if (data.portal_url) {
        // Already subscribed, redirect to portal
        window.location.href = data.portal_url;
      } else {
        console.error("No checkout URL returned:", data);
      }
    } catch (error) {
      console.error("Checkout error:", error);
    } finally {
      setLoading(false);
    }
  };

  // Determine CTA text
  const getCtaText = () => {
    if (loading) return "Loading...";
    if (isCurrent) return "Current Plan";
    if (tier.tier_id === "free") return "Get Started Free";
    if (!isAuthenticated) return "Get Started";
    return "Upgrade";
  };

  // Get description based on tier
  const getDescription = () => {
    switch (tier.tier_id) {
      case "free":
        return "Start routing signals today";
      case "tier_1":
        return "Perfect for individual traders";
      case "tier_2":
        return "For traders with multiple accounts";
      case "tier_3":
        return "Professional trading features";
      case "tier_4":
        return "Maximum power and flexibility";
      default:
        return "Trading automation";
    }
  };

  return (
    <Card
      className={cn(
        "relative flex flex-col transition-all hover:shadow-lg",
        isPopular && "border-primary ring-2 ring-primary",
        isCurrent && "border-green-500 bg-green-500/5"
      )}
    >
      {/* Popular badge */}
      {isPopular && !isCurrent && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <Badge className="bg-primary text-primary-foreground px-3 py-1">
            <Star className="h-3 w-3 mr-1 fill-current" />
            Most Popular
          </Badge>
        </div>
      )}

      {/* Current plan badge */}
      {isCurrent && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <Badge className="bg-green-500 text-white px-3 py-1">
            <Check className="h-3 w-3 mr-1" />
            Current Plan
          </Badge>
        </div>
      )}

      <CardHeader className="text-center pt-8">
        <CardTitle className="text-2xl font-bold">{tier.name}</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">{getDescription()}</p>

        {/* Price */}
        <div className="mt-4">
          <span className="text-4xl font-bold">
            {tier.price === 0 ? "Free" : formatPrice(tier.price)}
          </span>
          {tier.price > 0 && (
            <span className="text-muted-foreground ml-1">/month</span>
          )}
        </div>

        {/* Broker limit badge */}
        <div className="mt-3">
          <Badge variant="secondary" className="text-sm">
            {tier.brokers} Broker{tier.brokers !== 1 ? "s" : ""} Connection
            {tier.brokers !== 1 ? "s" : ""}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1">
        <ul className="space-y-3">
          {tier.features.map((feature) => (
            <li key={feature} className="flex items-start gap-3">
              <Check className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm">{feature}</span>
            </li>
          ))}

          {/* Standard features for all tiers */}
          <li className="flex items-start gap-3">
            <Check className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
            <span className="text-sm">Unlimited Signals</span>
          </li>
          <li className="flex items-start gap-3">
            <Check className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
            <span className="text-sm">Real-time Execution</span>
          </li>

          {/* Premium support indicators */}
          {(tier.tier_id === "tier_3" || tier.tier_id === "tier_4") && (
            <li className="flex items-start gap-3">
              <Check className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm">24/7 Support</span>
            </li>
          )}
          {tier.tier_id === "tier_4" && (
            <li className="flex items-start gap-3">
              <Check className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm">Priority Support</span>
            </li>
          )}
        </ul>
      </CardContent>

      <CardFooter>
        <Button
          className="w-full"
          variant={isPopular ? "default" : isCurrent ? "outline" : "secondary"}
          size="lg"
          onClick={handleClick}
          disabled={loading || isCurrent}
        >
          {getCtaText()}
        </Button>
      </CardFooter>
    </Card>
  );
}
