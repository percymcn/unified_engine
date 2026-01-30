"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { Check, ExternalLink, Crown, Zap, Sparkles, Building2 } from "lucide-react";
import { normalizeTierId } from "@/lib/pricing";

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
        description: "Your account has been upgraded. Enjoy your new features!",
      });
      // Clear the URL params
      window.history.replaceState({}, '', '/dashboard/settings/billing');
    } else if (canceled === "true") {
      toast({
        title: "Checkout canceled",
        description: "Your checkout was canceled. No charges were made.",
        variant: "destructive",
      });
      window.history.replaceState({}, '', '/dashboard/settings/billing');
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

  const handleUpgrade = async (tierId?: string) => {
    setPortalLoading(true);
    try {
      // Use specified tier or default to tier_1
      const targetTierId = tierId || "tier_1";
      const targetPlan = plans.find((p) => p.id === targetTierId);
      if (!targetPlan) {
        toast({
          title: "Error",
          description: "Selected plan not available",
          variant: "destructive",
        });
        return;
      }

      // Use the upgrade endpoint which handles both new and existing subscribers
      const response = await fetch("/api/billing/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: 'include',
        body: JSON.stringify({ tier_id: targetTierId }),
      });
      const data = await response.json();

      if (!response.ok) {
        toast({
          title: "Error",
          description: data.detail || data.error || "Failed to process upgrade",
          variant: "destructive",
        });
        return;
      }

      // If checkout URL provided, redirect to Stripe
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }

      // Upgrade was processed immediately
      if (data.success) {
        toast({
          title: "Upgrade Successful!",
          description: data.message || `You are now on the ${targetPlan.name} plan.`,
        });
        // Refresh billing data to show new tier
        fetchBillingData();
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to process upgrade",
        variant: "destructive",
      });
    } finally {
      setPortalLoading(false);
    }
  };

  // Get icon for each tier
  const getTierIcon = (tierId: string) => {
    switch (tierId) {
      case "tier_1":
        return <Zap className="h-5 w-5" />;
      case "tier_2":
        return <Sparkles className="h-5 w-5" />;
      case "tier_3":
        return <Crown className="h-5 w-5" />;
      case "tier_4":
        return <Building2 className="h-5 w-5" />;
      default:
        return null;
    }
  };

  // Check if a plan is an upgrade from current
  const isUpgrade = (planId: string) => {
    const normalizedCurrent = normalizeTierId(currentTier);
    const tierOrder = ["free", "tier_1", "tier_2", "tier_3", "tier_4"];
    const currentIndex = tierOrder.indexOf(normalizedCurrent);
    const planIndex = tierOrder.indexOf(planId);
    return planIndex > currentIndex;
  };

  // Check if a plan is a downgrade from current
  const isDowngrade = (planId: string) => {
    const normalizedCurrent = normalizeTierId(currentTier);
    const tierOrder = ["free", "tier_1", "tier_2", "tier_3", "tier_4"];
    const currentIndex = tierOrder.indexOf(normalizedCurrent);
    const planIndex = tierOrder.indexOf(planId);
    return planIndex < currentIndex && planIndex > 0; // Can't downgrade to free
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
            {billing?.status === "canceling" && (
              <Badge variant="destructive">Canceling</Badge>
            )}
            {billing?.status === "past_due" && (
              <Badge variant="destructive">Payment Due</Badge>
            )}
          </CardTitle>
          <CardDescription>
            {isPaid
              ? `You have access to ${currentPlan?.broker_limit || billing?.broker_limit || 1} broker connection${(currentPlan?.broker_limit || 1) > 1 ? "s" : ""}`
              : "Upgrade to unlock more broker connections and premium features"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isPaid ? (
            <>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-primary" />
                  <span>{currentPlan?.broker_limit || billing?.broker_limit || 1} broker connection{(currentPlan?.broker_limit || 1) > 1 ? "s" : ""}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-primary" />
                  <span>Using {billing?.brokers_used || 0} of {billing?.broker_limit || 1} connections</span>
                </div>
              </div>
              {billing?.ends_at && (
                <p className="text-sm text-muted-foreground">
                  {billing.status === "canceling"
                    ? `Access until ${new Date(billing.ends_at).toLocaleDateString()}`
                    : `Renews on ${new Date(billing.ends_at).toLocaleDateString()}`}
                </p>
              )}
              {billing?.status === "past_due" && (
                <p className="text-sm text-destructive">
                  Your payment is past due. Please update your payment method to continue using premium features.
                </p>
              )}
              <div className="flex gap-2 flex-wrap">
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
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4" />
                1 broker connection (limited features)
              </div>
              <p className="text-sm text-muted-foreground">
                Upgrade to a paid plan to unlock unlimited signals, advanced risk management, and more broker connections.
              </p>
              {upgradePlan && (
                <Button onClick={() => handleUpgrade()} disabled={portalLoading}>
                  {portalLoading
                    ? "Loading..."
                    : `Upgrade to ${upgradePlan.name} - ${upgradePlan.price_display}`}
                </Button>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Available Plans */}
      {plans.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Available Plans</CardTitle>
            <CardDescription>
              Choose a plan that fits your trading needs. Upgrade or change your plan anytime.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {plans
                .filter((plan) => plan.id.startsWith("tier_"))
                .sort((a, b) => a.monthly_price - b.monthly_price)
                .map((plan) => {
                  const normalizedCurrent = normalizeTierId(currentTier);
                  const isCurrentPlan = plan.id === normalizedCurrent;
                  const canUpgrade = isUpgrade(plan.id);
                  const canDowngrade = isDowngrade(plan.id);

                  return (
                    <div
                      key={plan.id}
                      className={`relative rounded-lg border p-4 flex flex-col ${
                        isCurrentPlan
                          ? "border-primary bg-primary/5 ring-2 ring-primary"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {isCurrentPlan && (
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                          <Badge variant="default" className="text-xs">
                            Current Plan
                          </Badge>
                        </div>
                      )}

                      <div className="flex items-center gap-2 mb-2">
                        <div className={`p-2 rounded-full ${isCurrentPlan ? "bg-primary/20" : "bg-muted"}`}>
                          {getTierIcon(plan.id)}
                        </div>
                        <h3 className="font-semibold text-lg">{plan.name}</h3>
                      </div>

                      <div className="mb-4">
                        <span className="text-2xl font-bold">{plan.price_display}</span>
                        <span className="text-muted-foreground text-sm">/month</span>
                      </div>

                      <ul className="space-y-2 mb-4 flex-1">
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-primary flex-shrink-0" />
                          <span>{plan.broker_limit} broker connection{plan.broker_limit > 1 ? "s" : ""}</span>
                        </li>
                        {plan.features.slice(0, 3).map((feature, idx) => (
                          <li key={idx} className="flex items-center gap-2 text-sm">
                            <Check className="h-4 w-4 text-primary flex-shrink-0" />
                            <span>{feature}</span>
                          </li>
                        ))}
                      </ul>

                      {isCurrentPlan ? (
                        <Button variant="outline" disabled className="w-full">
                          Current Plan
                        </Button>
                      ) : canUpgrade ? (
                        <Button
                          onClick={() => handleUpgrade(plan.id)}
                          disabled={portalLoading}
                          className="w-full"
                        >
                          {portalLoading ? "Loading..." : `Upgrade to ${plan.name}`}
                        </Button>
                      ) : canDowngrade && billing?.can_manage ? (
                        <Button
                          variant="outline"
                          onClick={handleManageSubscription}
                          disabled={portalLoading}
                          className="w-full"
                        >
                          {portalLoading ? "Loading..." : "Manage Plan"}
                        </Button>
                      ) : (
                        <Button
                          onClick={() => handleUpgrade(plan.id)}
                          disabled={portalLoading}
                          className="w-full"
                        >
                          {portalLoading ? "Loading..." : "Select Plan"}
                        </Button>
                      )}
                    </div>
                  );
                })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Plan Features Comparison */}
      {plans.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Feature Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 pr-4">Feature</th>
                    <th className="text-center py-2 px-2">Free</th>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan) => (
                        <th key={plan.id} className="text-center py-2 px-2">
                          {plan.name}
                        </th>
                      ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-2 pr-4">Broker connections</td>
                    <td className="text-center py-2 px-2">1</td>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan) => (
                        <td key={plan.id} className="text-center py-2 px-2 text-primary font-medium">
                          {plan.broker_limit}
                        </td>
                      ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-2 pr-4">Signal routing</td>
                    <td className="text-center py-2 px-2">Basic</td>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan) => (
                        <td key={plan.id} className="text-center py-2 px-2 text-primary">
                          Advanced
                        </td>
                      ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-2 pr-4">Webhook support</td>
                    <td className="text-center py-2 px-2">
                      <Check className="h-4 w-4 mx-auto" />
                    </td>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan) => (
                        <td key={plan.id} className="text-center py-2 px-2">
                          <Check className="h-4 w-4 mx-auto text-primary" />
                        </td>
                      ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-2 pr-4">Multi-account routing</td>
                    <td className="text-center py-2 px-2 text-muted-foreground">-</td>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan) => (
                        <td key={plan.id} className="text-center py-2 px-2">
                          <Check className="h-4 w-4 mx-auto text-primary" />
                        </td>
                      ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-2 pr-4">AI Strategy Suite</td>
                    <td className="text-center py-2 px-2 text-muted-foreground">-</td>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan, idx) => (
                        <td key={plan.id} className="text-center py-2 px-2">
                          {idx >= 2 ? (
                            <Check className="h-4 w-4 mx-auto text-primary" />
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                      ))}
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Support</td>
                    <td className="text-center py-2 px-2">Community</td>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan, idx) => (
                        <td key={plan.id} className="text-center py-2 px-2 text-primary">
                          {idx >= 3 ? "Priority" : idx >= 2 ? "Email" : "Email"}
                        </td>
                      ))}
                  </tr>
                </tbody>
              </table>
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
