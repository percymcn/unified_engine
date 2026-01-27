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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Check,
  X,
  Shield,
  Users,
  Settings,
  Key,
  Crown,
  Activity,
  Database,
  Server,
  Zap,
  RefreshCw,
  Lock,
  Eye,
  EyeOff,
  Copy,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  CreditCard,
  BarChart3,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

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
    url?: string;
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

const tabs = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "pipeline", label: "Pipeline", icon: Activity },
  { id: "users", label: "Users", icon: Users },
  { id: "plans", label: "Plans", icon: CreditCard },
  { id: "brokers", label: "Brokers", icon: Zap },
  { id: "env", label: "System", icon: Server },
] as const;

export default function OwnerPortal() {
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
  const [pipelineStatus, setPipelineStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<typeof tabs[number]["id"]>("overview");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);

  // Check authentication on mount
  useEffect(() => {
    checkAuth();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [activeTab, isAuthenticated]);

  const checkAuth = async () => {
    try {
      const response = await fetch("/api/admin/overview", { credentials: "include" });
      if (response.status === 403) {
        toast({
          title: "Access Denied",
          description: "You don't have permission to access the owner portal.",
          variant: "destructive",
        });
        router.push("/dashboard");
        return;
      }
      if (response.status === 401) {
        toast({
          title: "Authentication Required",
          description: "Please log in to access the owner portal.",
          variant: "destructive",
        });
        router.push("/login");
        return;
      }
      if (response.ok) {
        setIsAuthenticated(true);
        const data = await response.json();
        setOverview(data);
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      router.push("/dashboard");
    } finally {
      setAuthChecking(false);
      setLoading(false);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      if (activeTab === "overview") {
        const response = await fetch("/api/admin/overview", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setOverview(data);
        }
      } else if (activeTab === "pipeline") {
        const response = await fetch("/api/admin/system/pipeline-status", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setPipelineStatus(data);
        }
      } else if (activeTab === "users") {
        const response = await fetch("/api/admin/users", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setUsers(data.users || []);
        }
      } else if (activeTab === "plans") {
        const response = await fetch("/api/admin/plans", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setPlans(data.plans || []);
        }
      } else if (activeTab === "brokers" || activeTab === "env") {
        const response = await fetch("/api/admin/system/env-doctor", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setEnvDoctor(data);
        }
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh pipeline tab every 5 seconds
  useEffect(() => {
    if (activeTab === "pipeline" && isAuthenticated) {
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [activeTab, isAuthenticated]);

  const handleToggleActive = async (userId: number) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}/toggle-active`, {
        method: "PATCH",
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        toast({ title: "Success", description: data.message });
        fetchData();
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to toggle user", variant: "destructive" });
    }
  };

  const handleSetTier = async (userId: number, tier: string) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}/set-tier`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ tier }),
      });
      if (response.ok) {
        const data = await response.json();
        toast({ title: "Success", description: data.message });
        fetchData();
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to set tier", variant: "destructive" });
    }
  };

  if (authChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-primary/5">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="relative">
            <div className="absolute inset-0 blur-3xl bg-primary/20 rounded-full" />
            <Shield className="h-16 w-16 text-primary relative animate-pulse" />
          </div>
          <p className="mt-4 text-muted-foreground">Verifying access...</p>
        </motion.div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="border-b border-border/50 backdrop-blur-xl bg-background/80 sticky top-0 z-50"
      >
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute inset-0 blur-xl bg-primary/30 rounded-full" />
                <Crown className="h-8 w-8 text-primary relative" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                  Owner Portal
                </h1>
                <p className="text-xs text-muted-foreground">System Administration</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchData()}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>
      </motion.div>

      <div className="container mx-auto px-6 py-8">
        {/* Tab Navigation */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex gap-2 mb-8 overflow-x-auto pb-2"
        >
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? "default" : "ghost"}
                onClick={() => setActiveTab(tab.id)}
                className={`gap-2 transition-all ${
                  activeTab === tab.id
                    ? "bg-primary shadow-lg shadow-primary/25"
                    : "hover:bg-primary/10"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </Button>
            );
          })}
        </motion.div>

        {/* Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === "overview" && (
              <OverviewTab overview={overview} loading={loading} />
            )}
            {activeTab === "pipeline" && (
              <PipelineTab pipelineStatus={pipelineStatus} loading={loading} />
            )}
            {activeTab === "users" && (
              <UsersTab
                users={users}
                loading={loading}
                onToggleActive={handleToggleActive}
                onSetTier={handleSetTier}
              />
            )}
            {activeTab === "plans" && (
              <PlansTab plans={plans} loading={loading} />
            )}
            {activeTab === "brokers" && (
              <BrokersTab envDoctor={envDoctor} loading={loading} />
            )}
            {activeTab === "env" && (
              <SystemTab envDoctor={envDoctor} loading={loading} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// Pipeline Tab - Live System Blueprint
function PipelineTab({ pipelineStatus, loading }: { pipelineStatus: any; loading: boolean }) {
  if (loading && !pipelineStatus) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32" />
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "bg-emerald-500";
      case "warning":
        return "bg-amber-500";
      case "error":
      case "degraded":
        return "bg-red-500";
      case "idle":
        return "bg-blue-500";
      default:
        return "bg-gray-500";
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case "healthy":
        return "bg-emerald-500/10 border-emerald-500/50";
      case "warning":
        return "bg-amber-500/10 border-amber-500/50";
      case "error":
      case "degraded":
        return "bg-red-500/10 border-red-500/50";
      case "idle":
        return "bg-blue-500/10 border-blue-500/50";
      default:
        return "bg-gray-500/10 border-gray-500/50";
    }
  };

  const componentIcons: Record<string, any> = {
    database: Database,
    redis: Zap,
    webhook_ingestion: Activity,
    signal_processor: Zap,
    broker_connections: Server,
    trade_execution: CheckCircle2,
  };

  return (
    <div className="space-y-6">
      {/* Overall Health Banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 rounded-xl border ${getStatusBg(pipelineStatus?.overall_health || "unknown")}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${getStatusColor(pipelineStatus?.overall_health || "unknown")} animate-pulse`} />
            <div>
              <h3 className="font-semibold text-lg">System Status: {pipelineStatus?.overall_health?.toUpperCase() || "CHECKING..."}</h3>
              <p className="text-sm text-muted-foreground">
                Last updated: {pipelineStatus?.timestamp ? new Date(pipelineStatus.timestamp).toLocaleTimeString() : "..."}
              </p>
            </div>
          </div>
          <Badge variant="outline" className="animate-pulse">
            <Activity className="h-3 w-3 mr-1" />
            LIVE
          </Badge>
        </div>
      </motion.div>

      {/* Pipeline Flow Visualization */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Data Flow Pipeline
          </CardTitle>
          <CardDescription>Real-time data flow through the system</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative overflow-x-auto">
            <div className="flex items-center justify-between min-w-[800px] py-8">
              {/* Webhook Ingestion */}
              <div className="flex flex-col items-center">
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  className={`w-20 h-20 rounded-2xl border-2 flex items-center justify-center ${getStatusBg(pipelineStatus?.components?.webhook_ingestion?.status || "unknown")}`}
                >
                  <Activity className="h-8 w-8" />
                </motion.div>
                <span className="text-xs mt-2 font-medium">Webhooks</span>
                <span className="text-xs text-muted-foreground">
                  {pipelineStatus?.components?.webhook_ingestion?.active_webhooks || 0} active
                </span>
              </div>

              {/* Arrow */}
              <div className="flex-1 flex items-center justify-center relative mx-2">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  className="h-0.5 bg-gradient-to-r from-primary/50 to-primary w-full"
                />
                <motion.div
                  animate={{ x: [0, 20, 0] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="absolute w-2 h-2 bg-primary rounded-full"
                />
              </div>

              {/* Signal Processor */}
              <div className="flex flex-col items-center">
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.1 }}
                  className={`w-20 h-20 rounded-2xl border-2 flex items-center justify-center ${getStatusBg(pipelineStatus?.components?.signal_processor?.status || "unknown")}`}
                >
                  <Zap className="h-8 w-8" />
                </motion.div>
                <span className="text-xs mt-2 font-medium">Processor</span>
                <span className="text-xs text-muted-foreground">
                  {pipelineStatus?.components?.signal_processor?.pending || 0} pending
                </span>
              </div>

              {/* Arrow */}
              <div className="flex-1 flex items-center justify-center relative mx-2">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: 0.1 }}
                  className="h-0.5 bg-gradient-to-r from-primary/50 to-primary w-full"
                />
                <motion.div
                  animate={{ x: [0, 20, 0] }}
                  transition={{ repeat: Infinity, duration: 1.5, delay: 0.5 }}
                  className="absolute w-2 h-2 bg-primary rounded-full"
                />
              </div>

              {/* Broker Connections */}
              <div className="flex flex-col items-center">
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2 }}
                  className={`w-20 h-20 rounded-2xl border-2 flex items-center justify-center ${getStatusBg(pipelineStatus?.components?.broker_connections?.status || "unknown")}`}
                >
                  <Server className="h-8 w-8" />
                </motion.div>
                <span className="text-xs mt-2 font-medium">Brokers</span>
                <span className="text-xs text-muted-foreground">
                  {pipelineStatus?.components?.broker_connections?.active_accounts || 0} accounts
                </span>
              </div>

              {/* Arrow */}
              <div className="flex-1 flex items-center justify-center relative mx-2">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: 0.2 }}
                  className="h-0.5 bg-gradient-to-r from-primary/50 to-primary w-full"
                />
                <motion.div
                  animate={{ x: [0, 20, 0] }}
                  transition={{ repeat: Infinity, duration: 1.5, delay: 1 }}
                  className="absolute w-2 h-2 bg-primary rounded-full"
                />
              </div>

              {/* Trade Execution */}
              <div className="flex flex-col items-center">
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.3 }}
                  className={`w-20 h-20 rounded-2xl border-2 flex items-center justify-center ${getStatusBg(pipelineStatus?.components?.trade_execution?.status || "unknown")}`}
                >
                  <CheckCircle2 className="h-8 w-8" />
                </motion.div>
                <span className="text-xs mt-2 font-medium">Execution</span>
                <span className="text-xs text-muted-foreground">
                  {pipelineStatus?.components?.trade_execution?.success_rate || "N/A"}
                </span>
              </div>

              {/* Arrow */}
              <div className="flex-1 flex items-center justify-center relative mx-2">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: 0.3 }}
                  className="h-0.5 bg-gradient-to-r from-primary/50 to-primary w-full"
                />
                <motion.div
                  animate={{ x: [0, 20, 0] }}
                  transition={{ repeat: Infinity, duration: 1.5, delay: 1.5 }}
                  className="absolute w-2 h-2 bg-primary rounded-full"
                />
              </div>

              {/* Database */}
              <div className="flex flex-col items-center">
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.4 }}
                  className={`w-20 h-20 rounded-2xl border-2 flex items-center justify-center ${getStatusBg(pipelineStatus?.components?.database?.status || "unknown")}`}
                >
                  <Database className="h-8 w-8" />
                </motion.div>
                <span className="text-xs mt-2 font-medium">Database</span>
                <span className="text-xs text-muted-foreground">PostgreSQL</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Component Details Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {pipelineStatus?.components && Object.entries(pipelineStatus.components).map(([key, component]: [string, any], i) => {
          const Icon = componentIcons[key] || Server;
          return (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className={`border ${getStatusBg(component.status)}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <CardTitle className="text-sm capitalize">{key.replace(/_/g, " ")}</CardTitle>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(component.status)} animate-pulse`} />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">{component.message}</p>
                  {component.latency_ms && component.latency_ms > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">Latency: {component.latency_ms}ms</p>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Recent Activity Feed */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Live Activity Feed
          </CardTitle>
          <CardDescription>Recent signals and trades flowing through the system</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {pipelineStatus?.recent_activity?.length > 0 ? (
              pipelineStatus.recent_activity.map((activity: any, i: number) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-3 p-2 rounded-lg bg-muted/50 hover:bg-muted/80 transition-colors"
                >
                  <div className={`w-2 h-2 rounded-full ${activity.type === "signal" ? "bg-blue-500" : "bg-emerald-500"}`} />
                  <Badge variant="outline" className="text-xs">
                    {activity.type}
                  </Badge>
                  <span className="text-sm font-medium">{activity.symbol}</span>
                  <Badge variant={activity.action === "buy" ? "default" : "secondary"} className="text-xs">
                    {activity.action}
                  </Badge>
                  <span className="text-xs text-muted-foreground flex-1 text-right">
                    {activity.time ? new Date(activity.time).toLocaleTimeString() : ""}
                  </span>
                  <Badge
                    variant="outline"
                    className={`text-xs ${
                      activity.status === "executed" || activity.status === "processed"
                        ? "text-emerald-500 border-emerald-500/50"
                        : activity.status === "failed"
                        ? "text-red-500 border-red-500/50"
                        : "text-amber-500 border-amber-500/50"
                    }`}
                  >
                    {activity.status}
                  </Badge>
                </motion.div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No recent activity</p>
                <p className="text-xs">Signals and trades will appear here in real-time</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Overview Tab
function OverviewTab({ overview, loading }: { overview: any; loading: boolean }) {
  if (loading) {
    return (
      <div className="grid gap-6 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    );
  }

  const stats = [
    {
      label: "Total Users",
      value: overview?.users?.total || 0,
      subtext: `${overview?.users?.active || 0} active, ${overview?.users?.verified || 0} verified`,
      icon: Users,
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
    },
    {
      label: "Pricing Plans",
      value: overview?.plans_configured || 0,
      subtext: "Tiers configured",
      icon: CreditCard,
      color: "text-green-500",
      bgColor: "bg-green-500/10",
    },
    {
      label: "Stripe Status",
      value: overview?.stripe_configured ? "Active" : "Not configured",
      subtext: overview?.stripe_configured ? "Payment processing enabled" : "Configure to enable payments",
      icon: Zap,
      color: overview?.stripe_configured ? "text-emerald-500" : "text-amber-500",
      bgColor: overview?.stripe_configured ? "bg-emerald-500/10" : "bg-amber-500/10",
    },
  ];

  return (
    <div className="grid gap-6 md:grid-cols-3">
      {stats.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="relative overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-all">
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-primary/10 to-transparent rounded-bl-full" />
              <CardHeader className="pb-2">
                <div className={`w-12 h-12 rounded-xl ${stat.bgColor} flex items-center justify-center mb-2`}>
                  <Icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground mt-1">{stat.subtext}</p>
              </CardContent>
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}

// Users Tab
function UsersTab({
  users,
  loading,
  onToggleActive,
  onSetTier,
}: {
  users: User[];
  loading: boolean;
  onToggleActive: (id: number) => void;
  onSetTier: (id: number, tier: string) => void;
}) {
  if (loading) {
    return <Skeleton className="h-96" />;
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          User Management
        </CardTitle>
        <CardDescription>
          {users.length} users registered
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id} className="hover:bg-primary/5">
                  <TableCell>
                    <div>
                      <p className="font-medium">{user.email}</p>
                      <p className="text-xs text-muted-foreground">@{user.username}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Badge variant={user.is_active ? "default" : "secondary"}>
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                      {user.is_verified && (
                        <Badge variant="outline" className="text-emerald-500 border-emerald-500/50">
                          Verified
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Select
                      value={user.subscription_tier}
                      onValueChange={(value) => onSetTier(user.id, value)}
                    >
                      <SelectTrigger className="w-28 h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="free">Free</SelectItem>
                        <SelectItem value="starter">Starter</SelectItem>
                        <SelectItem value="pro">Pro</SelectItem>
                        <SelectItem value="enterprise">Enterprise</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(user.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onToggleActive(user.id)}
                    >
                      {user.is_active ? (
                        <X className="h-4 w-4 text-destructive" />
                      ) : (
                        <Check className="h-4 w-4 text-emerald-500" />
                      )}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

// Plans Tab
function PlansTab({ plans, loading }: { plans: PlanConfig[]; loading: boolean }) {
  if (loading) {
    return <Skeleton className="h-96" />;
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {plans.map((plan, i) => (
        <motion.div
          key={plan.tier_id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
        >
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-all">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{plan.name}</CardTitle>
                <Badge variant={plan.stripe_price_id ? "default" : "secondary"}>
                  {plan.stripe_price_id ? "Stripe Ready" : "No Stripe"}
                </Badge>
              </div>
              <CardDescription className="text-2xl font-bold text-primary">
                {plan.price_display}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Zap className="h-4 w-4 text-primary" />
                  <span>{plan.brokers} broker connections</span>
                </div>
                <div className="border-t border-border/50 pt-3">
                  <p className="text-xs text-muted-foreground mb-2">Features:</p>
                  <ul className="space-y-1">
                    {plan.features.slice(0, 4).map((feature, j) => (
                      <li key={j} className="text-xs flex items-center gap-2">
                        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}

// Brokers Tab
function BrokersTab({ envDoctor, loading }: { envDoctor: EnvDoctor | null; loading: boolean }) {
  if (loading || !envDoctor) {
    return <Skeleton className="h-96" />;
  }

  const brokerGroups = [
    { name: "MetaTrader 4", keys: ["mt4_sdk", "mt4_manager"] },
    { name: "MetaTrader 5", keys: ["mt5_sdk", "mt5_manager"] },
    { name: "TradeLocker", keys: ["tradelocker_sdk", "tradelocker_brand"] },
    { name: "Tradovate", keys: ["tradovate_oauth", "tradovate_password"] },
    { name: "ProjectX/TopStep", keys: ["projectx_sdk", "projectx_legacy"] },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "CONFIGURED":
        return "text-emerald-500 bg-emerald-500/10 border-emerald-500/50";
      case "PARTIAL":
        return "text-amber-500 bg-amber-500/10 border-amber-500/50";
      default:
        return "text-muted-foreground bg-muted/50 border-border";
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {brokerGroups.map((group, i) => (
        <motion.div
          key={group.name}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
        >
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{group.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {group.keys.map((key) => {
                const broker = envDoctor.brokers[key];
                if (!broker) return null;
                return (
                  <div
                    key={key}
                    className={`p-3 rounded-lg border ${getStatusColor(broker.status)}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <Badge variant="outline" className={getStatusColor(broker.status)}>
                        {broker.status}
                      </Badge>
                    </div>
                    {broker.missing_vars.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Missing: {broker.missing_vars.join(", ")}
                      </p>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}

// System Tab
function SystemTab({ envDoctor, loading }: { envDoctor: EnvDoctor | null; loading: boolean }) {
  if (loading || !envDoctor) {
    return <Skeleton className="h-96" />;
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Database */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            Database
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Type</span>
            <Badge>{envDoctor.database.type}</Badge>
          </div>
          {envDoctor.database.url && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Host</span>
              <span className="font-mono text-sm">{envDoctor.database.url}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/50">
              Connected
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* OAuth Providers */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5 text-primary" />
            OAuth Providers
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(envDoctor.oauth).map(([provider, configured]) => (
            <div key={provider} className="flex justify-between items-center">
              <span className="capitalize">{provider}</span>
              {configured ? (
                <Badge variant="outline" className="text-emerald-500 border-emerald-500/50">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Configured
                </Badge>
              ) : (
                <Badge variant="secondary">
                  <XCircle className="h-3 w-3 mr-1" />
                  Not Set
                </Badge>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Server Info */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm md:col-span-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5 text-primary" />
            Backend Server
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex justify-between p-3 rounded-lg bg-muted/50">
              <span className="text-muted-foreground">Host</span>
              <span className="font-mono">{envDoctor.backend_host}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-muted/50">
              <span className="text-muted-foreground">Port</span>
              <span className="font-mono">{envDoctor.backend_port}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
