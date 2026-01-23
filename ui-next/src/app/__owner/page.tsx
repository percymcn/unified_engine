"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Check,
  X,
  Shield,
  Users,
  Settings,
  Key,
  Crown,
} from "lucide-react";

interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  subscription_tier: string;
  subscription_status: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login: string | null;
}

interface PlanConfig {
  tier_id: string;
  name: string;
  monthly_price: number;
  price_display: string;
  brokers: number;
  stripe_price_id: string | null;
  features: string[];
}

interface BrokerStatus {
  status: "CONFIGURED" | "DISABLED" | "PARTIAL";
  missing_vars: string[];
  present_vars: string[];
  values: Record<string, string>;
}

interface EnvDoctor {
  database: {
    type: string;
    path?: string;
    exists?: boolean;
    size_bytes?: number;
  };
  brokers: Record<string, BrokerStatus>;
  oauth: {
    google: boolean;
    github: boolean;
    microsoft: boolean;
  };
  backend_port: number;
  backend_host: string;
}

export default function AdminPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [plans, setPlans] = useState<PlanConfig[]>([]);
  const [overview, setOverview] = useState<{
    users: { total: number; active: number; verified: number };
    plans_configured: number;
    stripe_configured: boolean;
  } | null>(null);
  const [envDoctor, setEnvDoctor] = useState<EnvDoctor | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "users" | "plans" | "brokers" | "env">("overview");

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const fetchData = async () => {
    try {
      if (activeTab === "overview") {
        const response = await fetch("/api/admin/overview");
        if (response.status === 403) {
          toast({
            title: "Access Denied",
            description: "This area is restricted to owners only.",
            variant: "destructive",
          });
          router.push("/dashboard");
          return;
        }
        if (!response.ok) throw new Error("Failed to fetch overview");
        const data = await response.json();
        setOverview(data);
      } else if (activeTab === "users") {
        const response = await fetch("/api/admin/users");
        if (response.status === 403) {
          toast({
            title: "Access Denied",
            description: "This area is restricted to owners only.",
            variant: "destructive",
          });
          router.push("/dashboard");
          return;
        }
        if (!response.ok) throw new Error("Failed to fetch users");
        const data = await response.json();
        setUsers(data.users || []);
      } else if (activeTab === "plans") {
        const response = await fetch("/api/admin/plans");
        if (response.status === 403) {
          toast({
            title: "Access Denied",
            description: "This area is restricted to owners only.",
            variant: "destructive",
          });
          router.push("/dashboard");
          return;
        }
        if (!response.ok) throw new Error("Failed to fetch plans");
        const data = await response.json();
        setPlans(data.plans || []);
      } else if (activeTab === "brokers" || activeTab === "env") {
        const response = await fetch("/api/admin/system/env-doctor");
        if (response.status === 403) {
          toast({
            title: "Access Denied",
            description: "This area is restricted to owners only.",
            variant: "destructive",
          });
          router.push("/dashboard");
          return;
        }
        if (!response.ok) throw new Error("Failed to fetch env doctor");
        const data = await response.json();
        setEnvDoctor(data);
      }
    } catch (error) {
      console.error("Failed to fetch admin data:", error);
      toast({
        title: "Error",
        description: "Failed to load admin data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (userId: number) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}/toggle-active`, {
        method: "PATCH",
      });
      if (!response.ok) throw new Error("Failed to toggle user");
      const data = await response.json();
      toast({
        title: "Success",
        description: data.message,
      });
      fetchData();
    } catch {
      toast({
        title: "Error",
        description: "Failed to update user",
        variant: "destructive",
      });
    }
  };

  const handleSetTier = async (userId: number, tier: string) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}/set-tier`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier }),
      });
      if (!response.ok) throw new Error("Failed to set tier");
      const data = await response.json();
      toast({
        title: "Success",
        description: data.message,
      });
      fetchData();
    } catch {
      toast({
        title: "Error",
        description: "Failed to update tier",
        variant: "destructive",
      });
    }
  };

  const handleResetPassword = async (userId: number) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}/reset-password-link`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to generate reset link");
      const data = await response.json();
      toast({
        title: "Reset Link Generated",
        description: `Reset URL: ${data.reset_url}`,
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to generate reset link",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64 mt-2" />
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Owner Admin Dashboard
          </h1>
          <p className="text-muted-foreground">
            Manage users, subscriptions, and pricing configuration
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 font-medium ${
            activeTab === "overview"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground"
          }`}
        >
          <Shield className="h-4 w-4 inline mr-2" />
          Overview
        </button>
        <button
          onClick={() => setActiveTab("users")}
          className={`px-4 py-2 font-medium ${
            activeTab === "users"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground"
          }`}
        >
          <Users className="h-4 w-4 inline mr-2" />
          Users
        </button>
        <button
          onClick={() => setActiveTab("plans")}
          className={`px-4 py-2 font-medium ${
            activeTab === "plans"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground"
          }`}
        >
          <Settings className="h-4 w-4 inline mr-2" />
          Plans & Pricing
        </button>
        <button
          onClick={() => setActiveTab("brokers")}
          className={`px-4 py-2 font-medium ${
            activeTab === "brokers"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground"
          }`}
        >
          <Shield className="h-4 w-4 inline mr-2" />
          Broker Status
        </button>
        <button
          onClick={() => setActiveTab("env")}
          className={`px-4 py-2 font-medium ${
            activeTab === "env"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground"
          }`}
        >
          <Key className="h-4 w-4 inline mr-2" />
          ENV Doctor
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Total Users
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{overview?.users.total || 0}</div>
              <p className="text-sm text-muted-foreground mt-1">
                {overview?.users.active || 0} active, {overview?.users.verified || 0} verified
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Pricing Plans
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{overview?.plans_configured || 0}</div>
              <p className="text-sm text-muted-foreground mt-1">Tiers configured</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Stripe Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {overview?.stripe_configured ? (
                  <Check className="h-8 w-8 text-green-500" />
                ) : (
                  <X className="h-8 w-8 text-red-500" />
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {overview?.stripe_configured ? "Configured" : "Not configured"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Users Tab */}
      {activeTab === "users" && (
        <Card>
          <CardHeader>
            <CardTitle>Users</CardTitle>
            <CardDescription>Manage user accounts and subscriptions</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Username</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{user.subscription_tier}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {user.is_active ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <X className="h-4 w-4 text-red-500" />
                        )}
                        <span>{user.is_active ? "Active" : "Inactive"}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleToggleActive(user.id)}
                        >
                          {user.is_active ? "Deactivate" : "Activate"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleResetPassword(user.id)}
                        >
                          <Key className="h-4 w-4" />
                        </Button>
                        <select
                          className="px-2 py-1 text-sm border rounded"
                          value={user.subscription_tier}
                          onChange={(e) => handleSetTier(user.id, e.target.value)}
                        >
                          <option value="free">Free</option>
                          <option value="tier_1">Tier 1</option>
                          <option value="tier_2">Tier 2</option>
                          <option value="tier_3">Tier 3</option>
                          <option value="tier_4">Tier 4</option>
                        </select>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Plans Tab */}
      {activeTab === "plans" && (
        <Card>
          <CardHeader>
            <CardTitle>Plans & Pricing Configuration</CardTitle>
            <CardDescription>
              View current pricing tiers and Stripe configuration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              {plans.map((plan) => (
                <Card key={plan.tier_id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        {plan.tier_id === "free" ? (
                          <Crown className="h-5 w-5" />
                        ) : (
                          <Shield className="h-5 w-5" />
                        )}
                        {plan.name}
                      </CardTitle>
                      <Badge variant="secondary">{plan.price_display}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">Brokers:</span>
                        <span>{plan.brokers}</span>
                      </div>
                      {plan.stripe_price_id && (
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">Stripe Price ID:</span>
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {plan.stripe_price_id}
                          </code>
                        </div>
                      )}
                      <div>
                        <span className="text-sm font-medium">Features:</span>
                        <ul className="list-disc list-inside mt-1 text-sm text-muted-foreground">
                          {plan.features.map((feature, idx) => (
                            <li key={idx}>{feature}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Broker Status Tab */}
      {activeTab === "brokers" && envDoctor && (
        <Card>
          <CardHeader>
            <CardTitle>Broker Configuration Status</CardTitle>
            <CardDescription>
              View broker configuration and missing environment variables
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(envDoctor.brokers).map(([broker, status]) => (
                <Card key={broker}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{broker.replace(/_/g, " ").toUpperCase()}</CardTitle>
                      <Badge
                        variant={
                          status.status === "CONFIGURED"
                            ? "default"
                            : status.status === "PARTIAL"
                              ? "secondary"
                              : "destructive"
                        }
                      >
                        {status.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {status.status === "CONFIGURED" && (
                      <div className="text-sm text-green-600">
                        <Check className="h-4 w-4 inline mr-1" />
                        All required variables configured
                      </div>
                    )}
                    {status.present_vars.length > 0 && (
                      <div className="mt-2">
                        <span className="text-sm font-medium">Configured:</span>
                        <ul className="list-disc list-inside ml-2 text-sm">
                          {status.present_vars.map((v) => (
                            <li key={v}>
                              {v}: {status.values[v] || "(set)"}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {status.missing_vars.length > 0 && (
                      <div className="mt-2">
                        <span className="text-sm font-medium text-red-600">Missing:</span>
                        <ul className="list-disc list-inside ml-2 text-sm text-red-600">
                          {status.missing_vars.map((v) => (
                            <li key={v}>{v}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ENV Doctor Tab */}
      {activeTab === "env" && envDoctor && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>System Environment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <span className="font-medium">Backend:</span> {envDoctor.backend_host}:{envDoctor.backend_port}
                </div>
                <div>
                  <span className="font-medium">Database:</span> {envDoctor.database.type}
                  {envDoctor.database.path && ` - ${envDoctor.database.path}`}
                  {envDoctor.database.exists === false && (
                    <Badge variant="destructive" className="ml-2">File not found</Badge>
                  )}
                </div>
                <div>
                  <span className="font-medium">OAuth:</span>
                  <div className="ml-4 mt-1">
                    Google: {envDoctor.oauth.google ? (
                      <Badge variant="default">Configured</Badge>
                    ) : (
                      <Badge variant="secondary">Not configured</Badge>
                    )}
                    {" "}
                    GitHub: {envDoctor.oauth.github ? (
                      <Badge variant="default">Configured</Badge>
                    ) : (
                      <Badge variant="secondary">Not configured</Badge>
                    )}
                    {" "}
                    Microsoft: {envDoctor.oauth.microsoft ? (
                      <Badge variant="default">Configured</Badge>
                    ) : (
                      <Badge variant="secondary">Not configured</Badge>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Broker Status Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(envDoctor.brokers).map(([broker, status]) => (
                  <div key={broker} className="flex items-center justify-between p-2 border rounded">
                    <span className="text-sm">{broker.replace(/_/g, " ")}</span>
                    <Badge
                      variant={
                        status.status === "CONFIGURED"
                          ? "default"
                          : status.status === "PARTIAL"
                            ? "secondary"
                            : "destructive"
                      }
                    >
                      {status.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
