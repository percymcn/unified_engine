"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { Check, ExternalLink } from "lucide-react";

interface BillingStatus {
  tier: string;
  status: string;
  ends_at: string | null;
  can_manage: boolean;
}

function BillingPageContent() {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const searchParams = useSearchParams();
  const { toast } = useToast();

  useEffect(() => {
    // Check for success/cancel params from Stripe redirect
    const success = searchParams.get("success");
    const canceled = searchParams.get("canceled");

    if (success === "true") {
      toast({
        title: "Subscription activated!",
        description: "Welcome to Tradeflow Pro. Your account has been upgraded.",
      });
    } else if (canceled === "true") {
      toast({
        title: "Subscription canceled",
        description: "Your subscription has been canceled.",
        variant: "destructive",
      });
    }

    fetchBillingStatus();
  }, [searchParams, toast]);

  const fetchBillingStatus = async () => {
    try {
      const response = await fetch("/api/billing/status");
      if (response.ok) {
        const data = await response.json();
        setBilling(data);
      }
    } catch (error) {
      console.error("Failed to fetch billing status:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    setPortalLoading(true);
    try {
      const response = await fetch("/api/billing/portal");
      const data = await response.json();
      if (data.portal_url) {
        window.location.href = data.portal_url;
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to open billing portal",
        variant: "destructive",
      });
    } finally {
      setPortalLoading(false);
    }
  };

  const handleUpgrade = async () => {
    setPortalLoading(true);
    try {
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: "pro" }),
      });
      const data = await response.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to start checkout",
        variant: "destructive",
      });
    } finally {
      setPortalLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Billing</h1>
          <p className="text-muted-foreground">Manage your subscription and billing</p>
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-10 w-40" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const isPro = billing?.tier === "pro" && billing?.status === "active";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Billing</h1>
        <p className="text-muted-foreground">Manage your subscription and billing</p>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Current Plan
            <Badge variant={isPro ? "default" : "secondary"}>
              {billing?.tier === "pro" ? "Pro" : "Free"}
            </Badge>
          </CardTitle>
          <CardDescription>
            {isPro
              ? "You have access to all Pro features"
              : "Upgrade to Pro for unlimited broker connections"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isPro ? (
            <>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4 text-primary" />
                Unlimited broker connections
              </div>
              {billing?.ends_at && (
                <p className="text-sm text-muted-foreground">
                  {billing.status === "canceling"
                    ? `Access until ${new Date(billing.ends_at).toLocaleDateString()}`
                    : `Renews on ${new Date(billing.ends_at).toLocaleDateString()}`}
                </p>
              )}
              {billing?.can_manage && (
                <Button
                  variant="outline"
                  onClick={handleManageSubscription}
                  disabled={portalLoading}
                >
                  {portalLoading ? "Loading..." : "Manage Subscription"}
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Button>
              )}
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4" />
                1 broker connection
              </div>
              <Button onClick={handleUpgrade} disabled={portalLoading}>
                {portalLoading ? "Loading..." : "Upgrade to Pro - $29/month"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Plan Comparison */}
      <Card>
        <CardHeader>
          <CardTitle>Plan Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="font-medium">Feature</div>
            <div className="font-medium text-center">Free</div>
            <div className="font-medium text-center">Pro</div>

            <div>Broker connections</div>
            <div className="text-center">1</div>
            <div className="text-center text-primary">Unlimited</div>

            <div>Signal routing</div>
            <div className="text-center">Basic</div>
            <div className="text-center text-primary">Advanced</div>

            <div>Webhook support</div>
            <div className="text-center"><Check className="h-4 w-4 mx-auto" /></div>
            <div className="text-center"><Check className="h-4 w-4 mx-auto text-primary" /></div>

            <div>Multi-account routing</div>
            <div className="text-center text-muted-foreground">-</div>
            <div className="text-center"><Check className="h-4 w-4 mx-auto text-primary" /></div>

            <div>Support</div>
            <div className="text-center">Community</div>
            <div className="text-center text-primary">Email</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function BillingPageSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Billing</h1>
        <p className="text-muted-foreground">Manage your subscription and billing</p>
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-40" />
        </CardContent>
      </Card>
    </div>
  );
}

export default function BillingSettingsPage() {
  return (
    <Suspense fallback={<BillingPageSkeleton />}>
      <BillingPageContent />
    </Suspense>
  );
}
