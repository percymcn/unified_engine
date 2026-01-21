import { Check, X } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Start routing signals today",
    features: [
      { text: "1 broker connection", included: true },
      { text: "TradingView webhooks", included: true },
      { text: "Basic signal routing", included: true },
      { text: "Community support", included: true },
      { text: "Unlimited connections", included: false },
      { text: "Priority execution", included: false },
    ],
    cta: "Get Started Free",
    ctaHref: "/register",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "Unlimited power for serious traders",
    features: [
      { text: "Unlimited broker connections", included: true },
      { text: "TradingView webhooks", included: true },
      { text: "Advanced routing rules", included: true },
      { text: "Priority email support", included: true },
      { text: "Priority execution", included: true },
      { text: "Webhook analytics", included: true },
    ],
    cta: "Start Pro Trial",
    ctaHref: "/api/billing/checkout",
    highlighted: true,
  },
];

export function PricingSection() {
  return (
    <section id="pricing" className="py-20 bg-background">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
          Simple, Transparent Pricing
        </h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto text-lg">
          Start free, upgrade when you need more. No hidden fees, cancel anytime.
        </p>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={cn(
                "relative rounded-2xl border bg-card p-8 shadow-sm transition-all hover:shadow-md",
                plan.highlighted && "ring-2 ring-primary"
              )}
            >
              {plan.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-primary text-primary-foreground text-xs font-semibold px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <p className="text-muted-foreground text-sm mb-4">
                  {plan.description}
                </p>
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-muted-foreground">{plan.period}</span>
                </div>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature.text} className="flex items-center gap-3">
                    {feature.included ? (
                      <Check className="h-5 w-5 text-green-500 shrink-0" />
                    ) : (
                      <X className="h-5 w-5 text-muted-foreground/50 shrink-0" />
                    )}
                    <span
                      className={cn(
                        "text-sm",
                        !feature.included && "text-muted-foreground"
                      )}
                    >
                      {feature.text}
                    </span>
                  </li>
                ))}
              </ul>

              <Button
                asChild
                variant={plan.highlighted ? "default" : "outline"}
                className="w-full"
                size="lg"
              >
                <Link href={plan.ctaHref}>{plan.cta}</Link>
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
