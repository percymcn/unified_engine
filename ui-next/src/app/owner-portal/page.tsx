"use client";

import React, { useState, useEffect } from "react";
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
import { Textarea } from "@/components/ui/textarea";
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
  ScrollText,
  Signal,
  ArrowUpDown,
  Mail,
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
  { id: "smartflow", label: "SmartFlow", icon: Shield },
  { id: "pipeline", label: "Pipeline", icon: Activity },
  { id: "logs", label: "Logs", icon: ScrollText },
  { id: "users", label: "Users", icon: Users },
  { id: "plans", label: "Plans", icon: CreditCard },
  { id: "brokers", label: "Brokers", icon: Zap },
  { id: "broadcast", label: "Broadcast", icon: Mail },
  { id: "config", label: "Config", icon: Settings },
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
  const [connectedAccounts, setConnectedAccounts] = useState<any>(null);
  const [allEnvVars, setAllEnvVars] = useState<any>(null);
  const [systemLogs, setSystemLogs] = useState<any>(null);
  const [smartflowIntegrity, setSmartflowIntegrity] = useState<any>(null);
  const [smartflowTopology, setSmartflowTopology] = useState<any>(null);
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
      } else if (activeTab === "logs") {
        const response = await fetch("/api/admin/logs?limit=100", { credentials: "include" });
        console.log("[DEBUG] Logs response status:", response.status);
        if (response.ok) {
          const data = await response.json();
          console.log("[DEBUG] Logs data received:", data);
          console.log("[DEBUG] Logs count:", data?.logs?.length, "Total:", data?.total);
          setSystemLogs(data);
        } else {
          console.log("[DEBUG] Logs response not ok:", await response.text());
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
      } else if (activeTab === "brokers") {
        const response = await fetch("/api/admin/system/connected-accounts", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setConnectedAccounts(data);
        }
      } else if (activeTab === "config") {
        const response = await fetch("/api/admin/system/all-env-vars", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setAllEnvVars(data);
        }
      } else if (activeTab === "env") {
        const response = await fetch("/api/admin/system/env-doctor", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          setEnvDoctor(data);
        }
      } else if (activeTab === "smartflow") {
        // Fetch both integrity status and topology
        const [integrityRes, topologyRes] = await Promise.all([
          fetch("/api/v1/smartflow/integrity/status", { credentials: "include" }),
          fetch("/api/v1/smartflow/integrity/topology", { credentials: "include" }),
        ]);
        if (integrityRes.ok) {
          const data = await integrityRes.json();
          setSmartflowIntegrity(data);
        }
        if (topologyRes.ok) {
          const data = await topologyRes.json();
          setSmartflowTopology(data);
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
      const data = await response.json();
      if (response.ok) {
        toast({ title: "Success", description: data.message || `Tier set to ${tier}` });
        fetchData();
      } else {
        // Show the actual error from backend
        console.error("Set tier error:", response.status, data);
        toast({
          title: "Error",
          description: data.detail || data.error || data.message || `Failed to set tier (${response.status})`,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error("Set tier exception:", error);
      toast({ title: "Error", description: "Failed to set tier - network error", variant: "destructive" });
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
            {activeTab === "smartflow" && (
              <SmartFlowIntegrityTab
                integrity={smartflowIntegrity}
                topology={smartflowTopology}
                loading={loading}
                onRefresh={fetchData}
              />
            )}
            {activeTab === "pipeline" && (
              <PipelineTab pipelineStatus={pipelineStatus} loading={loading} />
            )}
            {activeTab === "logs" && (
              <LogsTab logs={systemLogs} loading={loading} onRefresh={fetchData} />
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
              <BrokersTab connectedAccounts={connectedAccounts} loading={loading} />
            )}
            {activeTab === "config" && (
              <ConfigTab
                envVars={allEnvVars}
                loading={loading}
                onRefresh={fetchData}
              />
            )}
            {activeTab === "env" && (
              <SystemTab envDoctor={envDoctor} loading={loading} />
            )}
            {activeTab === "broadcast" && (
              <BroadcastTab />
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
  const { toast } = useToast();
  const [selectedUserLogs, setSelectedUserLogs] = useState<{
    userId: number;
    email: string;
    logs: any[];
    loading: boolean;
  } | null>(null);

  const handleViewLogs = async (userId: number, email: string) => {
    setSelectedUserLogs({ userId, email, logs: [], loading: true });
    try {
      const response = await fetch(`/api/admin/users/${userId}/logs`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedUserLogs({ userId, email, logs: data.logs || [], loading: false });
      } else {
        toast({ title: "Error", description: "Failed to fetch user logs", variant: "destructive" });
        setSelectedUserLogs(null);
      }
    } catch {
      toast({ title: "Error", description: "Failed to fetch user logs", variant: "destructive" });
      setSelectedUserLogs(null);
    }
  };

  if (loading) {
    return <Skeleton className="h-96" />;
  }

  return (
    <>
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
                          <SelectItem value="trader">Trader</SelectItem>
                          <SelectItem value="pro">Pro</SelectItem>
                          <SelectItem value="enterprise">Enterprise</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(user.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewLogs(user.id, user.email)}
                          title="View Logs"
                        >
                          <ScrollText className="h-4 w-4 text-blue-500" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onToggleActive(user.id)}
                          title={user.is_active ? "Deactivate" : "Activate"}
                        >
                          {user.is_active ? (
                            <X className="h-4 w-4 text-destructive" />
                          ) : (
                            <Check className="h-4 w-4 text-emerald-500" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* User Logs Dialog */}
      <Dialog open={!!selectedUserLogs} onOpenChange={() => setSelectedUserLogs(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ScrollText className="h-5 w-5 text-primary" />
              Activity Logs for {selectedUserLogs?.email}
            </DialogTitle>
            <DialogDescription>
              Recent signals and trades for this user
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto">
            {selectedUserLogs?.loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : selectedUserLogs?.logs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <ScrollText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No activity logs found for this user</p>
              </div>
            ) : (
              <div className="space-y-2">
                {selectedUserLogs?.logs.map((log: any, i: number) => (
                  <div
                    key={`${log.type}-${log.id}-${i}`}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/50"
                  >
                    <div className={`w-2 h-2 rounded-full ${log.type === "signal" ? "bg-blue-500" : "bg-emerald-500"}`} />
                    <Badge variant="outline" className="text-xs">
                      {log.type}
                    </Badge>
                    <span className="text-sm font-medium">{log.symbol || "-"}</span>
                    <Badge variant={log.action === "buy" ? "default" : "secondary"} className="text-xs">
                      {log.action}
                    </Badge>
                    <span className="text-xs text-muted-foreground flex-1 text-right">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : "-"}
                    </span>
                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        log.status === "executed" || log.status === "processed"
                          ? "text-emerald-500 border-emerald-500/50"
                          : log.status === "failed"
                          ? "text-red-500 border-red-500/50"
                          : "text-amber-500 border-amber-500/50"
                      }`}
                    >
                      {log.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedUserLogs(null)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
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

// Brokers Tab - Shows connected accounts from database
function BrokersTab({ connectedAccounts, loading }: { connectedAccounts: any; loading: boolean }) {
  if (loading || !connectedAccounts) {
    return <Skeleton className="h-96" />;
  }

  const brokerDisplayNames: Record<string, string> = {
    mt4: "MetaTrader 4",
    mt5: "MetaTrader 5",
    tradelocker: "TradeLocker",
    tradovate: "Tradovate",
    projectx: "ProjectX",
    topstep: "TopStep",
  };

  const brokerColors: Record<string, string> = {
    mt4: "from-blue-500/20 to-cyan-500/20 border-blue-500/30",
    mt5: "from-purple-500/20 to-pink-500/20 border-purple-500/30",
    tradelocker: "from-emerald-500/20 to-teal-500/20 border-emerald-500/30",
    tradovate: "from-orange-500/20 to-amber-500/20 border-orange-500/30",
    projectx: "from-rose-500/20 to-red-500/20 border-rose-500/30",
    topstep: "from-indigo-500/20 to-violet-500/20 border-indigo-500/30",
  };

  const brokers = Object.entries(connectedAccounts.brokers || {});

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">{connectedAccounts.summary?.total || 0}</div>
              <p className="text-sm text-muted-foreground">Total Accounts</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-emerald-500">{connectedAccounts.summary?.active || 0}</div>
              <p className="text-sm text-muted-foreground">Active</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-cyan-500">{connectedAccounts.summary?.connected || 0}</div>
              <p className="text-sm text-muted-foreground">Connected</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Broker Groups */}
      {brokers.length === 0 ? (
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardContent className="py-12 text-center">
            <Server className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-2">No Connected Accounts</h3>
            <p className="text-muted-foreground">Users haven't connected any broker accounts yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {brokers.map(([brokerKey, brokerData]: [string, any], i) => (
            <motion.div
              key={brokerKey}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <Card className={`border bg-gradient-to-br ${brokerColors[brokerKey] || "from-gray-500/20 to-slate-500/20 border-gray-500/30"}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">
                      {brokerDisplayNames[brokerKey] || brokerKey.toUpperCase()}
                    </CardTitle>
                    <div className="flex gap-2">
                      <Badge variant="outline" className="bg-background/50">
                        {brokerData.count} accounts
                      </Badge>
                      <Badge variant="outline" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                        {brokerData.active} active
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {brokerData.accounts.map((account: any) => (
                      <div
                        key={account.id}
                        className="flex items-center justify-between p-3 rounded-lg bg-background/50 border border-border/50"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium truncate">
                              {account.account_name || account.account_number}
                            </span>
                            {account.is_connected && (
                              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground truncate">
                            {account.user_email}
                          </p>
                        </div>
                        <div className="text-right ml-4">
                          <div className="text-sm font-medium">
                            ${account.balance?.toLocaleString() || "0"}
                          </div>
                          <p className="text-xs text-muted-foreground">Balance</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

// Config Tab - Environment Variables Management
function ConfigTab({
  envVars,
  loading,
  onRefresh,
}: {
  envVars: any;
  loading: boolean;
  onRefresh: () => void;
}) {
  const { toast } = useToast();
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [restarting, setRestarting] = useState(false);

  const handleRestart = async () => {
    if (!confirm("Are you sure you want to restart the backend? This will briefly interrupt service.")) {
      return;
    }

    setRestarting(true);
    try {
      const response = await fetch("/api/admin/system/restart", {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        toast({
          title: "Restarting...",
          description: "Backend is restarting. Please wait 5-10 seconds and refresh.",
        });
        // Wait a bit then refresh
        setTimeout(() => {
          window.location.reload();
        }, 6000);
      } else {
        const data = await response.json();
        toast({ title: "Error", description: data.error || "Failed to restart", variant: "destructive" });
        setRestarting(false);
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to restart backend", variant: "destructive" });
      setRestarting(false);
    }
  };

  if (loading || !envVars) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32" />
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      </div>
    );
  }

  const categoryIcons: Record<string, any> = {
    stripe: CreditCard,
    database: Database,
    redis: Zap,
    auth: Lock,
    oauth: Key,
    email: Activity,
    brokers: Server,
  };

  const categoryColors: Record<string, string> = {
    stripe: "from-violet-500/20 to-purple-500/20 border-violet-500/30",
    database: "from-blue-500/20 to-cyan-500/20 border-blue-500/30",
    redis: "from-red-500/20 to-orange-500/20 border-red-500/30",
    auth: "from-emerald-500/20 to-green-500/20 border-emerald-500/30",
    oauth: "from-amber-500/20 to-yellow-500/20 border-amber-500/30",
    email: "from-pink-500/20 to-rose-500/20 border-pink-500/30",
    brokers: "from-indigo-500/20 to-blue-500/20 border-indigo-500/30",
  };

  const handleEdit = (key: string, currentValue: string) => {
    setEditingKey(key);
    setEditValue(currentValue === "[REDACTED]" ? "" : currentValue);
  };

  const handleSave = async (key: string) => {
    if (!editValue.trim()) {
      toast({ title: "Error", description: "Value cannot be empty", variant: "destructive" });
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`/api/admin/system/env-var/${encodeURIComponent(key)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ value: editValue }),
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Configuration updated. Restart backend to apply changes.",
        });
        setEditingKey(null);
        setEditValue("");
        onRefresh();
      } else {
        const data = await response.json();
        toast({ title: "Error", description: data.error || "Failed to update", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to save configuration", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditValue("");
  };

  const toggleShowSecret = (key: string) => {
    setShowSecrets((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const copyToClipboard = (value: string) => {
    if (value && value !== "[REDACTED]" && value !== "[NOT SET]") {
      navigator.clipboard.writeText(value);
      toast({ title: "Copied", description: "Value copied to clipboard" });
    }
  };

  const categories = Object.entries(envVars.categories || {});

  // Count configured and total variables
  let totalVars = 0;
  let configuredVars = 0;
  categories.forEach(([_, category]: [string, any]) => {
    Object.values(category.variables || {}).forEach((v: any) => {
      totalVars++;
      if (v.configured) configuredVars++;
    });
  });

  return (
    <div className="space-y-6">
      {/* Summary Banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 rounded-xl border bg-gradient-to-r from-primary/10 to-primary/5 border-primary/30"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Settings className="h-6 w-6 text-primary" />
            <div>
              <h3 className="font-semibold text-lg">System Configuration</h3>
              <p className="text-sm text-muted-foreground">
                {configuredVars} of {totalVars} variables configured
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/30">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Restart required after changes
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRestart}
              disabled={restarting}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${restarting ? "animate-spin" : ""}`} />
              {restarting ? "Restarting..." : "Restart Backend"}
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Category Cards */}
      <div className="grid gap-6 md:grid-cols-2">
        {categories.map(([categoryKey, category]: [string, any], i) => {
          const Icon = categoryIcons[categoryKey] || Settings;
          const variables = Object.entries(category.variables || {});
          const configuredCount = variables.filter(([_, v]: [string, any]) => v.configured).length;

          return (
            <motion.div
              key={categoryKey}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className={`border bg-gradient-to-br ${categoryColors[categoryKey] || "from-gray-500/20 to-slate-500/20 border-gray-500/30"}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-background/50 flex items-center justify-center">
                        <Icon className="h-4 w-4" />
                      </div>
                      <CardTitle className="text-lg">{category.name}</CardTitle>
                    </div>
                    <Badge variant="outline" className="bg-background/50">
                      {configuredCount}/{variables.length}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {variables.map(([varKey, varData]: [string, any]) => (
                      <div
                        key={varKey}
                        className="p-3 rounded-lg bg-background/50 border border-border/50"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-medium">{varKey}</span>
                            {varData.is_secret && (
                              <Lock className="h-3 w-3 text-amber-500" />
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            {varData.configured ? (
                              <Badge variant="outline" className="text-xs text-emerald-500 border-emerald-500/50">
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                Set
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-xs">
                                <XCircle className="h-3 w-3 mr-1" />
                                Not Set
                              </Badge>
                            )}
                          </div>
                        </div>

                        {editingKey === varKey ? (
                          <div className="flex items-center gap-2 mt-2">
                            <Input
                              type={varData.is_secret ? "password" : "text"}
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              placeholder={varData.is_secret ? "Enter new value..." : "Enter value..."}
                              className="h-8 text-xs font-mono"
                              autoFocus
                            />
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleSave(varKey)}
                              disabled={saving}
                              className="h-8 px-2"
                            >
                              {saving ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <Check className="h-3 w-3 text-emerald-500" />
                              )}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={handleCancel}
                              className="h-8 px-2"
                            >
                              <X className="h-3 w-3 text-destructive" />
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-between mt-2">
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                              <span className="text-xs text-muted-foreground font-mono truncate">
                                {varData.is_secret && !showSecrets[varKey]
                                  ? varData.value === "[NOT SET]"
                                    ? "[NOT SET]"
                                    : "••••••••"
                                  : varData.value || "[NOT SET]"}
                              </span>
                            </div>
                            <div className="flex items-center gap-1 ml-2">
                              {varData.is_secret && varData.configured && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => toggleShowSecret(varKey)}
                                  className="h-6 w-6 p-0"
                                >
                                  {showSecrets[varKey] ? (
                                    <EyeOff className="h-3 w-3" />
                                  ) : (
                                    <Eye className="h-3 w-3" />
                                  )}
                                </Button>
                              )}
                              {varData.configured && !varData.is_secret && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => copyToClipboard(varData.value)}
                                  className="h-6 w-6 p-0"
                                >
                                  <Copy className="h-3 w-3" />
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEdit(varKey, varData.value || "")}
                                className="h-6 w-6 p-0"
                              >
                                <Settings className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        )}

                        {varData.source === "database" && (
                          <div className="mt-1">
                            <Badge variant="outline" className="text-[10px] text-cyan-500 border-cyan-500/30">
                              DB Override
                            </Badge>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Info Note */}
      <Card className="border-border/50 bg-card/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
            <div className="text-sm text-muted-foreground">
              <p className="font-medium text-foreground mb-1">Configuration Notes:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Changes are stored in the database and override environment variables</li>
                <li>Backend service must be restarted for changes to take effect</li>
                <li>Secret values are always encrypted and redacted in the UI</li>
                <li>Original .env file values remain unchanged</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
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

// Logs Tab - System Activity Logs
function LogsTab({ logs, loading, onRefresh }: { logs: any; loading: boolean; onRefresh: () => void }) {
  const [logFilter, setLogFilter] = useState("all");

  if (loading && !logs) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  const getLogIcon = (type: string) => {
    switch (type) {
      case "signal":
        return Signal;
      case "trade":
        return ArrowUpDown;
      case "webhook":
        return Zap;
      default:
        return Activity;
    }
  };

  const getLogColor = (type: string, status: string) => {
    if (status === "failed" || status === "error") return "text-red-500 bg-red-500/10 border-red-500/30";
    if (status === "pending") return "text-amber-500 bg-amber-500/10 border-amber-500/30";
    switch (type) {
      case "signal":
        return "text-blue-500 bg-blue-500/10 border-blue-500/30";
      case "trade":
        return "text-emerald-500 bg-emerald-500/10 border-emerald-500/30";
      case "webhook":
        return "text-purple-500 bg-purple-500/10 border-purple-500/30";
      default:
        return "text-gray-500 bg-gray-500/10 border-gray-500/30";
    }
  };

  const filteredLogs = logs?.logs?.filter((log: any) =>
    logFilter === "all" ? true : log.type === logFilter
  ) || [];

  return (
    <div className="space-y-6">
      {/* Header with filters */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-primary" />
            System Logs
          </h2>
          <Badge variant="outline">{logs?.total || 0} entries</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Select value={logFilter} onValueChange={setLogFilter}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Logs</SelectItem>
              <SelectItem value="signal">Signals</SelectItem>
              <SelectItem value="trade">Trades</SelectItem>
              <SelectItem value="webhook">Webhooks</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={onRefresh} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </motion.div>

      {/* Logs Table */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">Type</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Message</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-12">
                      <ScrollText className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
                      <p className="text-muted-foreground">No logs found</p>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredLogs.map((log: any, i: number) => {
                    const Icon = getLogIcon(log.type);
                    return (
                      <motion.tr
                        key={`${log.type}-${log.id}-${i}`}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.02 }}
                        className="hover:bg-primary/5"
                      >
                        <TableCell>
                          <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${getLogColor(log.type, log.status)}`}>
                            <Icon className="h-3 w-3" />
                            {log.type}
                          </div>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground font-mono">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : "-"}
                        </TableCell>
                        <TableCell className="text-sm">
                          {log.user_email || "-"}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {log.action}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium">
                          {log.symbol || "-"}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={`text-xs ${
                              log.status === "executed" || log.status === "processed" || log.status === "active"
                                ? "text-emerald-500 border-emerald-500/50"
                                : log.status === "failed" || log.status === "error"
                                ? "text-red-500 border-red-500/50"
                                : "text-amber-500 border-amber-500/50"
                            }`}
                          >
                            {log.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[300px] truncate">
                          {log.message}
                        </TableCell>
                      </motion.tr>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Live Activity Summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-border/50 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Signal className="h-5 w-5 text-blue-500" />
              <div>
                <div className="text-2xl font-bold">
                  {logs?.logs?.filter((l: any) => l.type === "signal").length || 0}
                </div>
                <p className="text-sm text-muted-foreground">Signals</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border-emerald-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <ArrowUpDown className="h-5 w-5 text-emerald-500" />
              <div>
                <div className="text-2xl font-bold">
                  {logs?.logs?.filter((l: any) => l.type === "trade").length || 0}
                </div>
                <p className="text-sm text-muted-foreground">Trades</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Zap className="h-5 w-5 text-purple-500" />
              <div>
                <div className="text-2xl font-bold">
                  {logs?.logs?.filter((l: any) => l.type === "webhook").length || 0}
                </div>
                <p className="text-sm text-muted-foreground">Webhooks</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Broadcast Tab - Send mass emails/notifications to users
function BroadcastTab() {
  const { toast } = useToast();
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [ctaText, setCtaText] = useState("");
  const [ctaUrl, setCtaUrl] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [sending, setSending] = useState(false);
  const [lastResult, setLastResult] = useState<{
    sent: number;
    failed: number;
    total: number;
  } | null>(null);

  const sendBroadcast = async () => {
    if (!subject.trim() || !message.trim()) {
      toast({
        title: "Error",
        description: "Subject and message are required",
        variant: "destructive",
      });
      return;
    }

    setSending(true);
    try {
      const response = await fetch("/api/admin/broadcast/email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          subject,
          message,
          cta_text: ctaText || undefined,
          cta_url: ctaUrl || undefined,
          tier_filter: tierFilter === "all" ? undefined : tierFilter,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setLastResult({
          sent: data.sent,
          failed: data.failed,
          total: data.total_users,
        });
        toast({
          title: "Broadcast Sent",
          description: `Email sent to ${data.sent} users`,
        });
        // Clear form
        setSubject("");
        setMessage("");
        setCtaText("");
        setCtaUrl("");
      } else {
        toast({
          title: "Error",
          description: data.message || "Failed to send broadcast",
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to send broadcast",
        variant: "destructive",
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-primary" />
            Send Broadcast Email
          </CardTitle>
          <CardDescription>
            Send email to all users or a specific tier. Use for maintenance announcements, feature updates, etc.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="broadcast-subject">Subject</Label>
            <Input
              id="broadcast-subject"
              placeholder="e.g., Scheduled Maintenance - Jan 30"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="broadcast-message">Message</Label>
            <Textarea
              id="broadcast-message"
              placeholder="Write your message here..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={6}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="cta-text">CTA Button Text (optional)</Label>
              <Input
                id="cta-text"
                placeholder="e.g., View Status Page"
                value={ctaText}
                onChange={(e) => setCtaText(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cta-url">CTA Button URL (optional)</Label>
              <Input
                id="cta-url"
                placeholder="https://..."
                value={ctaUrl}
                onChange={(e) => setCtaUrl(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tier-filter">Filter by Tier (optional)</Label>
            <Select value={tierFilter} onValueChange={setTierFilter}>
              <SelectTrigger id="tier-filter">
                <SelectValue placeholder="All users" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Users</SelectItem>
                <SelectItem value="free">Free</SelectItem>
                <SelectItem value="starter">Starter</SelectItem>
                <SelectItem value="trader">Trader</SelectItem>
                <SelectItem value="pro">Pro</SelectItem>
                <SelectItem value="enterprise">Enterprise</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between pt-4">
            <div className="text-sm text-muted-foreground">
              {lastResult && (
                <span>
                  Last broadcast: {lastResult.sent}/{lastResult.total} sent
                  {lastResult.failed > 0 && ` (${lastResult.failed} failed)`}
                </span>
              )}
            </div>
            <Button onClick={sendBroadcast} disabled={sending}>
              {sending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Mail className="mr-2 h-4 w-4" />
                  Send Broadcast
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      {(subject || message) && (
        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle className="text-sm">Email Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border p-4 bg-white dark:bg-gray-900">
              <div className="text-center mb-4 pb-4 border-b">
                <h1 className="text-xl font-bold text-indigo-600">MyTradeFlow</h1>
                <p className="text-xs text-gray-500">Automated Trading Signal Router</p>
              </div>
              <h2 className="font-semibold text-lg mb-2">{subject || "Subject"}</h2>
              <p className="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{message || "Your message here..."}</p>
              {ctaText && ctaUrl && (
                <div className="mt-4 text-center">
                  <span className="inline-block bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium">
                    {ctaText}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// SmartFlow Integrity Tab - Live System Health & Topology
function SmartFlowIntegrityTab({
  integrity,
  topology,
  loading,
  onRefresh,
}: {
  integrity: any;
  topology: any;
  loading: boolean;
  onRefresh: () => void;
}) {
  if (loading && !integrity && !topology) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
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
      case "critical":
        return "bg-red-500";
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
      case "critical":
        return "bg-red-500/10 border-red-500/50";
      default:
        return "bg-gray-500/10 border-gray-500/50";
    }
  };

  return (
    <div className="space-y-6">
      {/* Health Score Banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 rounded-xl border ${getStatusBg(integrity?.overall_status || "unknown")}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-4 h-4 rounded-full ${getStatusColor(integrity?.overall_status || "unknown")} animate-pulse`} />
            <div>
              <h3 className="font-semibold text-lg">
                SmartFlow Health: {integrity?.overall_status?.toUpperCase() || "CHECKING..."}
              </h3>
              <p className="text-sm text-muted-foreground">
                Score: {integrity?.health_score ?? "..."} / 100 |
                Baseline: {integrity?.baseline_version || "None"} |
                Drift: {integrity?.drift_count ?? 0} finding(s)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {integrity?.critical_drift_count > 0 && (
              <Badge variant="destructive" className="animate-pulse">
                <AlertTriangle className="h-3 w-3 mr-1" />
                {integrity.critical_drift_count} Critical
              </Badge>
            )}
            <Button variant="outline" size="sm" onClick={onRefresh} className="gap-2">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Category Scores */}
      {integrity?.category_scores && (
        <div className="grid gap-4 md:grid-cols-4 lg:grid-cols-8">
          {Object.entries(integrity.category_scores).map(([category, score]: [string, any], i) => (
            <motion.div
              key={category}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className={`border ${score >= 80 ? "border-emerald-500/30" : score >= 50 ? "border-amber-500/30" : "border-red-500/30"}`}>
                <CardContent className="pt-4 pb-3 text-center">
                  <div className={`text-2xl font-bold ${score >= 80 ? "text-emerald-500" : score >= 50 ? "text-amber-500" : "text-red-500"}`}>
                    {score}
                  </div>
                  <p className="text-xs text-muted-foreground capitalize">{category.replace(/_/g, " ")}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Topology Visualization */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            SmartFlow Runtime Topology
          </CardTitle>
          <CardDescription>
            Live signal processing pipeline status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative overflow-x-auto">
            <div className="flex items-center justify-between min-w-[1000px] py-6">
              {topology?.nodes?.map((node: any, i: number) => (
                <React.Fragment key={node.id}>
                  {i > 0 && (
                    <div className="flex-1 flex items-center justify-center relative mx-1">
                      <motion.div
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ delay: i * 0.05 }}
                        className="h-0.5 bg-gradient-to-r from-primary/30 to-primary/60 w-full"
                      />
                      <motion.div
                        animate={{ x: [0, 15, 0] }}
                        transition={{ repeat: Infinity, duration: 2, delay: i * 0.2 }}
                        className="absolute w-1.5 h-1.5 bg-primary rounded-full"
                      />
                    </div>
                  )}
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex flex-col items-center"
                  >
                    <div
                      className={`w-14 h-14 rounded-xl border-2 flex items-center justify-center relative ${getStatusBg(node.status)}`}
                    >
                      {node.drift_flag && (
                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-amber-500 rounded-full animate-pulse" />
                      )}
                      <div className={`w-2 h-2 rounded-full ${getStatusColor(node.status)}`} />
                    </div>
                    <span className="text-[10px] mt-1.5 font-medium text-center max-w-[60px] truncate">
                      {node.name}
                    </span>
                  </motion.div>
                </React.Fragment>
              )) || (
                <div className="text-center py-8 text-muted-foreground w-full">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Loading topology...</p>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Components Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {integrity?.components?.map((component: any, i: number) => (
          <motion.div
            key={component.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
          >
            <Card className={`border ${getStatusBg(component.status)}`}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(component.status)} animate-pulse`} />
                    <CardTitle className="text-sm font-medium">{component.name}</CardTitle>
                  </div>
                  {component.drift_flag && (
                    <Badge variant="outline" className="text-amber-500 border-amber-500/50 text-[10px]">
                      Drift
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">{component.message}</p>
                {component.last_success && (
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Last: {new Date(component.last_success).toLocaleString()}
                  </p>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Notes / Warnings */}
      {integrity?.notes?.length > 0 && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Notes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-muted-foreground space-y-1">
              {integrity.notes.map((note: string, i: number) => (
                <li key={i}>• {note}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Baseline Info */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            Golden Baseline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-xs text-muted-foreground">Version</p>
              <p className="font-medium">{integrity?.baseline_version || "Not loaded"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Last Check</p>
              <p className="font-medium">
                {integrity?.timestamp ? new Date(integrity.timestamp).toLocaleString() : "-"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Health Score</p>
              <p className={`font-bold text-xl ${
                (integrity?.health_score ?? 0) >= 80 ? "text-emerald-500" :
                (integrity?.health_score ?? 0) >= 50 ? "text-amber-500" : "text-red-500"
              }`}>
                {integrity?.health_score ?? "-"}%
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
