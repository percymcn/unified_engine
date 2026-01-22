"use client";

import { useState } from "react";
import { Check, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { PricingCard } from "@/components/pricing/pricing-card";
import {
  getAllTiers,
  formatPrice,
  type PricingTier,
} from "@/lib/pricing";

// Get all tiers from centralized config
const tiers = getAllTiers();

export function PricingSection() {
  const [isAnnual, setIsAnnual] = useState(false);

  // Calculate annual price (20% discount)
  const getDisplayPrice = (tier: PricingTier) => {
    if (tier.price === 0) return "Free";
    const monthlyPrice = tier.price;
    if (isAnnual) {
      const annualMonthly = Math.round(monthlyPrice * 0.8);
      return formatPrice(annualMonthly);
    }
    return formatPrice(monthlyPrice);
  };

  return (
    <section id="pricing" className="py-20 bg-background">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto text-lg">
            Start free, upgrade when you need more. No hidden fees, cancel anytime.
          </p>

          {/* Free Trial Callout */}
          <div className="inline-flex items-center gap-2 bg-green-500/10 text-green-600 dark:text-green-400 px-4 py-2 rounded-full text-sm font-medium mb-6">
            <Sparkles className="h-4 w-4" />
            Start with 100 free trades - No credit card required
          </div>

          {/* Annual/Monthly Toggle */}
          <div className="flex items-center justify-center gap-3">
            <Label
              htmlFor="billing-toggle"
              className={cn(
                "text-sm cursor-pointer",
                !isAnnual ? "font-semibold" : "text-muted-foreground"
              )}
            >
              Monthly
            </Label>
            <Switch
              id="billing-toggle"
              checked={isAnnual}
              onCheckedChange={setIsAnnual}
            />
            <Label
              htmlFor="billing-toggle"
              className={cn(
                "text-sm cursor-pointer",
                isAnnual ? "font-semibold" : "text-muted-foreground"
              )}
            >
              Annual
            </Label>
            {isAnnual && (
              <Badge variant="secondary" className="bg-green-500/10 text-green-600 dark:text-green-400">
                Save 20%
              </Badge>
            )}
          </div>
        </div>

        {/* Pricing Cards Grid - 5 tiers (free + 4 paid) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 max-w-7xl mx-auto">
          {tiers.map((tier) => (
            <PricingCard
              key={tier.tier_id}
              tier={{
                ...tier,
                // Override price display for annual if needed
                price: isAnnual && tier.price > 0 ? Math.round(tier.price * 0.8) : tier.price,
              }}
              isPopular={tier.tier_id === "tier_3"}
              isAuthenticated={false}
            />
          ))}
        </div>

        {/* Feature Comparison Table */}
        <div className="mt-16 max-w-5xl mx-auto">
          <h3 className="text-2xl font-bold text-center mb-8">
            Compare Plans
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-4 px-4 font-semibold">Feature</th>
                  {tiers.map((tier) => (
                    <th
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2 font-semibold",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      {tier.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Broker Connections */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Broker Connections</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      <span className="font-semibold">{tier.brokers}</span>
                    </td>
                  ))}
                </tr>

                {/* Monthly Price */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Price</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      <span className="font-semibold">{getDisplayPrice(tier)}</span>
                      {tier.price > 0 && (
                        <span className="text-muted-foreground text-xs">/mo</span>
                      )}
                    </td>
                  ))}
                </tr>

                {/* Unlimited Signals */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Unlimited Signals</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      <Check className="h-5 w-5 text-green-500 mx-auto" />
                    </td>
                  ))}
                </tr>

                {/* Real-time Execution */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Real-time Execution</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      <Check className="h-5 w-5 text-green-500 mx-auto" />
                    </td>
                  ))}
                </tr>

                {/* Symbol Mapping */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Symbol Mapping</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      {tier.tier_id === "free" || tier.tier_id === "tier_1" ? (
                        <span className="text-muted-foreground">-</span>
                      ) : (
                        <Check className="h-5 w-5 text-green-500 mx-auto" />
                      )}
                    </td>
                  ))}
                </tr>

                {/* Risk Management */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Risk Management</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      {tier.tier_id === "tier_3" || tier.tier_id === "tier_4" ? (
                        <Check className="h-5 w-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                  ))}
                </tr>

                {/* Position Sizing */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Position Sizing</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      {tier.tier_id === "tier_3" || tier.tier_id === "tier_4" ? (
                        <Check className="h-5 w-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                  ))}
                </tr>

                {/* Multi-Account Routing */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Multi-Account Routing</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      {tier.tier_id === "tier_4" ? (
                        <Check className="h-5 w-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                  ))}
                </tr>

                {/* Priority Support */}
                <tr className="border-b">
                  <td className="py-4 px-4 text-sm">Priority Support</td>
                  {tiers.map((tier) => (
                    <td
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-2",
                        tier.tier_id === "tier_3" && "bg-primary/5"
                      )}
                    >
                      {tier.tier_id === "tier_3" || tier.tier_id === "tier_4" ? (
                        <Check className="h-5 w-5 text-green-500 mx-auto" />
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="mt-12 text-center">
          <p className="text-muted-foreground mb-4">
            Not sure which plan is right for you?
          </p>
          <Button variant="outline" asChild>
            <a href="mailto:support@tradeflow.fluxeo.net">Contact Sales</a>
          </Button>
        </div>
      </div>
    </section>
  );
}
