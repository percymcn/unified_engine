"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Check, Crown, Star, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { getAllTiers, formatPrice, type PricingTier } from "@/lib/pricing";

interface UpgradeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentTier?: string;
}

export function UpgradeModal({ open, onOpenChange, currentTier = "free" }: UpgradeModalProps) {
  const [isAnnual, setIsAnnual] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const tiers = getAllTiers();

  const getDisplayPrice = (tier: PricingTier) => {
    if (tier.price === 0) return "Free";
    const monthlyPrice = tier.price;
    if (isAnnual) {
      const annualMonthly = Math.round(monthlyPrice * 0.8);
      return formatPrice(annualMonthly);
    }
    return formatPrice(monthlyPrice);
  };

  const handleUpgrade = async (tier: PricingTier) => {
    if (tier.tier_id === "free" || tier.tier_id === currentTier) return;

    setLoading(tier.tier_id);
    try {
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tier_id: tier.tier_id,
          billing_cycle: isAnnual ? "annual" : "monthly"
        }),
      });

      const data = await response.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else if (data.portal_url) {
        window.location.href = data.portal_url;
      }
    } catch (error) {
      console.error("Checkout error:", error);
    } finally {
      setLoading(null);
    }
  };

  const isCurrent = (tierId: string) => {
    // Map tier_id to subscription_tier values
    const tierMap: Record<string, string> = {
      "free": "free",
      "tier_1": "starter",
      "tier_2": "trader",
      "tier_3": "pro",
      "tier_4": "enterprise",
    };
    return tierMap[tierId] === currentTier || tierId === currentTier;
  };

  const isUpgrade = (tierId: string) => {
    const tierOrder = ["free", "tier_1", "tier_2", "tier_3", "tier_4"];
    const currentMap: Record<string, string> = {
      "free": "free",
      "starter": "tier_1",
      "trader": "tier_2",
      "pro": "tier_3",
      "enterprise": "tier_4",
    };
    const currentIndex = tierOrder.indexOf(currentMap[currentTier] || "free");
    const targetIndex = tierOrder.indexOf(tierId);
    return targetIndex > currentIndex;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-2xl">
            <Crown className="h-6 w-6 text-primary" />
            Upgrade Your Plan
          </DialogTitle>
          <DialogDescription>
            Choose the plan that best fits your trading needs
          </DialogDescription>
        </DialogHeader>

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-3 py-4">
          <Label
            htmlFor="billing-toggle-modal"
            className={cn(
              "text-sm cursor-pointer transition-colors",
              !isAnnual ? "font-semibold text-foreground" : "text-muted-foreground"
            )}
          >
            Monthly
          </Label>
          <Switch
            id="billing-toggle-modal"
            checked={isAnnual}
            onCheckedChange={setIsAnnual}
          />
          <Label
            htmlFor="billing-toggle-modal"
            className={cn(
              "text-sm cursor-pointer transition-colors",
              isAnnual ? "font-semibold text-foreground" : "text-muted-foreground"
            )}
          >
            Annual
          </Label>
          {isAnnual && (
            <Badge variant="secondary" className="bg-green-500/10 text-green-600 dark:text-green-400">
              <Sparkles className="h-3 w-3 mr-1" />
              Save 20%
            </Badge>
          )}
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {tiers.map((tier) => {
            const current = isCurrent(tier.tier_id);
            const upgrade = isUpgrade(tier.tier_id);
            const isPopular = tier.tier_id === "tier_3";

            return (
              <div
                key={tier.tier_id}
                className={cn(
                  "relative flex flex-col rounded-xl border p-4 transition-all",
                  isPopular && "border-primary ring-2 ring-primary",
                  current && "border-green-500 bg-green-500/5",
                  !current && !isPopular && "border-border hover:border-primary/50"
                )}
              >
                {/* Popular badge */}
                {isPopular && !current && (
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground text-xs px-2 py-0.5">
                      <Star className="h-3 w-3 mr-1 fill-current" />
                      Popular
                    </Badge>
                  </div>
                )}

                {/* Current badge */}
                {current && (
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
                    <Badge className="bg-green-500 text-white text-xs px-2 py-0.5">
                      <Check className="h-3 w-3 mr-1" />
                      Current
                    </Badge>
                  </div>
                )}

                <div className="text-center pt-2">
                  <h3 className="font-semibold text-lg">{tier.name}</h3>
                  <div className="mt-2">
                    <span className="text-2xl font-bold">
                      {tier.price === 0 ? "Free" : getDisplayPrice(tier)}
                    </span>
                    {tier.price > 0 && (
                      <span className="text-muted-foreground text-sm">/mo</span>
                    )}
                  </div>
                  <Badge variant="secondary" className="mt-2 text-xs">
                    {tier.brokers} Broker{tier.brokers !== 1 ? "s" : ""}
                  </Badge>
                </div>

                <ul className="flex-1 space-y-1.5 mt-4 text-xs">
                  {tier.features.slice(0, 5).map((feature) => (
                    <li key={feature} className="flex items-start gap-1.5">
                      <Check className="h-3 w-3 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full mt-4"
                  variant={isPopular ? "default" : current ? "outline" : "secondary"}
                  size="sm"
                  onClick={() => handleUpgrade(tier)}
                  disabled={current || loading === tier.tier_id || (!upgrade && tier.price > 0)}
                >
                  {loading === tier.tier_id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : current ? (
                    "Current Plan"
                  ) : upgrade ? (
                    "Upgrade"
                  ) : tier.price === 0 ? (
                    "Free Plan"
                  ) : (
                    "Downgrade"
                  )}
                </Button>
              </div>
            );
          })}
        </div>

        {/* Footer note */}
        <p className="text-center text-xs text-muted-foreground mt-4">
          All plans include a 7-day money-back guarantee. Cancel anytime.
        </p>
      </DialogContent>
    </Dialog>
  );
}
