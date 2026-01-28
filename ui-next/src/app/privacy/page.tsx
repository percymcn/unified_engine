import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy | Tradeflow",
  description: "Tradeflow Privacy Policy - Learn how we collect, use, and protect your data.",
};

export default function PrivacyPage() {
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
        <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-muted-foreground mb-8">Last updated: January 28, 2026</p>

        <div className="prose dark:prose-invert max-w-none">
          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">1. Introduction</h2>
            <p className="text-muted-foreground mb-4">
              Tradeflow (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) respects your privacy and is committed to protecting your personal data. This privacy policy explains how we collect, use, and safeguard your information when you use our service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">2. Information We Collect</h2>

            <h3 className="text-lg font-medium mb-2 mt-4">Account Information</h3>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Email address</li>
              <li>Username</li>
              <li>Password (encrypted)</li>
              <li>Profile information (optional)</li>
            </ul>

            <h3 className="text-lg font-medium mb-2 mt-4">Broker Credentials</h3>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Broker API keys and tokens (AES-256 encrypted)</li>
              <li>Account identifiers</li>
              <li>OAuth tokens (where applicable)</li>
            </ul>

            <h3 className="text-lg font-medium mb-2 mt-4">Usage Data</h3>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Trading signals received and processed</li>
              <li>Trade execution history</li>
              <li>Service usage patterns</li>
              <li>IP address and device information</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">3. How We Use Your Information</h2>
            <p className="text-muted-foreground mb-4">We use your information to:</p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Provide and maintain the Service</li>
              <li>Execute trades on your behalf via connected brokers</li>
              <li>Process payments and manage subscriptions</li>
              <li>Send service-related communications</li>
              <li>Improve our Service and develop new features</li>
              <li>Detect and prevent fraud or abuse</li>
              <li>Comply with legal obligations</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">4. Data Security</h2>
            <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 mb-4">
              <p className="font-medium text-primary mb-2">Security Measures</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>AES-256 encryption for all broker credentials</li>
                <li>TLS/SSL encryption for all data in transit</li>
                <li>Regular security audits and penetration testing</li>
                <li>SOC 2 compliant infrastructure</li>
              </ul>
            </div>
            <p className="text-muted-foreground">
              We implement industry-standard security measures to protect your data. However, no method of transmission over the Internet is 100% secure, and we cannot guarantee absolute security.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">5. Data Sharing</h2>
            <p className="text-muted-foreground mb-4">We do not sell your personal data. We may share data with:</p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li><strong>Broker APIs:</strong> To execute trades on your behalf</li>
              <li><strong>Payment processors:</strong> To process subscription payments (Stripe)</li>
              <li><strong>Cloud providers:</strong> For hosting and infrastructure</li>
              <li><strong>Legal authorities:</strong> When required by law</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">6. Data Retention</h2>
            <p className="text-muted-foreground mb-4">We retain your data for:</p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li><strong>Account data:</strong> Until you delete your account</li>
              <li><strong>Trade history:</strong> 2 years for analysis and compliance</li>
              <li><strong>Webhook logs:</strong> 90 days</li>
              <li><strong>Broker credentials:</strong> Deleted immediately upon account disconnection</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">7. Your Rights</h2>
            <p className="text-muted-foreground mb-4">You have the right to:</p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Access your personal data</li>
              <li>Correct inaccurate data</li>
              <li>Request deletion of your data</li>
              <li>Export your data</li>
              <li>Withdraw consent for marketing communications</li>
            </ul>
            <p className="text-muted-foreground mt-4">
              To exercise these rights, contact us at{" "}
              <a href="mailto:privacy@tradeflow.com" className="text-primary hover:underline">
                privacy@tradeflow.com
              </a>
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">8. Cookies</h2>
            <p className="text-muted-foreground mb-4">We use essential cookies for:</p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Authentication and session management</li>
              <li>Security and fraud prevention</li>
              <li>User preferences</li>
            </ul>
            <p className="text-muted-foreground mt-4">
              We do not use third-party advertising or tracking cookies.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">9. International Data Transfers</h2>
            <p className="text-muted-foreground">
              Your data may be processed in countries outside your residence. We ensure appropriate safeguards are in place for such transfers in compliance with applicable data protection laws.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">10. Children&apos;s Privacy</h2>
            <p className="text-muted-foreground">
              Our Service is not intended for individuals under 18 years of age. We do not knowingly collect data from children.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">11. Changes to This Policy</h2>
            <p className="text-muted-foreground">
              We may update this privacy policy from time to time. We will notify you of significant changes via email or through the Service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold mb-4">12. Contact Us</h2>
            <p className="text-muted-foreground">
              For privacy-related questions or to exercise your rights, contact us at:{" "}
              <a href="mailto:privacy@tradeflow.com" className="text-primary hover:underline">
                privacy@tradeflow.com
              </a>
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
