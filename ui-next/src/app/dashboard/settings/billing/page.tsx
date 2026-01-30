"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { Check, ExternalLink, Crown, Zap, Sparkles, Building2, CreditCard, Settings, ArrowUpRight } from "lucide-react";
import { normalizeTierId, getTierInfo, getAllTiers, formatPrice, type PricingTier } from "@/lib/pricing";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

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
  const [upgradeConfirm, setUpgradeConfirm] = useState<{
    open: boolean;
    targetPlan: PlanInfo | null;
    priceDiff: number;
  }>({ open: false, targetPlan: null, priceDiff: 0 });
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
      } else {
        toast({
          title: "Error",
          description: data.error || "No portal URL returned",
          variant: "destructive",
        });
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

  // Show upgrade confirmation dialog for existing paid users
  const showUpgradeConfirm = (tierId: string) => {
    const targetPlan = plans.find((p) => p.id === tierId);
    if (!targetPlan) return;

    const currentTier = billing?.tier || "free";
    const currentPlan = plans.find((p) => p.id === currentTier);
    const isPaidUser = currentTier !== "free" && billing?.status === "active";

    if (isPaidUser && currentPlan) {
      // Calculate price difference (prorated amount user will pay now)
      const priceDiff = targetPlan.monthly_price - currentPlan.monthly_price;
      setUpgradeConfirm({
        open: true,
        targetPlan,
        priceDiff: priceDiff > 0 ? priceDiff : 0,
      });
    } else {
      // Free user - go directly to checkout
      handleUpgrade(tierId);
    }
  };

  const handleUpgrade = async (tierId?: string) => {
    setPortalLoading(true);
    setUpgradeConfirm({ open: false, targetPlan: null, priceDiff: 0 });

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
        // Handle payment errors (402) - card declined, insufficient funds, etc.
        if (response.status === 402) {
          toast({
            title: "Payment Failed",
            description: data.detail || "Your payment could not be processed. Please update your payment method below and try again.",
            variant: "destructive",
          });
        } else {
          toast({
            title: "Error",
            description: data.detail || data.error || "Failed to process upgrade",
            variant: "destructive",
          });
        }
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
          description: data.message || `You are now on the ${targetPlan.name} plan. You'll be charged the prorated difference.`,
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

                      <div className="flex items-center gap-2 mb-1">
                        <div className={`p-2 rounded-full ${isCurrentPlan ? "bg-primary/20" : "bg-muted"}`}>
                          {getTierIcon(plan.id)}
                        </div>
                        <h3 className="font-semibold text-lg">{plan.name}</h3>
                      </div>

                      {/* Tagline from pricing config */}
                      {(() => {
                        const tierInfo = getTierInfo(plan.id);
                        return tierInfo?.tagline && (
                          <p className="text-xs text-muted-foreground mb-3">{tierInfo.tagline}</p>
                        );
                      })()}

                      <div className="mb-3">
                        <span className="text-2xl font-bold">{plan.price_display}</span>
                        <span className="text-muted-foreground text-sm">/month</span>
                      </div>

                      {/* Key limits badges */}
                      {(() => {
                        const tierInfo = getTierInfo(plan.id);
                        return (
                          <div className="flex flex-wrap gap-1 mb-3">
                            <Badge variant="secondary" className="text-xs">
                              {plan.broker_limit} broker{plan.broker_limit > 1 ? "s" : ""}
                            </Badge>
                            {tierInfo?.signalsPerDay && (
                              <Badge variant="outline" className="text-xs">
                                {tierInfo.signalsPerDay === -1 ? "∞" : tierInfo.signalsPerDay} signals/day
                              </Badge>
                            )}
                            {tierInfo?.webhooks && (
                              <Badge variant="outline" className="text-xs">
                                {tierInfo.webhooks === -1 ? "∞" : tierInfo.webhooks} webhooks
                              </Badge>
                            )}
                          </div>
                        );
                      })()}

                      <ul className="space-y-1.5 mb-4 flex-1 text-xs">
                        {plan.features.map((feature, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <Check className="h-3 w-3 text-primary flex-shrink-0 mt-0.5" />
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
                          onClick={() => showUpgradeConfirm(plan.id)}
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
                          onClick={() => showUpgradeConfirm(plan.id)}
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

      {/* Plan Features Comparison - Comprehensive table matching landing page */}
      {plans.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Compare All Features</CardTitle>
            <CardDescription>See what&apos;s included in each plan</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left py-3 px-3 font-semibold">Feature</th>
                    <th className="text-center py-3 px-2 font-semibold">Free</th>
                    {plans
                      .filter((p) => p.id.startsWith("tier_"))
                      .sort((a, b) => a.monthly_price - b.monthly_price)
                      .map((plan) => {
                        const normalizedCurrent = normalizeTierId(currentTier);
                        const isCurrentPlan = plan.id === normalizedCurrent;
                        return (
                          <th key={plan.id} className={`text-center py-3 px-2 font-semibold ${isCurrentPlan ? "bg-primary/10" : ""}`}>
                            <div>{plan.name}</div>
                            <div className="text-xs font-normal text-muted-foreground mt-1">{plan.price_display}/mo</div>
                          </th>
                        );
                      })}
                  </tr>
                </thead>
                <tbody>
                  {/* Broker Connections */}
                  <tr className="border-b">
                    <td className="py-2 px-3 font-medium">Broker Connections</td>
                    <td className="text-center py-2 px-2"><span className="font-semibold text-primary">1</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          <span className="font-semibold text-primary">{plan.broker_limit}</span>
                        </td>
                      );
                    })}
                  </tr>

                  {/* Signals per Day */}
                  <tr className="border-b bg-muted/30">
                    <td className="py-2 px-3 font-medium">Signals per Day</td>
                    <td className="text-center py-2 px-2"><span className="font-semibold">50</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan) => {
                      const tierInfo = getTierInfo(plan.id);
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          <span className="font-semibold">{tierInfo?.signalsPerDay === -1 ? "Unlimited" : tierInfo?.signalsPerDay}</span>
                        </td>
                      );
                    })}
                  </tr>

                  {/* Webhooks */}
                  <tr className="border-b">
                    <td className="py-2 px-3 font-medium">Webhooks</td>
                    <td className="text-center py-2 px-2"><span className="font-semibold">1</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan) => {
                      const tierInfo = getTierInfo(plan.id);
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          <span className="font-semibold">{tierInfo?.webhooks === -1 ? "Unlimited" : tierInfo?.webhooks}</span>
                        </td>
                      );
                    })}
                  </tr>

                  {/* AI Signal Guards */}
                  <tr className="border-b bg-muted/30">
                    <td className="py-2 px-3 font-medium">AI Signal Guards</td>
                    <td className="text-center py-2 px-2"><span className="text-muted-foreground">-</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          {idx === 0 ? (
                            <span className="text-xs">Staleness only</span>
                          ) : idx === 1 ? (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">All 5 guards</span>
                            </>
                          ) : (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">+ Custom</span>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Risk Management */}
                  <tr className="border-b">
                    <td className="py-2 px-3 font-medium">Risk Management</td>
                    <td className="text-center py-2 px-2"><span className="text-muted-foreground">-</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          {idx === 0 ? (
                            <span className="text-xs">Daily limits</span>
                          ) : idx === 1 ? (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">Full suite</span>
                            </>
                          ) : idx === 2 ? (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">+ Per-symbol</span>
                            </>
                          ) : (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">+ Per-account</span>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Position Sizing */}
                  <tr className="border-b bg-muted/30">
                    <td className="py-2 px-3 font-medium">Position Sizing</td>
                    <td className="text-center py-2 px-2"><span className="text-xs">Fixed lots</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          {idx === 0 ? (
                            <span className="text-xs">Fixed lots</span>
                          ) : idx === 1 ? (
                            <span className="text-xs">% of balance</span>
                          ) : idx === 2 ? (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">Risk-based</span>
                            </>
                          ) : (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">All methods</span>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Symbol Mapping */}
                  <tr className="border-b">
                    <td className="py-2 px-3 font-medium">Symbol Mapping</td>
                    <td className="text-center py-2 px-2"><span className="text-muted-foreground">-</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          {idx === 0 ? (
                            <span className="text-muted-foreground">-</span>
                          ) : idx === 1 ? (
                            <Check className="h-4 w-4 text-primary mx-auto" />
                          ) : idx === 2 ? (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">+ Aliases</span>
                            </>
                          ) : (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">+ Bulk import</span>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Account Groups */}
                  <tr className="border-b bg-muted/30">
                    <td className="py-2 px-3 font-medium">Account Groups</td>
                    <td className="text-center py-2 px-2"><span className="text-muted-foreground">-</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          {idx === 0 ? (
                            <span className="text-muted-foreground">-</span>
                          ) : idx === 1 ? (
                            <span className="font-semibold">2</span>
                          ) : idx === 2 ? (
                            <span className="font-semibold">Unlimited</span>
                          ) : (
                            <span className="font-semibold">+ Nested</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* AI Strategy Suite */}
                  <tr className="border-b">
                    <td className="py-2 px-3 font-medium">AI Strategy Suite</td>
                    <td className="text-center py-2 px-2"><span className="text-muted-foreground">-</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          {idx < 2 ? (
                            <span className="text-muted-foreground">-</span>
                          ) : idx === 2 ? (
                            <Check className="h-4 w-4 text-primary mx-auto" />
                          ) : (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">+ AI Coach</span>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* API Access */}
                  <tr className="border-b bg-muted/30">
                    <td className="py-2 px-3 font-medium">API Access</td>
                    <td className="text-center py-2 px-2"><span className="text-muted-foreground">-</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          {idx < 2 ? (
                            <span className="text-muted-foreground">-</span>
                          ) : idx === 2 ? (
                            <Check className="h-4 w-4 text-primary mx-auto" />
                          ) : (
                            <>
                              <Check className="h-4 w-4 text-primary mx-auto" />
                              <span className="text-xs block">Higher limits</span>
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Webhook Log Retention */}
                  <tr className="border-b">
                    <td className="py-2 px-3 font-medium">Webhook Log Retention</td>
                    <td className="text-center py-2 px-2"><span className="font-semibold">7 days</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      const days = [7, 14, 30, 90];
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          <span className="font-semibold">{days[idx]} days</span>
                        </td>
                      );
                    })}
                  </tr>

                  {/* Support */}
                  <tr className="bg-muted/30">
                    <td className="py-2 px-3 font-medium">Support</td>
                    <td className="text-center py-2 px-2"><span className="text-xs">Community</span></td>
                    {plans.filter((p) => p.id.startsWith("tier_")).sort((a, b) => a.monthly_price - b.monthly_price).map((plan, idx) => {
                      const isCurrentPlan = plan.id === normalizeTierId(currentTier);
                      const support = ["Email (48h)", "Email (24h)", "Priority (12h)", "+ Live chat"];
                      return (
                        <td key={plan.id} className={`text-center py-2 px-2 ${isCurrentPlan ? "bg-primary/5" : ""}`}>
                          <span className="text-xs">{support[idx]}</span>
                        </td>
                      );
                    })}
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Subscription Management Card - Always visible for paid users */}
      {isPaid && billing?.can_manage && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Subscription Management
            </CardTitle>
            <CardDescription>
              Update payment method, view invoices, or cancel your subscription
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4">
              <Button
                variant="outline"
                onClick={handleManageSubscription}
                disabled={portalLoading}
                className="flex-1"
              >
                <CreditCard className="mr-2 h-4 w-4" />
                {portalLoading ? "Loading..." : "Update Payment Method"}
              </Button>
              <Button
                variant="outline"
                onClick={handleManageSubscription}
                disabled={portalLoading}
                className="flex-1"
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                {portalLoading ? "Loading..." : "View Invoices & History"}
              </Button>
              <Button
                variant="ghost"
                onClick={handleManageSubscription}
                disabled={portalLoading}
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                Cancel Subscription
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              You&apos;ll be redirected to our secure billing portal powered by Stripe.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Upgrade Confirmation Dialog */}
      <AlertDialog open={upgradeConfirm.open} onOpenChange={(open) => setUpgradeConfirm(prev => ({ ...prev, open }))}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <ArrowUpRight className="h-5 w-5 text-primary" />
              Confirm Upgrade to {upgradeConfirm.targetPlan?.name}
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4">
                <p>
                  You&apos;re upgrading from <strong>{billing?.tier_name}</strong> to{" "}
                  <strong>{upgradeConfirm.targetPlan?.name}</strong>.
                </p>

                {upgradeConfirm.priceDiff > 0 && (
                  <div className="bg-muted p-4 rounded-lg">
                    <div className="flex justify-between items-center">
                      <span>New plan price:</span>
                      <span className="font-semibold">{upgradeConfirm.targetPlan?.price_display}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm text-muted-foreground">
                      <span>Current plan:</span>
                      <span>{plans.find(p => p.id === billing?.tier)?.price_display || "Free"}</span>
                    </div>
                    <hr className="my-2" />
                    <div className="flex justify-between items-center font-semibold text-primary">
                      <span>Prorated charge today:</span>
                      <span>~{formatPrice(upgradeConfirm.priceDiff)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      You&apos;ll be charged the prorated difference for the remainder of your billing cycle immediately.
                    </p>
                  </div>
                )}

                <div className="space-y-2">
                  <p className="font-medium">New features you&apos;ll get:</p>
                  <ul className="text-sm space-y-1">
                    {upgradeConfirm.targetPlan?.features.slice(0, 5).map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <Check className="h-3 w-3 text-primary" />
                        {feature}
                      </li>
                    ))}
                    {(upgradeConfirm.targetPlan?.features.length || 0) > 5 && (
                      <li className="text-muted-foreground">
                        + {(upgradeConfirm.targetPlan?.features.length || 0) - 5} more features
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={portalLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleUpgrade(upgradeConfirm.targetPlan?.id)}
              disabled={portalLoading}
              className="bg-primary"
            >
              {portalLoading ? "Processing..." : `Upgrade & Pay ${upgradeConfirm.priceDiff > 0 ? formatPrice(upgradeConfirm.priceDiff) : "Now"}`}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
