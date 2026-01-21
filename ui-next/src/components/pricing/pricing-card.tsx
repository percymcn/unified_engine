"use client";

import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useRouter } from "next/navigation";
import { useState } from "react";

interface Plan {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  ctaHref: string;
  highlighted: boolean;
}

interface PricingCardProps {
  plan: Plan;
}

export function PricingCard({ plan }: PricingCardProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (plan.name === "Free") {
      router.push(plan.ctaHref);
      return;
    }

    // Pro plan - need to check auth and create checkout
    setLoading(true);
    try {
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: "pro" }),
      });

      if (response.status === 401) {
        // Not logged in - redirect to login with return URL
        router.push("/login?redirect=/pricing&upgrade=pro");
        return;
      }

      const data = await response.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        console.error("No checkout URL returned");
      }
    } catch (error) {
      console.error("Checkout error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className={plan.highlighted ? "border-primary shadow-lg" : ""}>
      {plan.highlighted && (
        <div className="bg-primary text-primary-foreground text-center py-1 text-sm font-medium rounded-t-lg">
          Most Popular
        </div>
      )}
      <CardHeader>
        <CardTitle className="text-2xl">{plan.name}</CardTitle>
        <CardDescription>{plan.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-6">
          <span className="text-4xl font-bold">{plan.price}</span>
          <span className="text-muted-foreground ml-2">/{plan.period}</span>
        </div>
        <ul className="space-y-3">
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-center gap-2">
              <Check className="h-5 w-5 text-primary flex-shrink-0" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </CardContent>
      <CardFooter>
        <Button
          className="w-full"
          variant={plan.highlighted ? "default" : "outline"}
          onClick={handleClick}
          disabled={loading}
        >
          {loading ? "Loading..." : plan.cta}
        </Button>
      </CardFooter>
    </Card>
  );
}
