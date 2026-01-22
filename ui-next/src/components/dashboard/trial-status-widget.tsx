"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Crown, Zap, ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";

interface SubscriptionStatus {
  tier: string;
  status: string;
  ends_at: string | null;
  can_manage: boolean;
}

export function TrialStatusWidget() {
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const response = await fetch("/api/billing/status");
        if (response.ok) {
          const data = await response.json();
          setSubscription(data);
        }
      } catch (error) {
        console.error("Error fetching subscription status:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Subscription Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-6">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const isPro = subscription?.tier === "pro";
  const isCanceling = subscription?.status === "canceling";

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Subscription Status</CardTitle>
          {isPro && (
            <Badge
              variant="outline"
              className="border-primary text-primary flex items-center gap-1"
            >
              <Crown className="h-3 w-3" />
              Pro
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isPro ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Crown className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">Pro Plan</p>
                <p className="text-xs text-muted-foreground">
                  {isCanceling ? (
                    <>
                      Canceling - Active until{" "}
                      {subscription?.ends_at
                        ? new Date(subscription.ends_at).toLocaleDateString()
                        : "end of period"}
                    </>
                  ) : (
                    "Unlimited broker connections"
                  )}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Zap className="h-4 w-4 text-green-500" />
                <span>Priority signal execution</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Zap className="h-4 w-4 text-green-500" />
                <span>Advanced routing rules</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Zap className="h-4 w-4 text-green-500" />
                <span>Email support</span>
              </div>
            </div>

            {subscription?.can_manage && (
              <Link href="/dashboard/settings/billing">
                <Button variant="outline" size="sm" className="w-full">
                  Manage Subscription
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                <Zap className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-medium">Free Plan</p>
                <p className="text-xs text-muted-foreground">
                  Limited to 1 broker connection
                </p>
              </div>
            </div>

            <div className="rounded-lg bg-primary/5 p-3 border border-primary/10">
              <p className="text-sm font-medium">Upgrade to Pro</p>
              <p className="text-xs text-muted-foreground mt-1">
                Get unlimited broker connections, priority execution, and more.
              </p>
            </div>

            <Link href="/pricing">
              <Button className="w-full">
                <Crown className="h-4 w-4 mr-2" />
                Upgrade to Pro
              </Button>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
