import { Metadata } from "next";
import { PricingCard } from "@/components/pricing/pricing-card";

export const metadata: Metadata = {
  title: "Pricing - Tradeflow",
  description: "Simple, transparent pricing. Start free, upgrade when you need more.",
};

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Perfect for getting started with automated trading.",
    features: [
      "1 broker connection",
      "Basic signal routing",
      "TradingView webhook support",
      "Real-time trade execution",
      "Community support",
    ],
    cta: "Get Started Free",
    ctaHref: "/register",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "per month",
    description: "For serious traders who need unlimited connections.",
    features: [
      "Unlimited broker connections",
      "Priority signal execution",
      "Advanced routing rules",
      "All broker SDKs supported",
      "Email support",
      "Webhook analytics",
      "Multi-account routing",
    ],
    cta: "Subscribe to Pro",
    ctaHref: "/api/billing/checkout",
    highlighted: true,
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/" className="text-xl font-bold">
            Tradeflow
          </a>
          <nav className="flex items-center gap-4">
            <a href="/login" className="text-sm text-muted-foreground hover:text-foreground">
              Log in
            </a>
            <a
              href="/register"
              className="text-sm bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
            >
              Sign up
            </a>
          </nav>
        </div>
      </header>

      {/* Pricing Section */}
      <main className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Start free and upgrade when you need more broker connections.
            No hidden fees, cancel anytime.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan) => (
            <PricingCard key={plan.name} plan={plan} />
          ))}
        </div>

        {/* FAQ or additional info */}
        <div className="mt-16 text-center">
          <h2 className="text-2xl font-semibold mb-4">
            Questions?
          </h2>
          <p className="text-muted-foreground">
            Email us at{" "}
            <a href="mailto:support@tradeflow.fluxeo.net" className="text-primary hover:underline">
              support@tradeflow.fluxeo.net
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
