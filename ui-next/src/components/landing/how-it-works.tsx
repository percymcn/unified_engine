import { Webhook, Settings, Link2, Zap } from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Webhook,
    title: "Create Your Webhook",
    description:
      "Sign up and get your unique webhook URL instantly. No complex setup required.",
  },
  {
    number: "02",
    icon: Settings,
    title: "Configure TradingView",
    description:
      "Paste your webhook URL into any TradingView alert. Works with any strategy.",
  },
  {
    number: "03",
    icon: Link2,
    title: "Connect Your Broker",
    description:
      "Add your broker API credentials. We support TradeLocker, Tradovate, TopStep, and MT4/5.",
  },
  {
    number: "04",
    icon: Zap,
    title: "Trade Automatically",
    description:
      "Your alerts now execute trades automatically. Sit back and let Tradeflow work.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-4">How It Works</h2>
        <p className="text-center text-muted-foreground mb-16 max-w-2xl mx-auto">
          Get started in under 5 minutes. No coding required.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8 max-w-5xl mx-auto">
          {steps.map((step, index) => (
            <div key={step.number} className="relative">
              {/* Connector line between steps (hidden on mobile and tablet) */}
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute top-8 left-full w-full h-0.5 bg-border -translate-x-1/2" />
              )}

              {/* Step content */}
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 text-primary mb-4">
                  <step.icon className="w-8 h-8" />
                </div>
                <div className="text-sm text-muted-foreground mb-2">
                  Step {step.number}
                </div>
                <h3 className="font-semibold mb-2">{step.title}</h3>
                <p className="text-sm text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
