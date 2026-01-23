"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Shield, AlertTriangle, DollarSign, TrendingDown, Zap, Clock } from "lucide-react";
import { Slider } from "@/components/ui/slider";

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
}

export default function RiskSettingsPage() {
  const [settings, setSettings] = useState<GlobalRiskSettings | null>(null);
  const [momentumSettings, setMomentumSettings] = useState<MomentumSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchSettings();
    fetchMomentumSettings();
  }, []);

  async function fetchMomentumSettings() {
    try {
      const res = await fetch("/api/signal-intelligence/settings");
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
      });
    }
  }

  async function fetchSettings() {
    try {
      const res = await fetch("/api/risk/settings");
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
          body: JSON.stringify(settings),
        }),
        momentumSettings ? fetch("/api/signal-intelligence/settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
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
          <CardDescription>Default position sizing for new accounts</CardDescription>
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
                <SelectItem value="fixed">Fixed Lot Size</SelectItem>
                <SelectItem value="percent_balance">% of Balance</SelectItem>
                <SelectItem value="percent_equity">% of Equity</SelectItem>
                <SelectItem value="risk_based">Risk-Based (% per trade)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Default Lot Size</Label>
              <Input
                type="number"
                step="0.01"
                value={settings.default_fixed_lot_size || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_fixed_lot_size: e.target.value ? parseFloat(e.target.value) : null
                })}
                placeholder="0.01"
              />
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

      <Button onClick={saveSettings} disabled={saving}>
        {saving ? "Saving..." : "Save Settings"}
      </Button>
    </div>
  );
}
