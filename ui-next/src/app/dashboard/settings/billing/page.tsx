"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { Check, ExternalLink } from "lucide-react";

interface PlanInfo {
  id: string;
  name: string;
  monthly_price: number; // cents
  price_display: string;
  features: string[];
  stripe_price_id: string | null;
  broker_limit: number;
}

interface BillingStatus {
  tier: string;
  tier_name: string;
  status: string;
  broker_limit: number;
  brokers_used: number;
  ends_at: string | null;
  can_manage: boolean;
}

function BillingPageContent() {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [plans, setPlans] = useState<PlanInfo[]>([]);
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

    fetchBillingData();
  }, [searchParams, toast]);

  const fetchBillingData = async () => {
    try {
      const [billingRes, plansRes] = await Promise.all([
        fetch("/api/billing/status", { credentials: 'include' }),
        fetch("/api/billing/plans", { credentials: 'include' }),
      ]);

      if (billingRes.ok) {
        const billingData = await billingRes.json();
        setBilling(billingData);
      }

      if (plansRes.ok) {
        const plansData = await plansRes.json();
        setPlans(plansData.plans || []);
      }
    } catch (error) {
      console.error("Failed to fetch billing data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    setPortalLoading(true);
    try {
      const response = await fetch("/api/billing/portal", { credentials: 'include' });
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
      // Get the lowest paid tier (tier_1)
      const tier1 = plans.find((p) => p.id === "tier_1");
      if (!tier1) {
        toast({
          title: "Error",
          description: "No upgrade plans available",
          variant: "destructive",
        });
        return;
      }

      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: 'include',
        body: JSON.stringify({ tier_id: tier1.id }),
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

  const currentTier = billing?.tier || "free";
  const isPaid = currentTier !== "free" && billing?.status === "active";
  
  // Get current plan info from plans list
  const currentPlan = plans.find((p) => p.id === currentTier);
  // Get lowest paid tier for upgrade button
  const upgradePlan = plans.find((p) => p.id.startsWith("tier_")) || plans[0];

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
            <Badge variant={isPaid ? "default" : "secondary"}>
              {currentPlan?.name || billing?.tier_name || "Free"}
            </Badge>
          </CardTitle>
          <CardDescription>
            {isPaid
              ? `You have access to ${currentPlan?.broker_limit || billing?.broker_limit || 1} broker connection${(currentPlan?.broker_limit || 1) > 1 ? "s" : ""}`
              : "Upgrade to unlock more broker connections"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isPaid ? (
            <>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4 text-primary" />
                {currentPlan?.broker_limit || billing?.broker_limit || 1} broker connection{(currentPlan?.broker_limit || 1) > 1 ? "s" : ""}
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
              {upgradePlan && (
                <Button onClick={handleUpgrade} disabled={portalLoading}>
                  {portalLoading
                    ? "Loading..."
                    : `Upgrade to ${upgradePlan.name} - ${upgradePlan.price_display}`}
                </Button>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Plan Comparison */}
      {plans.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Plan Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="font-medium">Feature</div>
              <div className="font-medium text-center">Free</div>
              <div className="font-medium text-center">Paid Plans</div>

              <div>Broker connections</div>
              <div className="text-center">1</div>
              <div className="text-center text-primary">
                {plans.filter((p) => p.id.startsWith("tier_")).map((p) => p.broker_limit).join(", ")}
              </div>

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
      )}
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
