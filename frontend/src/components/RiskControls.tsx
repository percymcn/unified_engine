import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Badge } from './ui/badge';
import { Slider } from './ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Shield, AlertTriangle, Save, RotateCcw } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';

interface RiskControlsProps {
  broker: 'tradelocker' | 'topstep' | 'truforex';
}

export function RiskControls({ broker }: RiskControlsProps) {
  const [riskProfile, setRiskProfile] = useState({
    enabled: true,
    riskMode: 'risk_pct',
    maxDailyLoss: 500,
    maxDailyLossPct: 2.0,
    maxTradesPerDay: 10,
    maxOpenTrades: 5,
    maxConcurrentPositions: 3,
    maxRiskPerTrade: 100,
    maxRiskPerTradePct: 1.0,
    leverageCap: 10,
    allowedInstruments: [] as string[],
    deniedInstruments: [] as string[],
    tradingHoursEnabled: false,
    tradingHoursStart: '09:30',
    tradingHoursEnd: '16:00',
    tradingHoursTimezone: 'America/New_York',
    newsLockoutEnabled: false,
    newsLockoutMinutes: 5
  });

  const [hasChanges, setHasChanges] = useState(false);

  const handleSave = () => {
    // Mock save - in real app, call backend
    console.log('Saving risk profile:', riskProfile);
    setHasChanges(false);
  };

  const handleReset = () => {
    // Mock reset to defaults
    setHasChanges(false);
  };

  const updateProfile = (updates: Partial<typeof riskProfile>) => {
    setRiskProfile({ ...riskProfile, ...updates });
    setHasChanges(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white mb-1">Risk Management</h2>
          <p className="text-sm text-gray-400">Configure risk controls for {broker}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 mr-4">
            <span className="text-sm text-gray-400">Risk Controls</span>
            <Switch
              checked={riskProfile.enabled}
              onCheckedChange={(checked) => updateProfile({ enabled: checked })}
            />
            <Badge
              variant="outline"
              className={
                riskProfile.enabled
                  ? 'border-[#00ffc2] text-[#00ffc2]'
                  : 'border-gray-500 text-gray-500'
              }
            >
              {riskProfile.enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
          {hasChanges && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReset}
                className="border-gray-700 text-white"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                className="bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad]"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </Button>
            </>
          )}
        </div>
      </div>

      {riskProfile.enabled && (
        <Alert className="bg-yellow-950 border-yellow-800">
          <Shield className="w-4 h-4 text-yellow-400" />
          <AlertDescription className="text-yellow-200">
            Risk controls are active. All trades will be validated before execution.
          </AlertDescription>
        </Alert>
      )}

      {/* Daily Limits */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Daily Limits</CardTitle>
          <CardDescription className="text-gray-400">
            Maximum exposure per trading day
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="maxDailyLoss" className="text-gray-300">Max Daily Loss ($)</Label>
              <Input
                id="maxDailyLoss"
                type="number"
                value={riskProfile.maxDailyLoss}
                onChange={(e) => updateProfile({ maxDailyLoss: parseFloat(e.target.value) })}
                className="bg-[#002b36] border-gray-700 text-white mt-1"
              />
              <p className="text-xs text-gray-400 mt-1">Stop trading if daily loss exceeds this amount</p>
            </div>

            <div>
              <Label htmlFor="maxDailyLossPct" className="text-gray-300">Max Daily Loss (%)</Label>
              <Input
                id="maxDailyLossPct"
                type="number"
                step="0.1"
                value={riskProfile.maxDailyLossPct}
                onChange={(e) => updateProfile({ maxDailyLossPct: parseFloat(e.target.value) })}
                className="bg-[#002b36] border-gray-700 text-white mt-1"
              />
              <p className="text-xs text-gray-400 mt-1">As percentage of account equity</p>
            </div>

            <div>
              <Label htmlFor="maxTradesPerDay" className="text-gray-300">Max Trades Per Day</Label>
              <Input
                id="maxTradesPerDay"
                type="number"
                value={riskProfile.maxTradesPerDay}
                onChange={(e) => updateProfile({ maxTradesPerDay: parseInt(e.target.value) })}
                className="bg-[#002b36] border-gray-700 text-white mt-1"
              />
              <p className="text-xs text-gray-400 mt-1">Maximum number of trade executions per day</p>
            </div>

            <div>
              <Label htmlFor="maxConcurrent" className="text-gray-300">Max Concurrent Positions</Label>
              <Input
                id="maxConcurrent"
                type="number"
                value={riskProfile.maxConcurrentPositions}
                onChange={(e) => updateProfile({ maxConcurrentPositions: parseInt(e.target.value) })}
                className="bg-[#002b36] border-gray-700 text-white mt-1"
              />
              <p className="text-xs text-gray-400 mt-1">Maximum open positions at one time</p>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <Label htmlFor="maxOpenTrades" className="text-gray-300">Maximum Open Trades</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="maxOpenTrades"
                  type="number"
                  min="1"
                  max="50"
                  value={riskProfile.maxOpenTrades}
                  onChange={(e) => updateProfile({ maxOpenTrades: parseInt(e.target.value) || 1 })}
                  className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                />
                <span className="text-sm text-gray-400">trades</span>
              </div>
            </div>
            <Slider
              value={[riskProfile.maxOpenTrades]}
              onValueChange={([value]) => updateProfile({ maxOpenTrades: value })}
              min={1}
              max={50}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>1 trade</span>
              <span>50 trades</span>
            </div>
            <div className="mt-3 p-3 bg-[#002b36] rounded border border-gray-700">
              <p className="text-xs text-[#00ffc2] mb-1">Active Protection</p>
              <p className="text-xs text-gray-400">
                Once you reach {riskProfile.maxOpenTrades} open {riskProfile.maxOpenTrades === 1 ? 'trade' : 'trades'}, 
                new orders will be blocked until a position is closed. This prevents overexposure and helps manage risk.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-Trade Limits */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Per-Trade Limits</CardTitle>
          <CardDescription className="text-gray-400">
            Risk parameters for individual trades
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="riskMode" className="text-gray-300">Default Risk Mode</Label>
            <Select
              value={riskProfile.riskMode}
              onValueChange={(value) => updateProfile({ riskMode: value })}
            >
              <SelectTrigger className="bg-[#002b36] border-gray-700 text-white mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#002b36] border-gray-700">
                <SelectItem value="fixed_qty">Fixed Quantity</SelectItem>
                <SelectItem value="risk_usd">Risk in Dollars</SelectItem>
                <SelectItem value="risk_pct">Risk Percentage</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-gray-400 mt-1">Default position sizing method if not specified in alert</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="maxRiskPerTrade" className="text-gray-300">Max Risk Per Trade ($)</Label>
              <Input
                id="maxRiskPerTrade"
                type="number"
                value={riskProfile.maxRiskPerTrade}
                onChange={(e) => updateProfile({ maxRiskPerTrade: parseFloat(e.target.value) })}
                className="bg-[#002b36] border-gray-700 text-white mt-1"
              />
            </div>

            <div>
              <Label htmlFor="maxRiskPerTradePct" className="text-gray-300">Max Risk Per Trade (%)</Label>
              <Input
                id="maxRiskPerTradePct"
                type="number"
                step="0.1"
                value={riskProfile.maxRiskPerTradePct}
                onChange={(e) => updateProfile({ maxRiskPerTradePct: parseFloat(e.target.value) })}
                className="bg-[#002b36] border-gray-700 text-white mt-1"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="leverageCap" className="text-gray-300">Maximum Leverage</Label>
            <Input
              id="leverageCap"
              type="number"
              value={riskProfile.leverageCap}
              onChange={(e) => updateProfile({ leverageCap: parseFloat(e.target.value) })}
              className="bg-[#002b36] border-gray-700 text-white mt-1"
            />
            <p className="text-xs text-gray-400 mt-1">Cap effective leverage (e.g., 10 = 10:1 max)</p>
          </div>
        </CardContent>
      </Card>

      {/* Instrument Filters */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Instrument Filters</CardTitle>
          <CardDescription className="text-gray-400">
            Control which instruments can be traded
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="allowedInstruments" className="text-gray-300">Allowed Instruments (comma-separated)</Label>
            <Input
              id="allowedInstruments"
              placeholder="ES, NQ, RTY, YM (leave empty to allow all)"
              value={riskProfile.allowedInstruments.join(', ')}
              onChange={(e) => updateProfile({
                allowedInstruments: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
              })}
              className="bg-[#002b36] border-gray-700 text-white mt-1"
            />
            <p className="text-xs text-gray-400 mt-1">If specified, only these symbols will be tradeable</p>
          </div>

          <div>
            <Label htmlFor="deniedInstruments" className="text-gray-300">Denied Instruments (comma-separated)</Label>
            <Input
              id="deniedInstruments"
              placeholder="BTC, ETH (leave empty for none)"
              value={riskProfile.deniedInstruments.join(', ')}
              onChange={(e) => updateProfile({
                deniedInstruments: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
              })}
              className="bg-[#002b36] border-gray-700 text-white mt-1"
            />
            <p className="text-xs text-gray-400 mt-1">These symbols will be blocked from trading</p>
          </div>
        </CardContent>
      </Card>

      {/* Trading Hours */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">Trading Hours</CardTitle>
              <CardDescription className="text-gray-400">
                Restrict trading to specific time windows
              </CardDescription>
            </div>
            <Switch
              checked={riskProfile.tradingHoursEnabled}
              onCheckedChange={(checked) => updateProfile({ tradingHoursEnabled: checked })}
            />
          </div>
        </CardHeader>
        {riskProfile.tradingHoursEnabled && (
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="hoursStart" className="text-gray-300">Start Time</Label>
                <Input
                  id="hoursStart"
                  type="time"
                  value={riskProfile.tradingHoursStart}
                  onChange={(e) => updateProfile({ tradingHoursStart: e.target.value })}
                  className="bg-[#002b36] border-gray-700 text-white mt-1"
                />
              </div>

              <div>
                <Label htmlFor="hoursEnd" className="text-gray-300">End Time</Label>
                <Input
                  id="hoursEnd"
                  type="time"
                  value={riskProfile.tradingHoursEnd}
                  onChange={(e) => updateProfile({ tradingHoursEnd: e.target.value })}
                  className="bg-[#002b36] border-gray-700 text-white mt-1"
                />
              </div>

              <div>
                <Label htmlFor="timezone" className="text-gray-300">Timezone</Label>
                <Select
                  value={riskProfile.tradingHoursTimezone}
                  onValueChange={(value) => updateProfile({ tradingHoursTimezone: value })}
                >
                  <SelectTrigger className="bg-[#002b36] border-gray-700 text-white mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#002b36] border-gray-700">
                    <SelectItem value="America/New_York">Eastern (ET)</SelectItem>
                    <SelectItem value="America/Chicago">Central (CT)</SelectItem>
                    <SelectItem value="America/Denver">Mountain (MT)</SelectItem>
                    <SelectItem value="America/Los_Angeles">Pacific (PT)</SelectItem>
                    <SelectItem value="Europe/London">London</SelectItem>
                    <SelectItem value="UTC">UTC</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* News Lockout */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">News Lockout</CardTitle>
              <CardDescription className="text-gray-400">
                Pause trading around high-impact news events
              </CardDescription>
            </div>
            <Switch
              checked={riskProfile.newsLockoutEnabled}
              onCheckedChange={(checked) => updateProfile({ newsLockoutEnabled: checked })}
            />
          </div>
        </CardHeader>
        {riskProfile.newsLockoutEnabled && (
          <CardContent>
            <div>
              <Label htmlFor="newsMinutes" className="text-gray-300">Lockout Duration (minutes)</Label>
              <Input
                id="newsMinutes"
                type="number"
                value={riskProfile.newsLockoutMinutes}
                onChange={(e) => updateProfile({ newsLockoutMinutes: parseInt(e.target.value) })}
                className="bg-[#002b36] border-gray-700 text-white mt-1"
              />
              <p className="text-xs text-gray-400 mt-1">
                Block trading X minutes before and after news events (requires economic calendar integration)
              </p>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Risk Summary */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Current Risk Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 bg-[#002b36] rounded-lg">
              <p className="text-xs text-gray-400 mb-1">Daily Loss Used</p>
              <div className="flex items-baseline gap-2">
                <span className="text-white">$125.50</span>
                <span className="text-xs text-gray-400">/ ${riskProfile.maxDailyLoss}</span>
              </div>
              <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-[#00ffc2]" style={{ width: '25%' }} />
              </div>
            </div>

            <div className="p-3 bg-[#002b36] rounded-lg">
              <p className="text-xs text-gray-400 mb-1">Trades Today</p>
              <div className="flex items-baseline gap-2">
                <span className="text-white">6</span>
                <span className="text-xs text-gray-400">/ {riskProfile.maxTradesPerDay}</span>
              </div>
              <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-blue-400" style={{ width: '60%' }} />
              </div>
            </div>

            <div className="p-3 bg-[#002b36] rounded-lg">
              <p className="text-xs text-gray-400 mb-1">Open Positions</p>
              <div className="flex items-baseline gap-2">
                <span className="text-white">2</span>
                <span className="text-xs text-gray-400">/ {riskProfile.maxConcurrentPositions}</span>
              </div>
              <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-purple-400" style={{ width: '66%' }} />
              </div>
            </div>

            <div className="p-3 bg-[#002b36] rounded-lg">
              <p className="text-xs text-gray-400 mb-1">Total Open Trades</p>
              <div className="flex items-baseline gap-2">
                <span className="text-white">3</span>
                <span className="text-xs text-gray-400">/ {riskProfile.maxOpenTrades}</span>
              </div>
              <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-[#00ffc2]" style={{ width: `${(3 / riskProfile.maxOpenTrades) * 100}%` }} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
