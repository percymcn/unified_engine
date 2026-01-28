import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of Service | Tradeflow",
  description: "Tradeflow Terms of Service - Read our terms and conditions for using the platform.",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <Link href="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Back to Home
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-12 max-w-4xl">
        <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
        <p className="text-muted-foreground mb-8">Last updated: January 28, 2026</p>

        <div className="prose dark:prose-invert max-w-none">
          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">1. Acceptance of Terms</h2>
            <p className="text-muted-foreground mb-4">
              By accessing or using Tradeflow (&quot;the Service&quot;), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our Service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">2. Description of Service</h2>
            <p className="text-muted-foreground mb-4">
              Tradeflow is an automated trading signal routing service that connects trading signals from sources like TradingView to brokerage accounts. We facilitate the execution of trading signals but do not provide financial advice.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">3. Account Registration</h2>
            <p className="text-muted-foreground mb-4">
              To use our Service, you must create an account. You agree to:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Provide accurate and complete registration information</li>
              <li>Maintain the security of your account credentials</li>
              <li>Notify us immediately of any unauthorized access</li>
              <li>Be at least 18 years old or the age of majority in your jurisdiction</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">4. Trading Risks</h2>
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 mb-4">
              <p className="font-medium text-destructive mb-2">Important Risk Warning</p>
              <p className="text-sm text-muted-foreground">
                Trading financial instruments carries a high level of risk and may result in the loss of your invested capital. You should not invest more than you can afford to lose. Before trading, please consider your investment objectives, experience level, and risk tolerance.
              </p>
            </div>
            <p className="text-muted-foreground">
              Tradeflow is not a financial advisor. We do not provide trading signals, strategies, or investment advice. We only facilitate the routing of signals you choose to use.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">5. Service Availability</h2>
            <p className="text-muted-foreground mb-4">
              While we strive for 99.9% uptime, we do not guarantee uninterrupted access to the Service. We are not liable for:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Signal delays or failures due to network issues</li>
              <li>Broker API downtime or errors</li>
              <li>Market conditions affecting trade execution</li>
              <li>Scheduled maintenance periods</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">6. Payment Terms</h2>
            <p className="text-muted-foreground mb-4">
              Subscription fees are billed monthly or annually as selected. You agree to:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Pay all applicable fees on time</li>
              <li>Provide valid payment information</li>
              <li>Accept automatic renewals unless cancelled</li>
            </ul>
            <p className="text-muted-foreground mt-4">
              We offer a 7-day money-back guarantee on all paid plans. Refund requests must be submitted within 7 days of purchase.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">7. Prohibited Activities</h2>
            <p className="text-muted-foreground mb-4">You agree not to:</p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Use the Service for any illegal purpose</li>
              <li>Attempt to gain unauthorized access to our systems</li>
              <li>Share your account with others</li>
              <li>Reverse engineer or copy our software</li>
              <li>Use automated systems to abuse the Service</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">8. Limitation of Liability</h2>
            <p className="text-muted-foreground mb-4">
              To the maximum extent permitted by law, Tradeflow shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of profits, trading losses, or data loss.
            </p>
            <p className="text-muted-foreground">
              Our total liability shall not exceed the amount you paid us in the 12 months preceding the claim.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">9. Termination</h2>
            <p className="text-muted-foreground">
              We may terminate or suspend your account at any time for violation of these terms. You may cancel your subscription at any time through your account settings.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">10. Changes to Terms</h2>
            <p className="text-muted-foreground">
              We may update these terms from time to time. We will notify you of significant changes via email or through the Service. Continued use after changes constitutes acceptance.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">11. Contact</h2>
            <p className="text-muted-foreground">
              For questions about these terms, contact us at:{" "}
              <a href="mailto:legal@tradeflow.com" className="text-primary hover:underline">
                legal@tradeflow.com
              </a>
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
