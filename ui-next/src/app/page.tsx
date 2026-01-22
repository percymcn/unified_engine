import type { Metadata } from "next";

import { LandingHeader } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { PainPoints } from "@/components/landing/pain-points";
import { SocialProof } from "@/components/landing/social-proof";
import { Features } from "@/components/landing/features";
import { Stats } from "@/components/landing/stats";
import { HowItWorks } from "@/components/landing/how-it-works";
import { SignalFlowAnimation } from "@/components/landing/signal-flow-animation";
import { DemoSection } from "@/components/landing/demo-section";
import { PricingSection } from "@/components/landing/pricing-section";
import { Comparison } from "@/components/landing/comparison";
import { TestimonialsSection } from "@/components/landing/testimonials-section";
import { FAQ } from "@/components/landing/faq";
import { Footer } from "@/components/landing/footer";

export const metadata: Metadata = {
  title: "Tradeflow - Never Miss a Trade Again | Auto-Execute TradingView Signals",
  description:
    "Automatically route your TradingView alerts to TradeLocker, Tradovate, TopStep, and MetaTrader in <50ms. Start free, no credit card required.",
  openGraph: {
    title: "Tradeflow - Never Miss a Trade Again",
    description:
      "Auto-execute TradingView signals on any broker in <50ms. Trade while you sleep.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Tradeflow - Never Miss a Trade Again",
    description:
      "Auto-execute TradingView signals on any broker in <50ms. Trade while you sleep.",
  },
};

export default function Home() {
  return (
    <>
      <LandingHeader />
      <main>
        {/* Hero with urgency-focused messaging */}
        <Hero />

        {/* Pain points - before/after comparison */}
        <PainPoints />

        {/* Social proof and broker logos */}
        <SocialProof />

        {/* Feature cards with benefit-first language */}
        <Features />

        {/* How it works - 4 step process */}
        <HowItWorks />

        {/* Animated signal flow visualization */}
        <SignalFlowAnimation />

        {/* Demo section */}
        <DemoSection />

        {/* Stats bar */}
        <Stats />

        {/* Pricing with urgency */}
        <PricingSection />

        {/* Comparison table */}
        <Comparison />

        {/* Testimonials */}
        <TestimonialsSection />

        {/* FAQ */}
        <FAQ />
      </main>
      <Footer />
    </>
  );
}
