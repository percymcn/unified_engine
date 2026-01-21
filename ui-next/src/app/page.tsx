import type { Metadata } from "next";

import { LandingHeader } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { SocialProof } from "@/components/landing/social-proof";
import { Stats } from "@/components/landing/stats";
import { HowItWorks } from "@/components/landing/how-it-works";
import { DemoSection } from "@/components/landing/demo-section";

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
        {/* Features section will be added by 14-02 */}
        <HowItWorks />
        <DemoSection />
        <Stats />
      </main>
    </>
  );
}
