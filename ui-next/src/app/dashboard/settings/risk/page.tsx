"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Shield, AlertTriangle, DollarSign, TrendingDown, Zap, Clock, Info, Calendar, Lock } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useUser } from "@/providers/user-provider";
import Link from "next/link";

interface GlobalRiskSettings {
  default_max_daily_trades: number | null;
  default_max_open_positions: number | null;
  default_max_daily_loss: number | null;
  default_max_daily_loss_pct: number | null;
  default_max_drawdown_pct: number | null;
  default_trade_cooldown_seconds: number | null;
  default_position_sizing_mode: string | null;
  default_fixed_lot_size: number | null;
  default_risk_percent_per_trade: number | null;
  risk_management_enabled: boolean;
}

interface MomentumSettings {
  warn_at: number;
  auto_breakeven: boolean;
  pause_on_chop: boolean;
  max_exposure: number;
  auto_pause_on_exposure: boolean;
  allow_hedge: boolean;
  staleness_enabled: boolean;
  staleness_seconds: number;
  force_old_signals: boolean;
  discard_flush_interval: string;
  // Trading Session
  trading_session_enabled: boolean;
  trading_session_start: string;
  trading_session_end: string;
  trading_session_timezone: string;
  trading_session_days: number[];
  trading_sessions_preset?: string[]; // Selected preset sessions
}

// Predefined trading sessions
const TRADING_SESSION_PRESETS = {
  london: {
    id: "london",
    name: "London Session",
    description: "08:00 - 16:00 GMT",
    start: "08:00",
    end: "16:00",
    timezone: "Europe/London",
    days: [1, 2, 3, 4, 5],
  },
  new_york: {
    id: "new_york",
    name: "New York Session",
    description: "09:30 - 16:00 ET",
    start: "09:30",
    end: "16:00",
    timezone: "America/New_York",
    days: [1, 2, 3, 4, 5],
  },
  asian: {
    id: "asian",
    name: "Asian Session (Tokyo)",
    description: "09:00 - 15:00 JST",
    start: "09:00",
    end: "15:00",
    timezone: "Asia/Tokyo",
    days: [1, 2, 3, 4, 5],
  },
} as const;

export default function RiskSettingsPage() {
  const [settings, setSettings] = useState<GlobalRiskSettings | null>(null);
  const [momentumSettings, setMomentumSettings] = useState<MomentumSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  const { user } = useUser();

  // Check if user is on free tier (trading session not available for free users)
  const isFreeTier = user?.subscription_tier === "free" || !user?.subscription_tier;

  useEffect(() => {
    fetchSettings();
    fetchMomentumSettings();
  }, []);

  async function fetchMomentumSettings() {
    try {
      const res = await fetch("/api/signal-intelligence/settings", {
        credentials: 'include',
      });
      if (res.ok) {
        setMomentumSettings(await res.json());
      } else {
        // Set defaults if fetch fails
        setMomentumSettings({
          warn_at: 6,
          auto_breakeven: false,
          pause_on_chop: true,
          max_exposure: 5000,
          auto_pause_on_exposure: true,
          allow_hedge: false,
          staleness_enabled: true,
          staleness_seconds: 5,
          force_old_signals: false,
          discard_flush_interval: "24h",
          trading_session_enabled: false,
          trading_session_start: "09:30",
          trading_session_end: "16:00",
          trading_session_timezone: "America/New_York",
          trading_session_days: [1, 2, 3, 4, 5],
        });
      }
    } catch (error) {
      console.error("Error fetching momentum settings:", error);
      setMomentumSettings({
        warn_at: 6,
        auto_breakeven: false,
        pause_on_chop: true,
        max_exposure: 5000,
        auto_pause_on_exposure: true,
        allow_hedge: false,
        staleness_enabled: true,
        staleness_seconds: 5,
        force_old_signals: false,
        discard_flush_interval: "24h",
        trading_session_enabled: false,
        trading_session_start: "09:30",
        trading_session_end: "16:00",
        trading_session_timezone: "America/New_York",
        trading_session_days: [1, 2, 3, 4, 5],
      });
    }
  }

  async function fetchSettings() {
    try {
      const res = await fetch("/api/risk/settings", {
        credentials: 'include',
      });
      if (res.ok) {
        setSettings(await res.json());
      } else {
        console.error("Failed to fetch risk settings:", res.status);
        // Set defaults if fetch fails
        setSettings({
          default_max_daily_trades: null,
          default_max_open_positions: null,
          default_max_daily_loss: null,
          default_max_daily_loss_pct: null,
          default_max_drawdown_pct: null,
          default_trade_cooldown_seconds: null,
          default_position_sizing_mode: "fixed",
          default_fixed_lot_size: 0.01,
          default_risk_percent_per_trade: 1.0,
          risk_management_enabled: true,
        });
      }
    } catch (error) {
      console.error("Error fetching risk settings:", error);
      // Set defaults on error
      setSettings({
        default_max_daily_trades: null,
        default_max_open_positions: null,
        default_max_daily_loss: null,
        default_max_daily_loss_pct: null,
        default_max_drawdown_pct: null,
        default_trade_cooldown_seconds: null,
        default_position_sizing_mode: "fixed",
        default_fixed_lot_size: 0.01,
        default_risk_percent_per_trade: 1.0,
        risk_management_enabled: true,
      });
    }
  }

  async function saveSettings() {
    setSaving(true);
    try {
      const [res1, res2] = await Promise.all([
        fetch("/api/risk/settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: 'include',
          body: JSON.stringify(settings),
        }),
        momentumSettings ? fetch("/api/signal-intelligence/settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: 'include',
          body: JSON.stringify(momentumSettings),
        }) : Promise.resolve({ ok: true }),
      ]);
      
      if (res1.ok && res2.ok) {
        toast({ title: "Settings saved", description: "All settings updated successfully" });
      } else {
        toast({ title: "Error", description: "Failed to save some settings", variant: "destructive" });
      }
    } finally {
      setSaving(false);
    }
  }

  if (!settings || !momentumSettings) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Risk Management</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Risk Management</h1>
        <p className="text-muted-foreground">
          Configure global risk limits that apply to all accounts by default
        </p>
      </div>

      {/* Broker Compatibility Note */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>Multi-Broker Compatible</AlertTitle>
        <AlertDescription>
          These settings adapt automatically to each broker:
          <ul className="mt-2 text-sm space-y-1">
            <li><strong>TradeLocker/MT4/MT5:</strong> Lot sizes (0.01 = micro lot), pips for SL/TP</li>
            <li><strong>ProjectX/TopStep:</strong> Contracts (1 = 1 contract), points for SL/TP</li>
            <li><strong>Tradovate:</strong> Contracts, percentage-based risk</li>
          </ul>
        </AlertDescription>
      </Alert>

      {/* Master toggle */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Risk Management
          </CardTitle>
          <CardDescription>Enable or disable all risk checks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <Label>Enable Risk Management</Label>
            <Switch
              checked={settings.risk_management_enabled}
              onCheckedChange={(v) => setSettings({ ...settings, risk_management_enabled: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Trade Limits */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Trade Limits
          </CardTitle>
          <CardDescription>Default limits for new signals and positions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Max Daily Trades</Label>
              <Input
                type="number"
                value={settings.default_max_daily_trades || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_max_daily_trades: e.target.value ? parseInt(e.target.value) : null
                })}
                placeholder="Unlimited"
              />
            </div>
            <div>
              <Label>Max Open Positions</Label>
              <Input
                type="number"
                value={settings.default_max_open_positions || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_max_open_positions: e.target.value ? parseInt(e.target.value) : null
                })}
                placeholder="Unlimited"
              />
            </div>
            <div>
              <Label>Trade Cooldown (seconds)</Label>
              <Input
                type="number"
                value={settings.default_trade_cooldown_seconds || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_trade_cooldown_seconds: e.target.value ? parseInt(e.target.value) : null
                })}
                placeholder="No cooldown"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loss Limits */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5" />
            Loss Protection
          </CardTitle>
          <CardDescription>Stop trading when loss limits are hit</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Max Daily Loss ($)</Label>
              <Input
                type="number"
                value={settings.default_max_daily_loss || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_max_daily_loss: e.target.value ? parseFloat(e.target.value) : null
                })}
                placeholder="No limit"
              />
            </div>
            <div>
              <Label>Max Daily Loss (%)</Label>
              <div className="space-y-2">
                <Slider
                  value={settings.default_max_daily_loss_pct || 0}
                  onValueChange={(value) => setSettings({
                    ...settings,
                    default_max_daily_loss_pct: value > 0 ? value : null
                  })}
                  min={0}
                  max={50}
                  step={0.5}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0%</span>
                  <span className="font-medium">{settings.default_max_daily_loss_pct || 0}%</span>
                  <span>50%</span>
                </div>
              </div>
            </div>
            <div>
              <Label>Max Drawdown (%)</Label>
              <div className="space-y-2">
                <Slider
                  value={settings.default_max_drawdown_pct || 0}
                  onValueChange={(value) => setSettings({
                    ...settings,
                    default_max_drawdown_pct: value > 0 ? value : null
                  })}
                  min={0}
                  max={50}
                  step={0.5}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0%</span>
                  <span className="font-medium">{settings.default_max_drawdown_pct || 0}%</span>
                  <span>50%</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Position Sizing */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Position Sizing Defaults
          </CardTitle>
          <CardDescription>
            Default position sizing for new accounts. Units adapt per broker (lots for forex, contracts for futures).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Position Sizing Mode</Label>
            <Select
              value={settings.default_position_sizing_mode || "fixed"}
              onValueChange={(v) => setSettings({ ...settings, default_position_sizing_mode: v })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fixed">Fixed Size (Lots/Contracts)</SelectItem>
                <SelectItem value="percent_balance">% of Balance</SelectItem>
                <SelectItem value="percent_equity">% of Equity</SelectItem>
                <SelectItem value="risk_based">Risk-Based (% per trade)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Default Size (Lots / Contracts)</Label>
              <Input
                type="number"
                step="0.01"
                value={settings.default_fixed_lot_size || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_fixed_lot_size: e.target.value ? parseFloat(e.target.value) : null
                })}
                placeholder="0.01 for forex, 1 for futures"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Forex: 0.01 = micro lot | Futures: 1 = 1 contract
              </p>
            </div>
            <div>
              <Label>Risk % per Trade</Label>
              <div className="space-y-2">
                <Slider
                  value={settings.default_risk_percent_per_trade || 1}
                  onValueChange={(value) => setSettings({
                    ...settings,
                    default_risk_percent_per_trade: value
                  })}
                  min={0.1}
                  max={10}
                  step={0.1}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0.1%</span>
                  <span className="font-medium">{settings.default_risk_percent_per_trade || 1}%</span>
                  <span>10%</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Signal Intelligence Guard Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Signal Intelligence Guard
          </CardTitle>
          <CardDescription>Self-protecting execution guards for signal processing</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Momentum Guard */}
          <div className="space-y-4">
            <h3 className="font-semibold text-sm">Momentum Guard</h3>
            <div>
              <Label>Warning Threshold (opposite signals)</Label>
              <div className="space-y-2 mt-2">
                <Slider
                  value={momentumSettings.warn_at}
                  onValueChange={(value) => setMomentumSettings({ ...momentumSettings, warn_at: value })}
                  min={3}
                  max={15}
                  step={1}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>3</span>
                  <span className="font-medium">{momentumSettings.warn_at}</span>
                  <span>15</span>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label>Auto Breakeven</Label>
                <p className="text-xs text-muted-foreground">Move SL to entry on momentum warning</p>
              </div>
              <Switch
                checked={momentumSettings.auto_breakeven}
                onCheckedChange={(v) => setMomentumSettings({ ...momentumSettings, auto_breakeven: v })}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label>Pause on Choppy Market</Label>
                <p className="text-xs text-muted-foreground">Pause new entries when market is choppy</p>
              </div>
              <Switch
                checked={momentumSettings.pause_on_chop}
                onCheckedChange={(v) => setMomentumSettings({ ...momentumSettings, pause_on_chop: v })}
              />
            </div>
          </div>

          {/* Exposure Limits */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="font-semibold text-sm">Exposure Limits</h3>
            <div>
              <Label>Max Exposure ($)</Label>
              <Input
                type="number"
                value={momentumSettings.max_exposure}
                onChange={(e) => setMomentumSettings({
                  ...momentumSettings,
                  max_exposure: parseFloat(e.target.value) || 5000
                })}
                placeholder="5000"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label>Auto-Pause on Exposure Limit</Label>
                <p className="text-xs text-muted-foreground">Pause new entries when exposure limit hit</p>
              </div>
              <Switch
                checked={momentumSettings.auto_pause_on_exposure}
                onCheckedChange={(v) => setMomentumSettings({ ...momentumSettings, auto_pause_on_exposure: v })}
              />
            </div>
          </div>

          {/* Staleness Settings */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Staleness Protection
            </h3>
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Staleness Check</Label>
                <p className="text-xs text-muted-foreground">Skip signals older than threshold</p>
              </div>
              <Switch
                checked={momentumSettings.staleness_enabled}
                onCheckedChange={(v) => setMomentumSettings({ ...momentumSettings, staleness_enabled: v })}
              />
            </div>
            {momentumSettings.staleness_enabled && (
              <div>
                <Label>Staleness Threshold (seconds)</Label>
                <Input
                  type="number"
                  value={momentumSettings.staleness_seconds}
                  onChange={(e) => setMomentumSettings({
                    ...momentumSettings,
                    staleness_seconds: parseInt(e.target.value) || 5
                  })}
                  placeholder="5"
                />
              </div>
            )}
            <div className="flex items-center justify-between">
              <div>
                <Label>Force Old Signals</Label>
                <p className="text-xs text-muted-foreground">Allow execution of stale signals</p>
              </div>
              <Switch
                checked={momentumSettings.force_old_signals}
                onCheckedChange={(v) => setMomentumSettings({ ...momentumSettings, force_old_signals: v })}
              />
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="font-semibold text-sm">Advanced</h3>
            <div className="flex items-center justify-between">
              <div>
                <Label>Allow Hedging</Label>
                <p className="text-xs text-muted-foreground">Create reverse orders on momentum warning</p>
              </div>
              <Switch
                checked={momentumSettings.allow_hedge}
                onCheckedChange={(v) => setMomentumSettings({ ...momentumSettings, allow_hedge: v })}
              />
            </div>
            <div>
              <Label>Discard Bin Flush Interval</Label>
              <Select
                value={momentumSettings.discard_flush_interval}
                onValueChange={(v) => setMomentumSettings({ ...momentumSettings, discard_flush_interval: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">1 Hour</SelectItem>
                  <SelectItem value="24h">24 Hours</SelectItem>
                  <SelectItem value="30d">30 Days</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Trading Session */}
      <Card className={isFreeTier ? "opacity-75" : ""}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Trading Session
            {isFreeTier && (
              <span className="ml-2 inline-flex items-center gap-1 text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                <Lock className="h-3 w-3" />
                Paid Feature
              </span>
            )}
          </CardTitle>
          <CardDescription>
            Control when webhooks are active. Signals received outside your trading hours will be rejected.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isFreeTier ? (
            <Alert>
              <Lock className="h-4 w-4" />
              <AlertTitle>Upgrade Required</AlertTitle>
              <AlertDescription>
                Trading Session control is available on Starter plan and above.
                <Link href="/dashboard/settings/billing" className="ml-1 text-primary underline hover:no-underline">
                  Upgrade now
                </Link>
              </AlertDescription>
            </Alert>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <Label>Enable Trading Session</Label>
                  <p className="text-xs text-muted-foreground">Only execute signals during defined trading hours</p>
                </div>
                <Switch
                  checked={momentumSettings.trading_session_enabled}
                  onCheckedChange={(v) => setMomentumSettings({ ...momentumSettings, trading_session_enabled: v })}
                />
              </div>

          {momentumSettings.trading_session_enabled && (
            <>
              {/* Predefined Session Presets - Multi-select */}
              <div className="space-y-3">
                <Label>Select Trading Sessions</Label>
                <p className="text-xs text-muted-foreground mb-2">
                  Choose one or more predefined sessions, or customize your own below
                </p>
                <div className="grid gap-3">
                  {Object.values(TRADING_SESSION_PRESETS).map((preset) => {
                    const isSelected = momentumSettings.trading_sessions_preset?.includes(preset.id);
                    return (
                      <div
                        key={preset.id}
                        className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                          isSelected
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-primary/50"
                        }`}
                        onClick={() => {
                          const current = momentumSettings.trading_sessions_preset || [];
                          const newPresets = isSelected
                            ? current.filter((id) => id !== preset.id)
                            : [...current, preset.id];

                          // If selecting a preset, update the time/timezone to match
                          // Use the first selected preset's values
                          if (!isSelected && newPresets.length === 1) {
                            setMomentumSettings({
                              ...momentumSettings,
                              trading_sessions_preset: newPresets,
                              trading_session_start: preset.start,
                              trading_session_end: preset.end,
                              trading_session_timezone: preset.timezone,
                              trading_session_days: preset.days,
                            });
                          } else {
                            setMomentumSettings({
                              ...momentumSettings,
                              trading_sessions_preset: newPresets,
                            });
                          }
                        }}
                      >
                        <div className="flex items-center gap-3">
                          <Checkbox
                            checked={isSelected}
                            className="pointer-events-none"
                          />
                          <div>
                            <p className="font-medium text-sm">{preset.name}</p>
                            <p className="text-xs text-muted-foreground">{preset.description}</p>
                          </div>
                        </div>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Custom Time Range (always visible for fine-tuning) */}
              <div className="space-y-3 pt-4 border-t">
                <Label>Custom Time Range</Label>
                <p className="text-xs text-muted-foreground">
                  Fine-tune your session times or create a custom schedule
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs">Session Start</Label>
                    <Input
                      type="time"
                      value={momentumSettings.trading_session_start || "09:30"}
                      onChange={(e) => setMomentumSettings({
                        ...momentumSettings,
                        trading_session_start: e.target.value,
                        trading_sessions_preset: [], // Clear presets when customizing
                      })}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Session End</Label>
                    <Input
                      type="time"
                      value={momentumSettings.trading_session_end || "16:00"}
                      onChange={(e) => setMomentumSettings({
                        ...momentumSettings,
                        trading_session_end: e.target.value,
                        trading_sessions_preset: [], // Clear presets when customizing
                      })}
                    />
                  </div>
                </div>
              </div>

              {/* Timezone */}
              <div>
                <Label>Timezone</Label>
                <Select
                  value={momentumSettings.trading_session_timezone || "America/New_York"}
                  onValueChange={(v) => setMomentumSettings({
                    ...momentumSettings,
                    trading_session_timezone: v,
                    trading_sessions_preset: [], // Clear presets when customizing
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="America/New_York">Eastern Time (ET)</SelectItem>
                    <SelectItem value="America/Chicago">Central Time (CT)</SelectItem>
                    <SelectItem value="America/Denver">Mountain Time (MT)</SelectItem>
                    <SelectItem value="America/Los_Angeles">Pacific Time (PT)</SelectItem>
                    <SelectItem value="Europe/London">London (GMT/BST)</SelectItem>
                    <SelectItem value="Europe/Paris">Central European (CET)</SelectItem>
                    <SelectItem value="Asia/Tokyo">Tokyo (JST)</SelectItem>
                    <SelectItem value="Asia/Hong_Kong">Hong Kong (HKT)</SelectItem>
                    <SelectItem value="Asia/Singapore">Singapore (SGT)</SelectItem>
                    <SelectItem value="Australia/Sydney">Sydney (AEST)</SelectItem>
                    <SelectItem value="UTC">UTC</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Trading Days */}
              <div className="space-y-3">
                <Label>Trading Days</Label>
                <div className="flex flex-wrap gap-3">
                  {[
                    { day: 1, label: "Mon" },
                    { day: 2, label: "Tue" },
                    { day: 3, label: "Wed" },
                    { day: 4, label: "Thu" },
                    { day: 5, label: "Fri" },
                    { day: 6, label: "Sat" },
                    { day: 7, label: "Sun" },
                  ].map(({ day, label }) => (
                    <div key={day} className="flex items-center space-x-2">
                      <Checkbox
                        id={`day-${day}`}
                        checked={momentumSettings.trading_session_days?.includes(day)}
                        onCheckedChange={(checked) => {
                          const currentDays = momentumSettings.trading_session_days || [];
                          const newDays = checked
                            ? [...currentDays, day].sort()
                            : currentDays.filter((d) => d !== day);
                          setMomentumSettings({
                            ...momentumSettings,
                            trading_session_days: newDays,
                            trading_sessions_preset: [], // Clear presets when customizing
                          });
                        }}
                      />
                      <label
                        htmlFor={`day-${day}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {label}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Session Preview */}
              <Alert>
                <Calendar className="h-4 w-4" />
                <AlertTitle>Active Session</AlertTitle>
                <AlertDescription>
                  {(momentumSettings.trading_sessions_preset?.length || 0) > 0 ? (
                    <>
                      <span className="font-medium">
                        {momentumSettings.trading_sessions_preset?.map(id =>
                          TRADING_SESSION_PRESETS[id as keyof typeof TRADING_SESSION_PRESETS]?.name
                        ).join(", ")}
                      </span>
                      <br />
                    </>
                  ) : null}
                  Trading active: {momentumSettings.trading_session_start || "09:30"} - {momentumSettings.trading_session_end || "16:00"}{" "}
                  ({(momentumSettings.trading_session_timezone || "America/New_York").split("/").pop()?.replace("_", " ")})
                  <br />
                  Days: {momentumSettings.trading_session_days?.length === 7
                    ? "Every day"
                    : momentumSettings.trading_session_days?.length === 5 &&
                      [1, 2, 3, 4, 5].every(d => momentumSettings.trading_session_days?.includes(d))
                    ? "Weekdays only"
                    : momentumSettings.trading_session_days?.map(d =>
                        ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d]
                      ).join(", ") || "None selected"
                  }
                </AlertDescription>
              </Alert>
            </>
          )}
            </>
          )}
        </CardContent>
      </Card>

      <Button onClick={saveSettings} disabled={saving}>
        {saving ? "Saving..." : "Save Settings"}
      </Button>
    </div>
  );
}
