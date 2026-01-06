import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Slider } from './ui/slider';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { TrendingDown, TrendingUp, Save } from 'lucide-react';

interface TradingConfigurationProps {
  broker: 'tradelocker' | 'topstep' | 'truforex';
}

export function TradingConfiguration({ broker }: TradingConfigurationProps) {
  const [config, setConfig] = useState({
    // Lot Size Configuration
    lotSizeMode: 'fixed', // 'fixed' | 'percentage'
    fixedLotSize: 0.01,
    percentageLotSize: 1.0,
    minLotSize: 0.01,
    maxLotSize: 100.0,
    
    // Stop Loss Configuration
    slMode: 'percentage', // 'percentage' | 'pips' | 'price'
    slPercentage: 2.0,
    slPips: 20,
    slPrice: 0,
    useTrailingSL: false,
    trailingSlDistance: 1.0,
    
    // Take Profit Configuration
    tpMode: 'percentage', // 'percentage' | 'pips' | 'price' | 'risk_reward'
    tpPercentage: 4.0,
    tpPips: 40,
    tpPrice: 0,
    riskRewardRatio: 2.0,
    
    // Advanced Settings
    usePartialTP: false,
    partialTpPercent: 50,
    partialTpLevel: 1.5
  });

  const updateConfig = (updates: Partial<typeof config>) => {
    setConfig({ ...config, ...updates });
  };

  const formatValue = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-white mb-1">Trading Configuration</h2>
        <p className="text-sm text-gray-400">Configure position sizing, stop loss, and take profit settings for {broker}</p>
      </div>

      {/* Lot Size Configuration */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Position Size (Lot Size)</CardTitle>
          <CardDescription className="text-gray-400">
            Configure how much to trade per signal
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Label className="text-gray-300 mb-2 block">Position Sizing Mode</Label>
            <Select
              value={config.lotSizeMode}
              onValueChange={(value) => updateConfig({ lotSizeMode: value })}
            >
              <SelectTrigger className="bg-[#002b36] border-gray-700 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#002b36] border-gray-700">
                <SelectItem value="fixed">Fixed Lot Size</SelectItem>
                <SelectItem value="percentage">Percentage of Account</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {config.lotSizeMode === 'fixed' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Fixed Lot Size</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="100"
                    value={config.fixedLotSize}
                    onChange={(e) => updateConfig({ fixedLotSize: parseFloat(e.target.value) || 0.01 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">lots</span>
                </div>
              </div>
              <Slider
                value={[config.fixedLotSize]}
                onValueChange={([value]) => updateConfig({ fixedLotSize: value })}
                min={0.01}
                max={10}
                step={0.01}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.01 lots</span>
                <span>10.00 lots</span>
              </div>
            </div>
          )}

          {config.lotSizeMode === 'percentage' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Account Risk Percentage</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="100"
                    value={config.percentageLotSize}
                    onChange={(e) => updateConfig({ percentageLotSize: parseFloat(e.target.value) || 0.01 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">%</span>
                </div>
              </div>
              <Slider
                value={[config.percentageLotSize]}
                onValueChange={([value]) => updateConfig({ percentageLotSize: value })}
                min={0.01}
                max={10}
                step={0.01}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.01%</span>
                <span>10.00%</span>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Lot size will be calculated based on {config.percentageLotSize.toFixed(2)}% of your account equity and stop loss distance
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stop Loss Configuration */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-red-400" />
            <CardTitle className="text-white">Stop Loss Configuration</CardTitle>
          </div>
          <CardDescription className="text-gray-400">
            Set automatic stop loss for risk management
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Label className="text-gray-300 mb-2 block">Stop Loss Mode</Label>
            <Select
              value={config.slMode}
              onValueChange={(value) => updateConfig({ slMode: value })}
            >
              <SelectTrigger className="bg-[#002b36] border-gray-700 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#002b36] border-gray-700">
                <SelectItem value="percentage">Percentage from Entry</SelectItem>
                <SelectItem value="pips">Fixed Pips/Points</SelectItem>
                <SelectItem value="price">Absolute Price</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {config.slMode === 'percentage' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Stop Loss Percentage</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="20"
                    value={config.slPercentage}
                    onChange={(e) => updateConfig({ slPercentage: parseFloat(e.target.value) || 0.01 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">%</span>
                </div>
              </div>
              <Slider
                value={[config.slPercentage]}
                onValueChange={([value]) => updateConfig({ slPercentage: value })}
                min={0.01}
                max={10}
                step={0.01}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.01%</span>
                <span>10.00%</span>
              </div>
              <div className="mt-3 p-3 bg-[#002b36] rounded border border-gray-700">
                <p className="text-xs text-gray-400">
                  Example: Entry at $100, SL at ${(100 - (100 * config.slPercentage / 100)).toFixed(2)} ({config.slPercentage.toFixed(2)}% below)
                </p>
              </div>
            </div>
          )}

          {config.slMode === 'pips' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Stop Loss Distance</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="500"
                    value={config.slPips}
                    onChange={(e) => updateConfig({ slPips: parseFloat(e.target.value) || 0.1 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">pips</span>
                </div>
              </div>
              <Slider
                value={[config.slPips]}
                onValueChange={([value]) => updateConfig({ slPips: value })}
                min={0.1}
                max={200}
                step={0.1}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.1 pips</span>
                <span>200 pips</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between p-3 bg-[#002b36] rounded border border-gray-700">
            <div>
              <Label className="text-gray-300">Enable Trailing Stop Loss</Label>
              <p className="text-xs text-gray-400 mt-1">Move SL as price moves in your favor</p>
            </div>
            <Switch
              checked={config.useTrailingSL}
              onCheckedChange={(checked) => updateConfig({ useTrailingSL: checked })}
            />
          </div>

          {config.useTrailingSL && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Trailing Distance</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="10"
                    value={config.trailingSlDistance}
                    onChange={(e) => updateConfig({ trailingSlDistance: parseFloat(e.target.value) || 0.01 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">%</span>
                </div>
              </div>
              <Slider
                value={[config.trailingSlDistance]}
                onValueChange={([value]) => updateConfig({ trailingSlDistance: value })}
                min={0.01}
                max={5}
                step={0.01}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.01%</span>
                <span>5.00%</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Take Profit Configuration */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[#00ffc2]" />
            <CardTitle className="text-white">Take Profit Configuration</CardTitle>
          </div>
          <CardDescription className="text-gray-400">
            Set automatic profit targets
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Label className="text-gray-300 mb-2 block">Take Profit Mode</Label>
            <Select
              value={config.tpMode}
              onValueChange={(value) => updateConfig({ tpMode: value })}
            >
              <SelectTrigger className="bg-[#002b36] border-gray-700 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#002b36] border-gray-700">
                <SelectItem value="percentage">Percentage from Entry</SelectItem>
                <SelectItem value="pips">Fixed Pips/Points</SelectItem>
                <SelectItem value="price">Absolute Price</SelectItem>
                <SelectItem value="risk_reward">Risk/Reward Ratio</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {config.tpMode === 'percentage' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Take Profit Percentage</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="50"
                    value={config.tpPercentage}
                    onChange={(e) => updateConfig({ tpPercentage: parseFloat(e.target.value) || 0.01 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">%</span>
                </div>
              </div>
              <Slider
                value={[config.tpPercentage]}
                onValueChange={([value]) => updateConfig({ tpPercentage: value })}
                min={0.01}
                max={20}
                step={0.01}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.01%</span>
                <span>20.00%</span>
              </div>
              <div className="mt-3 p-3 bg-[#002b36] rounded border border-gray-700">
                <p className="text-xs text-gray-400">
                  Example: Entry at $100, TP at ${(100 + (100 * config.tpPercentage / 100)).toFixed(2)} ({config.tpPercentage.toFixed(2)}% above)
                </p>
              </div>
            </div>
          )}

          {config.tpMode === 'pips' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Take Profit Distance</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="1000"
                    value={config.tpPips}
                    onChange={(e) => updateConfig({ tpPips: parseFloat(e.target.value) || 0.1 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">pips</span>
                </div>
              </div>
              <Slider
                value={[config.tpPips]}
                onValueChange={([value]) => updateConfig({ tpPips: value })}
                min={0.1}
                max={500}
                step={0.1}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.1 pips</span>
                <span>500 pips</span>
              </div>
            </div>
          )}

          {config.tpMode === 'risk_reward' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300">Risk/Reward Ratio</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="10"
                    value={config.riskRewardRatio}
                    onChange={(e) => updateConfig({ riskRewardRatio: parseFloat(e.target.value) || 0.01 })}
                    className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                  />
                  <span className="text-sm text-gray-400">R</span>
                </div>
              </div>
              <Slider
                value={[config.riskRewardRatio]}
                onValueChange={([value]) => updateConfig({ riskRewardRatio: value })}
                min={0.01}
                max={5}
                step={0.01}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.01:1</span>
                <span>5.00:1</span>
              </div>
              <div className="mt-3 p-3 bg-[#002b36] rounded border border-gray-700">
                <p className="text-xs text-gray-400">
                  TP will be placed {config.riskRewardRatio.toFixed(2)}x the distance of your stop loss
                </p>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between p-3 bg-[#002b36] rounded border border-gray-700">
            <div>
              <Label className="text-gray-300">Partial Take Profit</Label>
              <p className="text-xs text-gray-400 mt-1">Close portion of position at interim level</p>
            </div>
            <Switch
              checked={config.usePartialTP}
              onCheckedChange={(checked) => updateConfig({ usePartialTP: checked })}
            />
          </div>

          {config.usePartialTP && (
            <>
              <div>
                <div className="flex items-center justify-between mb-3">
                  <Label className="text-gray-300">Partial Close %</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      step="1"
                      min="1"
                      max="99"
                      value={config.partialTpPercent}
                      onChange={(e) => updateConfig({ partialTpPercent: parseInt(e.target.value) || 1 })}
                      className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                    />
                    <span className="text-sm text-gray-400">%</span>
                  </div>
                </div>
                <Slider
                  value={[config.partialTpPercent]}
                  onValueChange={([value]) => updateConfig({ partialTpPercent: value })}
                  min={1}
                  max={99}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>1%</span>
                  <span>99%</span>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <Label className="text-gray-300">Partial TP Level</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      step="0.01"
                      min="0.01"
                      max="10"
                      value={config.partialTpLevel}
                      onChange={(e) => updateConfig({ partialTpLevel: parseFloat(e.target.value) || 0.01 })}
                      className="w-24 bg-[#002b36] border-gray-700 text-white text-right"
                    />
                    <span className="text-sm text-gray-400">%</span>
                  </div>
                </div>
                <Slider
                  value={[config.partialTpLevel]}
                  onValueChange={([value]) => updateConfig({ partialTpLevel: value })}
                  min={0.01}
                  max={5}
                  step={0.01}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0.01%</span>
                  <span>5.00%</span>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Summary & Save */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Configuration Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-[#002b36] rounded">
              <p className="text-xs text-gray-400 mb-1">Position Size</p>
              <p className="text-white">
                {config.lotSizeMode === 'fixed' 
                  ? `${config.fixedLotSize.toFixed(2)} lots` 
                  : `${config.percentageLotSize.toFixed(2)}% of account`}
              </p>
            </div>
            <div className="p-3 bg-[#002b36] rounded">
              <p className="text-xs text-gray-400 mb-1">Stop Loss</p>
              <p className="text-red-400">
                {config.slMode === 'percentage' && `${config.slPercentage.toFixed(2)}%`}
                {config.slMode === 'pips' && `${config.slPips.toFixed(1)} pips`}
                {config.useTrailingSL && ` (Trailing: ${config.trailingSlDistance.toFixed(2)}%)`}
              </p>
            </div>
            <div className="p-3 bg-[#002b36] rounded">
              <p className="text-xs text-gray-400 mb-1">Take Profit</p>
              <p className="text-[#00ffc2]">
                {config.tpMode === 'percentage' && `${config.tpPercentage.toFixed(2)}%`}
                {config.tpMode === 'pips' && `${config.tpPips.toFixed(1)} pips`}
                {config.tpMode === 'risk_reward' && `${config.riskRewardRatio.toFixed(2)}R`}
              </p>
            </div>
            <div className="p-3 bg-[#002b36] rounded">
              <p className="text-xs text-gray-400 mb-1">Partial TP</p>
              <p className="text-white">
                {config.usePartialTP 
                  ? `${config.partialTpPercent}% at ${config.partialTpLevel.toFixed(2)}%`
                  : 'Disabled'}
              </p>
            </div>
          </div>

          <Button className="w-full bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad]">
            <Save className="w-4 h-4 mr-2" />
            Save Configuration
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
