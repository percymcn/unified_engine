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
            Start with 50 free trades or 7 days - No credit card required
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
        <div className="mt-16 max-w-6xl mx-auto">
          <h3 className="text-2xl font-bold text-center mb-8">
            Compare All Features
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left py-4 px-4 font-semibold">Feature</th>
                  {tiers.map((tier) => (
                    <th
                      key={tier.tier_id}
                      className={cn(
                        "text-center py-4 px-3 font-semibold",
                        tier.tier_id === "tier_3" && "bg-primary/10"
                      )}
                    >
                      <div>{tier.name}</div>
                      <div className="text-xs font-normal text-muted-foreground mt-1">
                        {tier.price === 0 ? "Free" : `${getDisplayPrice(tier)}/mo`}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Broker Connections */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Broker Connections</td>
                  {tiers.map((tier) => (
                    <td key={tier.tier_id} className={cn("text-center py-3 px-3", tier.tier_id === "tier_3" && "bg-primary/5")}>
                      <span className="font-semibold text-primary">{tier.brokers}</span>
                    </td>
                  ))}
                </tr>

                {/* Signals per Day */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Signals per Day</td>
                  {tiers.map((tier) => (
                    <td key={tier.tier_id} className={cn("text-center py-3 px-3", tier.tier_id === "tier_3" && "bg-primary/5")}>
                      <span className="font-semibold">
                        {tier.signalsPerDay === -1 ? "Unlimited" : tier.signalsPerDay}
                      </span>
                    </td>
                  ))}
                </tr>

                {/* Webhooks */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Webhooks</td>
                  {tiers.map((tier) => (
                    <td key={tier.tier_id} className={cn("text-center py-3 px-3", tier.tier_id === "tier_3" && "bg-primary/5")}>
                      <span className="font-semibold">
                        {tier.webhooks === -1 ? "Unlimited" : tier.webhooks}
                      </span>
                    </td>
                  ))}
                </tr>

                {/* AI Signal Guards */}
                <tr className="border-b bg-muted/30">
                  <td className="py-3 px-4 font-medium">AI Signal Guards</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Staleness only</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">All 5 guards</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">+ Custom</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">+ Custom</span>
                  </td>
                </tr>

                {/* Risk Management */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Risk Management</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Daily limits</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">Full suite</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">+ Per-symbol</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">+ Per-account</span>
                  </td>
                </tr>

                {/* Position Sizing */}
                <tr className="border-b bg-muted/30">
                  <td className="py-3 px-4 font-medium">Position Sizing</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Fixed lots</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Fixed lots</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">% of balance</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">Risk-based</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">All methods</span>
                  </td>
                </tr>

                {/* Signal Routing */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Signal Routing</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Basic</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Basic</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">All accounts</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">Rule-based</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">Strategy-based</span>
                  </td>
                </tr>

                {/* Symbol Mapping */}
                <tr className="border-b bg-muted/30">
                  <td className="py-3 px-4 font-medium">Symbol Mapping</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">+ Aliases</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">+ Bulk import</span>
                  </td>
                </tr>

                {/* Account Groups */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Account Groups</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="font-semibold">2</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <span className="font-semibold">Unlimited</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="font-semibold">+ Nested</span>
                  </td>
                </tr>

                {/* Analytics */}
                <tr className="border-b bg-muted/30">
                  <td className="py-3 px-4 font-medium">Analytics</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Basic</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Basic</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Basic</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">Full suite</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">+ Export</span>
                  </td>
                </tr>

                {/* API Access */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">API Access</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-muted-foreground">-</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">Higher limits</span>
                  </td>
                </tr>

                {/* Webhook Log Retention */}
                <tr className="border-b bg-muted/30">
                  <td className="py-3 px-4 font-medium">Webhook Log Retention</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="font-semibold">7 days</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="font-semibold">7 days</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="font-semibold">14 days</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <span className="font-semibold">30 days</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="font-semibold">90 days</span>
                  </td>
                </tr>

                {/* Notifications */}
                <tr className="border-b">
                  <td className="py-3 px-4 font-medium">Notifications</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">In-app</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">In-app</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">+ Email</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <span className="text-xs">+ Email</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <Check className="h-4 w-4 text-green-500 mx-auto" />
                    <span className="text-xs block">All channels</span>
                  </td>
                </tr>

                {/* Support */}
                <tr className="border-b bg-muted/30">
                  <td className="py-3 px-4 font-medium">Support</td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Community</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Email (48h)</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">Email (24h)</span>
                  </td>
                  <td className={cn("text-center py-3 px-3 bg-primary/5")}>
                    <span className="text-xs">Priority (12h)</span>
                  </td>
                  <td className={cn("text-center py-3 px-3")}>
                    <span className="text-xs">+ Live chat</span>
                  </td>
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
            <a href="mailto:support@mytradeflow.app">Contact Sales</a>
          </Button>
        </div>
      </div>
    </section>
  );
}
