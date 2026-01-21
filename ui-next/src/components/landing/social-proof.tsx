import { Shield, Lock, Globe, CheckCircle } from "lucide-react";

/**
 * Trust signals configuration
 * These badges display security and compliance indicators to build credibility
 */
const trustSignals = [
  {
    icon: Lock,
    text: "256-bit SSL Encryption",
    description: "All data encrypted in transit",
  },
  {
    icon: Shield,
    text: "Bank-Grade Security",
    description: "Enterprise-level protection",
  },
  {
    icon: Globe,
    text: "GDPR Compliant",
    description: "Privacy by design",
  },
  {
    icon: CheckCircle,
    text: "No API Key Exposure",
    description: "Keys never leave our servers",
  },
];

/**
 * SocialProof component displays trust signals and security badges
 * Positioned below the hero to reduce purchase anxiety
 */
export function SocialProof() {
  return (
    <section className="py-12 border-y bg-background/50">
      <div className="container mx-auto px-4">
        {/* Trust header */}
        <p className="text-center text-sm text-muted-foreground mb-6">
          Trusted by traders worldwide
        </p>

        {/* Trust signal badges */}
        <div className="flex flex-wrap justify-center gap-6 md:gap-12">
          {trustSignals.map((signal) => (
            <div
              key={signal.text}
              className="flex items-center gap-2 text-sm group"
              title={signal.description}
            >
              <signal.icon className="w-4 h-4 text-green-500 group-hover:scale-110 transition-transform" />
              <span className="text-foreground/80">{signal.text}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
