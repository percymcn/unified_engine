"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Shield, AlertTriangle, DollarSign, TrendingDown } from "lucide-react";

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

export default function RiskSettingsPage() {
  const [settings, setSettings] = useState<GlobalRiskSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchSettings();
  }, []);

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
      const res = await fetch("/api/risk/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        toast({ title: "Settings saved", description: "Global risk settings updated successfully" });
      } else {
        toast({ title: "Error", description: "Failed to save settings", variant: "destructive" });
      }
    } finally {
      setSaving(false);
    }
  }

  if (!settings) {
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
              <Input
                type="number"
                step="0.1"
                value={settings.default_max_daily_loss_pct || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_max_daily_loss_pct: e.target.value ? parseFloat(e.target.value) : null
                })}
                placeholder="No limit"
              />
            </div>
            <div>
              <Label>Max Drawdown (%)</Label>
              <Input
                type="number"
                step="0.1"
                value={settings.default_max_drawdown_pct || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_max_drawdown_pct: e.target.value ? parseFloat(e.target.value) : null
                })}
                placeholder="No limit"
              />
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
              <Input
                type="number"
                step="0.1"
                value={settings.default_risk_percent_per_trade || ""}
                onChange={(e) => setSettings({
                  ...settings,
                  default_risk_percent_per_trade: e.target.value ? parseFloat(e.target.value) : null
                })}
                placeholder="1.0"
              />
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
