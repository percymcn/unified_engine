import type { Metadata } from "next";

import { LandingHeader } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { SocialProof } from "@/components/landing/social-proof";
import { Features } from "@/components/landing/features";
import { Stats } from "@/components/landing/stats";
import { HowItWorks } from "@/components/landing/how-it-works";
import { DemoSection } from "@/components/landing/demo-section";
import { PricingSection } from "@/components/landing/pricing-section";
import { Comparison } from "@/components/landing/comparison";

export const metadata: Metadata = {
  title: "Tradeflow - Route TradingView Signals to Any Broker",
  description:
    "Automatically route your TradingView alerts to TradeLocker, Tradovate, TopStep, and MetaTrader. Start free.",
};

export default function Home() {
  return (
    <>
      <LandingHeader />
      <main>
        <Hero />
        <SocialProof />
        <Features />
        <HowItWorks />
        <DemoSection />
        <Stats />
        <PricingSection />
        <Comparison />
      </main>
    </>
  );
}
