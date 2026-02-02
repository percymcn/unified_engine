'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TabsContent } from '@/components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Loader2, Trophy, Calendar, Target, TrendingDown, Info } from 'lucide-react';
import { AccountSettings, AccountGroup, PositionSizingMode, BrokerType, PropPhase, PROP_PROVIDERS } from '@/types/account';
import { getBrokerRiskProfile, formatBrokerValue, validateBrokerValue } from '@/lib/brokers/riskCapabilities';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface AccountSettingsFormProps {
  settings: AccountSettings;
  groups: AccountGroup[];
  broker: BrokerType;
  onSave: (updates: Partial<AccountSettings>) => Promise<void>;
  saving: boolean;
}

const POSITION_SIZING_OPTIONS: { value: PositionSizingMode; label: string; description: string }[] = [
  { value: 'fixed', label: 'Fixed Lot Size', description: 'Always use the same lot size for every trade' },
  { value: 'percent_balance', label: '% of Balance', description: 'Size trades based on account balance' },
  { value: 'percent_equity', label: '% of Equity', description: 'Size trades based on current equity' },
  { value: 'risk_based', label: 'Risk-Based', description: 'Size based on risk % and stop loss distance' },
];

export function AccountSettingsForm({
  settings,
  groups,
  broker,
  onSave,
  saving,
}: AccountSettingsFormProps) {
  // Get broker-specific risk capabilities
  const riskProfile = getBrokerRiskProfile(broker);
  // Position sizing state
  const [positionSizingMode, setPositionSizingMode] = useState<PositionSizingMode>(
    settings.positionSizing.mode
  );
  const [fixedLotSize, setFixedLotSize] = useState(settings.positionSizing.fixedLotSize.toString());
  const [percentOfBalance, setPercentOfBalance] = useState(
    settings.positionSizing.percentOfBalance.toString()
  );
  const [percentOfEquity, setPercentOfEquity] = useState(
    settings.positionSizing.percentOfEquity.toString()
  );
  const [riskPercentPerTrade, setRiskPercentPerTrade] = useState(
    settings.positionSizing.riskPercentPerTrade.toString()
  );

  // Risk limits state
  const [maxPositionSize, setMaxPositionSize] = useState(
    settings.riskLimits.maxPositionSize?.toString() || ''
  );
  const [maxDailyLoss, setMaxDailyLoss] = useState(
    settings.riskLimits.maxDailyLoss?.toString() || ''
  );
  const [maxDailyLossPct, setMaxDailyLossPct] = useState(
    settings.riskLimits.maxDailyLossPct?.toString() || ''
  );
  const [maxDrawdownPct, setMaxDrawdownPct] = useState(
    settings.riskLimits.maxDrawdownPct?.toString() || ''
  );
  const [maxOpenPositions, setMaxOpenPositions] = useState(
    settings.riskLimits.maxOpenPositions?.toString() || ''
  );
  const [maxDailyTrades, setMaxDailyTrades] = useState(
    settings.riskLimits.maxDailyTrades?.toString() || ''
  );
  const [tradeCooldownSeconds, setTradeCooldownSeconds] = useState(
    settings.riskLimits.tradeCooldownSeconds?.toString() || ''
  );
  
  // Stop loss and take profit (broker-aware defaults)
  const [defaultStopLoss, setDefaultStopLoss] = useState('');
  const [defaultTakeProfit, setDefaultTakeProfit] = useState('');
  // Unit types for SL/TP (pips, points, percent)
  const [slType, setSlType] = useState<'pips' | 'points' | 'percent' | 'price'>(
    settings.riskLimits.slType || riskProfile.stopLoss.mode
  );
  const [tpType, setTpType] = useState<'pips' | 'points' | 'percent' | 'price'>(
    settings.riskLimits.tpType || riskProfile.takeProfit.mode
  );

  // Routing state
  const [groupId, setGroupId] = useState<number | null>(settings.grouping.groupId);
  const [isSignalEnabled, setIsSignalEnabled] = useState(settings.routing.isSignalEnabled);
  const [signalPriority, setSignalPriority] = useState(settings.routing.signalPriority.toString());
  const [autoConfirm, setAutoConfirm] = useState(settings.routing.autoConfirm ?? true);

  // Prop rules state
  const [propEnabled, setPropEnabled] = useState(settings.propRules?.isEnabled || false);
  const [propProvider, setPropProvider] = useState(settings.propRules?.provider || '');
  const [propPhase, setPropPhase] = useState<PropPhase>(settings.propRules?.phase || 'none');
  const [propProfitTargetPct, setPropProfitTargetPct] = useState(
    settings.propRules?.profitTargetPct?.toString() || ''
  );
  const [propProfitTargetAmount, setPropProfitTargetAmount] = useState(
    settings.propRules?.profitTargetAmount?.toString() || ''
  );
  const [propMaxDailyLossPct, setPropMaxDailyLossPct] = useState(
    settings.propRules?.maxDailyLossPct?.toString() || ''
  );
  const [propMaxDailyLossAmount, setPropMaxDailyLossAmount] = useState(
    settings.propRules?.maxDailyLossAmount?.toString() || ''
  );
  const [propMaxDrawdownPct, setPropMaxDrawdownPct] = useState(
    settings.propRules?.maxDrawdownPct?.toString() || ''
  );
  const [propMaxDrawdownAmount, setPropMaxDrawdownAmount] = useState(
    settings.propRules?.maxDrawdownAmount?.toString() || ''
  );
  const [propTrailingDrawdown, setPropTrailingDrawdown] = useState(
    settings.propRules?.trailingDrawdown || false
  );
  const [propChallengeStartDate, setPropChallengeStartDate] = useState(
    settings.propRules?.challengeStartDate || ''
  );
  const [propChallengeEndDate, setPropChallengeEndDate] = useState(
    settings.propRules?.challengeEndDate || ''
  );

  // Reset form when settings change
  useEffect(() => {
    setPositionSizingMode(settings.positionSizing.mode);
    setFixedLotSize(settings.positionSizing.fixedLotSize.toString());
    setPercentOfBalance(settings.positionSizing.percentOfBalance.toString());
    setPercentOfEquity(settings.positionSizing.percentOfEquity.toString());
    setRiskPercentPerTrade(settings.positionSizing.riskPercentPerTrade.toString());
    setMaxPositionSize(settings.riskLimits.maxPositionSize?.toString() || '');
    setMaxDailyLoss(settings.riskLimits.maxDailyLoss?.toString() || '');
    setMaxDailyLossPct(settings.riskLimits.maxDailyLossPct?.toString() || '');
    setMaxDrawdownPct(settings.riskLimits.maxDrawdownPct?.toString() || '');
    setMaxOpenPositions(settings.riskLimits.maxOpenPositions?.toString() || '');
    setMaxDailyTrades(settings.riskLimits.maxDailyTrades?.toString() || '');
    setTradeCooldownSeconds(settings.riskLimits.tradeCooldownSeconds?.toString() || '');
    setDefaultStopLoss(settings.riskLimits.defaultStopLoss?.toString() || '');
    setDefaultTakeProfit(settings.riskLimits.defaultTakeProfit?.toString() || '');
    setSlType(settings.riskLimits.slType || riskProfile.stopLoss.mode);
    setTpType(settings.riskLimits.tpType || riskProfile.takeProfit.mode);
    setGroupId(settings.grouping.groupId);
    setIsSignalEnabled(settings.routing.isSignalEnabled);
    setSignalPriority(settings.routing.signalPriority.toString());
    // Prop rules
    setPropEnabled(settings.propRules?.isEnabled || false);
    setPropProvider(settings.propRules?.provider || '');
    setPropPhase(settings.propRules?.phase || 'none');
    setPropProfitTargetPct(settings.propRules?.profitTargetPct?.toString() || '');
    setPropProfitTargetAmount(settings.propRules?.profitTargetAmount?.toString() || '');
    setPropMaxDailyLossPct(settings.propRules?.maxDailyLossPct?.toString() || '');
    setPropMaxDailyLossAmount(settings.propRules?.maxDailyLossAmount?.toString() || '');
    setPropMaxDrawdownPct(settings.propRules?.maxDrawdownPct?.toString() || '');
    setPropMaxDrawdownAmount(settings.propRules?.maxDrawdownAmount?.toString() || '');
    setPropTrailingDrawdown(settings.propRules?.trailingDrawdown || false);
    setPropChallengeStartDate(settings.propRules?.challengeStartDate || '');
    setPropChallengeEndDate(settings.propRules?.challengeEndDate || '');
  }, [settings]);

  const handleSave = () => {
    const updates: Partial<AccountSettings> = {
      positionSizing: {
        mode: positionSizingMode,
        fixedLotSize: parseFloat(fixedLotSize) || 0.01,
        percentOfBalance: parseFloat(percentOfBalance) || 1,
        percentOfEquity: parseFloat(percentOfEquity) || 1,
        riskPercentPerTrade: parseFloat(riskPercentPerTrade) || 1,
      },
      riskLimits: {
        maxPositionSize: maxPositionSize ? parseFloat(maxPositionSize) : null,
        maxDailyLoss: maxDailyLoss ? parseFloat(maxDailyLoss) : null,
        maxDailyLossPct: maxDailyLossPct ? parseFloat(maxDailyLossPct) : null,
        maxDrawdownPct: maxDrawdownPct ? parseFloat(maxDrawdownPct) : null,
        maxOpenPositions: maxOpenPositions ? parseInt(maxOpenPositions) : null,
        maxDailyTrades: maxDailyTrades ? parseInt(maxDailyTrades) : null,
        tradeCooldownSeconds: tradeCooldownSeconds ? parseInt(tradeCooldownSeconds) : null,
        // SL/TP stored in broker-specific units (pips/points/percent)
        // Backend converts to absolute prices using signal's entry price
        defaultStopLoss: defaultStopLoss ? parseFloat(defaultStopLoss) : null,
        defaultTakeProfit: defaultTakeProfit ? parseFloat(defaultTakeProfit) : null,
        slType: slType,
        tpType: tpType,
      },
      grouping: {
        groupId: groupId,
        groupName: groups.find((g) => g.id === groupId)?.name || null,
        groupColor: groups.find((g) => g.id === groupId)?.color || null,
      },
      routing: {
        isSignalEnabled: isSignalEnabled,
        signalPriority: parseInt(signalPriority) || 0,
        autoConfirm: autoConfirm,
      },
      propRules: {
        isEnabled: propEnabled,
        provider: propProvider || null,
        phase: propPhase,
        profitTargetPct: propProfitTargetPct ? parseFloat(propProfitTargetPct) : null,
        profitTargetAmount: propProfitTargetAmount ? parseFloat(propProfitTargetAmount) : null,
        maxDailyLossPct: propMaxDailyLossPct ? parseFloat(propMaxDailyLossPct) : null,
        maxDailyLossAmount: propMaxDailyLossAmount ? parseFloat(propMaxDailyLossAmount) : null,
        maxDrawdownPct: propMaxDrawdownPct ? parseFloat(propMaxDrawdownPct) : null,
        maxDrawdownAmount: propMaxDrawdownAmount ? parseFloat(propMaxDrawdownAmount) : null,
        trailingDrawdown: propTrailingDrawdown,
        challengeStartDate: propChallengeStartDate || null,
        challengeEndDate: propChallengeEndDate || null,
      },
    };

    onSave(updates);
  };

  return (
    <>
      {/* Position Sizing Tab */}
      <TabsContent value="position-sizing">
        <Card>
          <CardHeader>
            <CardTitle>Position Sizing Mode</CardTitle>
            <CardDescription>
              Choose how trade sizes are calculated for this account
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <RadioGroup
              value={positionSizingMode}
              onValueChange={(value) => setPositionSizingMode(value as PositionSizingMode)}
              className="space-y-4"
            >
              {POSITION_SIZING_OPTIONS.map((option) => (
                <div key={option.value} className="flex items-start space-x-3">
                  <RadioGroupItem value={option.value} id={option.value} className="mt-1" />
                  <div className="grid gap-1">
                    <Label htmlFor={option.value} className="font-medium cursor-pointer">
                      {option.label}
                    </Label>
                    <p className="text-sm text-muted-foreground">{option.description}</p>
                  </div>
                </div>
              ))}
            </RadioGroup>

            {/* Mode-specific inputs */}
            <div className="space-y-4 pt-4 border-t border-border">
              {positionSizingMode === 'fixed' && (
                <div className="space-y-2">
                  <Label htmlFor="fixedLotSize">{riskProfile.positionSize.label}</Label>
                  <Input
                    id="fixedLotSize"
                    type="number"
                    step={riskProfile.positionSize.step}
                    min={riskProfile.positionSize.min}
                    max={riskProfile.positionSize.max}
                    value={fixedLotSize}
                    onChange={(e) => {
                      const value = parseFloat(e.target.value) || 0;
                      const validation = validateBrokerValue(
                        value,
                        riskProfile.positionSize.min,
                        riskProfile.positionSize.max,
                        riskProfile.positionSize.step
                      );
                      if (validation.valid) {
                        const formatted = formatBrokerValue(value, riskProfile.positionSize.step);
                        setFixedLotSize(formatted.toString());
                      } else if (validation.corrected !== undefined) {
                        setFixedLotSize(validation.corrected.toString());
                      }
                    }}
                    placeholder={riskProfile.positionSize.min.toString()}
                  />
                  <p className="text-xs text-muted-foreground">
                    {riskProfile.positionSize.helperText}
                  </p>
                </div>
              )}

              {positionSizingMode === 'percent_balance' && (
                <div className="space-y-2">
                  <Label htmlFor="percentOfBalance">Percent of Balance</Label>
                  <Input
                    id="percentOfBalance"
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="100"
                    value={percentOfBalance}
                    onChange={(e) => setPercentOfBalance(e.target.value)}
                    placeholder="1"
                  />
                  <p className="text-xs text-muted-foreground">
                    Trade size as percentage of account balance (0.1 - 100%)
                  </p>
                </div>
              )}

              {positionSizingMode === 'percent_equity' && (
                <div className="space-y-2">
                  <Label htmlFor="percentOfEquity">Percent of Equity</Label>
                  <Input
                    id="percentOfEquity"
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="100"
                    value={percentOfEquity}
                    onChange={(e) => setPercentOfEquity(e.target.value)}
                    placeholder="1"
                  />
                  <p className="text-xs text-muted-foreground">
                    Trade size as percentage of current equity (0.1 - 100%)
                  </p>
                </div>
              )}

              {positionSizingMode === 'risk_based' && (
                <div className="space-y-2">
                  <Label htmlFor="riskPercentPerTrade">Risk Per Trade (%)</Label>
                  <Input
                    id="riskPercentPerTrade"
                    type="number"
                    step={riskProfile.riskPercent.step}
                    min={riskProfile.riskPercent.min}
                    max={riskProfile.riskPercent.max}
                    value={riskPercentPerTrade}
                    onChange={(e) => {
                      const value = parseFloat(e.target.value) || 0;
                      const validation = validateBrokerValue(
                        value,
                        riskProfile.riskPercent.min,
                        riskProfile.riskPercent.max,
                        riskProfile.riskPercent.step
                      );
                      if (validation.valid) {
                        const formatted = formatBrokerValue(value, riskProfile.riskPercent.precision);
                        setRiskPercentPerTrade(formatted.toString());
                      } else if (validation.corrected !== undefined) {
                        setRiskPercentPerTrade(validation.corrected.toString());
                      }
                    }}
                    placeholder="1"
                  />
                  <p className="text-xs text-muted-foreground">
                    Maximum risk per trade based on stop loss ({riskProfile.riskPercent.min} - {riskProfile.riskPercent.max}%)
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end mt-6">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </Button>
        </div>
      </TabsContent>

      {/* Risk Limits Tab */}
      <TabsContent value="risk-limits">
        <Card>
          <CardHeader>
            <CardTitle>Risk Limits</CardTitle>
            <CardDescription>
              Set trading limits and protections to manage risk. Leave empty for no limit.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Stop Loss and Take Profit Section */}
              <div className="pb-4 border-b border-border">
                <h3 className="text-sm font-semibold mb-4">Default Stop Loss & Take Profit</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="defaultStopLoss">{riskProfile.stopLoss.label}</Label>
                    <div className="space-y-2">
                      <Slider
                        value={defaultStopLoss ? parseFloat(defaultStopLoss) : riskProfile.stopLoss.min}
                        onValueChange={(value) => {
                          if (value === riskProfile.stopLoss.min) {
                            setDefaultStopLoss('');
                          } else {
                            const formatted = formatBrokerValue(value, riskProfile.stopLoss.precision);
                            setDefaultStopLoss(formatted.toString());
                          }
                        }}
                        min={riskProfile.stopLoss.min}
                        max={Math.min(riskProfile.stopLoss.max, 100)} // Cap slider at 100 for UI
                        step={riskProfile.stopLoss.step}
                      />
                      <div className="flex items-center gap-2">
                        <Input
                          id="defaultStopLoss"
                          type="number"
                          step={slType === 'percent' ? 0.001 : riskProfile.stopLoss.step}
                          min={slType === 'percent' ? 0.001 : riskProfile.stopLoss.min}
                          max={slType === 'percent' ? 50 : riskProfile.stopLoss.max}
                          value={defaultStopLoss}
                          onChange={(e) => {
                            const value = parseFloat(e.target.value) || 0;
                            if (value === 0) {
                              setDefaultStopLoss('');
                              return;
                            }
                            setDefaultStopLoss(value.toString());
                          }}
                          placeholder="Enter value"
                          className="flex-1"
                        />
                        <Select value={slType} onValueChange={(v) => setSlType(v as 'pips' | 'points' | 'percent' | 'price')}>
                          <SelectTrigger className="w-24">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="pips">Pips</SelectItem>
                            <SelectItem value="points">Points</SelectItem>
                            <SelectItem value="percent">%</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {slType === 'percent'
                        ? 'Stop loss as percentage of entry price'
                        : slType === 'pips'
                        ? '1 pip = 0.0001 for most forex pairs'
                        : '1 point = minimum price tick for futures'}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="defaultTakeProfit">{riskProfile.takeProfit.label}</Label>
                    <div className="space-y-2">
                      <Slider
                        value={defaultTakeProfit ? parseFloat(defaultTakeProfit) : riskProfile.takeProfit.min}
                        onValueChange={(value) => {
                          if (value === riskProfile.takeProfit.min) {
                            setDefaultTakeProfit('');
                          } else {
                            const formatted = formatBrokerValue(value, riskProfile.takeProfit.precision);
                            setDefaultTakeProfit(formatted.toString());
                          }
                        }}
                        min={riskProfile.takeProfit.min}
                        max={Math.min(riskProfile.takeProfit.max, 200)} // Cap slider at 200 for UI
                        step={riskProfile.takeProfit.step}
                      />
                      <div className="flex items-center gap-2">
                        <Input
                          id="defaultTakeProfit"
                          type="number"
                          step={tpType === 'percent' ? 0.001 : riskProfile.takeProfit.step}
                          min={tpType === 'percent' ? 0.001 : riskProfile.takeProfit.min}
                          max={tpType === 'percent' ? 100 : riskProfile.takeProfit.max}
                          value={defaultTakeProfit}
                          onChange={(e) => {
                            const value = parseFloat(e.target.value) || 0;
                            if (value === 0) {
                              setDefaultTakeProfit('');
                              return;
                            }
                            setDefaultTakeProfit(value.toString());
                          }}
                          placeholder="Enter value"
                          className="flex-1"
                        />
                        <Select value={tpType} onValueChange={(v) => setTpType(v as 'pips' | 'points' | 'percent' | 'price')}>
                          <SelectTrigger className="w-24">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="pips">Pips</SelectItem>
                            <SelectItem value="points">Points</SelectItem>
                            <SelectItem value="percent">%</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {tpType === 'percent'
                        ? 'Take profit as percentage of entry price'
                        : tpType === 'pips'
                        ? '1 pip = 0.0001 for most forex pairs'
                        : '1 point = minimum price tick for futures'}
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Other Risk Limits */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="maxPositionSize">{riskProfile.positionSize.label} (Max)</Label>
                <Input
                  id="maxPositionSize"
                  type="number"
                  step={riskProfile.positionSize.step}
                  min={riskProfile.positionSize.min}
                  max={riskProfile.positionSize.max}
                  value={maxPositionSize}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value) || 0;
                    if (value === 0) {
                      setMaxPositionSize('');
                      return;
                    }
                    const validation = validateBrokerValue(
                      value,
                      riskProfile.positionSize.min,
                      riskProfile.positionSize.max,
                      riskProfile.positionSize.step
                    );
                    if (validation.valid) {
                      const formatted = formatBrokerValue(value, riskProfile.positionSize.step);
                      setMaxPositionSize(formatted.toString());
                    } else if (validation.corrected !== undefined) {
                      setMaxPositionSize(validation.corrected.toString());
                    }
                  }}
                  placeholder="No limit"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum allowed {riskProfile.positionSize.unit} per trade. Leave empty for no limit.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxOpenPositions">Max Open Positions</Label>
                <Input
                  id="maxOpenPositions"
                  type="number"
                  min="1"
                  max="100"
                  value={maxOpenPositions}
                  onChange={(e) => setMaxOpenPositions(e.target.value)}
                  placeholder="No limit"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxDailyLoss">Max Daily Loss ($)</Label>
                <Input
                  id="maxDailyLoss"
                  type="number"
                  min="0"
                  value={maxDailyLoss}
                  onChange={(e) => setMaxDailyLoss(e.target.value)}
                  placeholder="No limit"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxDailyLossPct">Max Daily Loss (%)</Label>
                <Input
                  id="maxDailyLossPct"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={maxDailyLossPct}
                  onChange={(e) => setMaxDailyLossPct(e.target.value)}
                  placeholder="No limit"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxDrawdownPct">Max Drawdown (%)</Label>
                <Input
                  id="maxDrawdownPct"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={maxDrawdownPct}
                  onChange={(e) => setMaxDrawdownPct(e.target.value)}
                  placeholder="No limit"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxDailyTrades">Max Daily Trades</Label>
                <Input
                  id="maxDailyTrades"
                  type="number"
                  min="1"
                  max="1000"
                  value={maxDailyTrades}
                  onChange={(e) => setMaxDailyTrades(e.target.value)}
                  placeholder="No limit"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="tradeCooldownSeconds">Trade Cooldown (seconds)</Label>
                <Input
                  id="tradeCooldownSeconds"
                  type="number"
                  min="0"
                  max="3600"
                  value={tradeCooldownSeconds}
                  onChange={(e) => setTradeCooldownSeconds(e.target.value)}
                  placeholder="No cooldown"
                />
                <p className="text-xs text-muted-foreground">
                  Minimum time between trades (0 - 3600 seconds)
                </p>
              </div>
            </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end mt-6">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </Button>
        </div>
      </TabsContent>

      {/* Signal Routing Tab */}
      <TabsContent value="routing">
        <Card>
          <CardHeader>
            <CardTitle>Signal Routing</CardTitle>
            <CardDescription>
              Control how signals are routed to this account
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Enable/Disable Signals */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="signal-enabled">Enable Signals</Label>
                <p className="text-sm text-muted-foreground">
                  Allow this account to receive trading signals
                </p>
              </div>
              <Switch
                id="signal-enabled"
                checked={isSignalEnabled}
                onCheckedChange={setIsSignalEnabled}
              />
            </div>

            {/* Auto-Confirm Trades */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="auto-confirm">Auto-Execute Trades</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically execute trades without manual confirmation. When off, signals that trigger
                  risk warnings (e.g., momentum flip) will require manual approval.
                </p>
              </div>
              <Switch
                id="auto-confirm"
                checked={autoConfirm}
                onCheckedChange={setAutoConfirm}
                disabled={!isSignalEnabled}
              />
            </div>

            {/* Signal Priority */}
            <div className="space-y-2">
              <Label htmlFor="signalPriority">Signal Priority</Label>
              <Input
                id="signalPriority"
                type="number"
                min="0"
                max="100"
                value={signalPriority}
                onChange={(e) => setSignalPriority(e.target.value)}
                disabled={!isSignalEnabled}
              />
              <p className="text-xs text-muted-foreground">
                Higher priority accounts execute signals first (0 - 100)
              </p>
            </div>

            {/* Account Group */}
            <div className="space-y-2">
              <Label htmlFor="group">Account Group</Label>
              <Select
                value={groupId?.toString() || 'none'}
                onValueChange={(value) =>
                  setGroupId(value === 'none' ? null : parseInt(value))
                }
              >
                <SelectTrigger id="group">
                  <SelectValue placeholder="No group" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No Group</SelectItem>
                  {groups.map((group) => (
                    <SelectItem key={group.id} value={group.id.toString()}>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: group.color }}
                        />
                        {group.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Organize accounts into groups for easier management
              </p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end mt-6">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </Button>
        </div>
      </TabsContent>

      {/* Prop Rules Tab */}
      <TabsContent value="prop-rules">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5" />
              Prop Firm Rules
            </CardTitle>
            <CardDescription>
              Configure prop firm challenge rules and limits. The system will help you stay compliant with your prop firm&apos;s requirements.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Enable Prop Rules */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="prop-enabled" className="font-medium">Enable Prop Rules</Label>
                <p className="text-sm text-muted-foreground">
                  Track and enforce prop firm compliance for this account
                </p>
              </div>
              <Switch
                id="prop-enabled"
                checked={propEnabled}
                onCheckedChange={setPropEnabled}
              />
            </div>

            {propEnabled && (
              <>
                {/* Provider and Phase */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="propProvider">Prop Firm Provider</Label>
                    <Select
                      value={propProvider}
                      onValueChange={setPropProvider}
                    >
                      <SelectTrigger id="propProvider">
                        <SelectValue placeholder="Select provider" />
                      </SelectTrigger>
                      <SelectContent>
                        {PROP_PROVIDERS.map((provider) => (
                          <SelectItem key={provider} value={provider}>
                            {provider}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="propPhase">Challenge Phase</Label>
                    <Select
                      value={propPhase}
                      onValueChange={(value) => setPropPhase(value as PropPhase)}
                    >
                      <SelectTrigger id="propPhase">
                        <SelectValue placeholder="Select phase" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Not Set</SelectItem>
                        <SelectItem value="evaluation_1">Evaluation Phase 1</SelectItem>
                        <SelectItem value="evaluation_2">Evaluation Phase 2</SelectItem>
                        <SelectItem value="funded">Funded Account</SelectItem>
                        <SelectItem value="payout">Payout Eligible</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Challenge Dates */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="challengeStartDate" className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      Challenge Start Date
                    </Label>
                    <Input
                      id="challengeStartDate"
                      type="date"
                      value={propChallengeStartDate}
                      onChange={(e) => setPropChallengeStartDate(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="challengeEndDate" className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      Challenge End Date
                    </Label>
                    <Input
                      id="challengeEndDate"
                      type="date"
                      value={propChallengeEndDate}
                      onChange={(e) => setPropChallengeEndDate(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Leave empty for unlimited time challenges
                    </p>
                  </div>
                </div>

                {/* Profit Target */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Profit Target
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="profitTargetPct">Profit Target (%)</Label>
                      <Input
                        id="profitTargetPct"
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={propProfitTargetPct}
                        onChange={(e) => setPropProfitTargetPct(e.target.value)}
                        placeholder="e.g., 10"
                      />
                      <p className="text-xs text-muted-foreground">
                        Target profit as percentage of starting balance
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="profitTargetAmount">Profit Target ($)</Label>
                      <Input
                        id="profitTargetAmount"
                        type="number"
                        step="1"
                        min="0"
                        value={propProfitTargetAmount}
                        onChange={(e) => setPropProfitTargetAmount(e.target.value)}
                        placeholder="e.g., 10000"
                      />
                      <p className="text-xs text-muted-foreground">
                        Target profit in account currency
                      </p>
                    </div>
                  </div>
                </div>

                {/* Daily Loss Limit */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" />
                    Daily Loss Limit
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="propDailyLossPct">Daily Loss Limit (%)</Label>
                      <Input
                        id="propDailyLossPct"
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={propMaxDailyLossPct}
                        onChange={(e) => setPropMaxDailyLossPct(e.target.value)}
                        placeholder="e.g., 5"
                      />
                      <p className="text-xs text-muted-foreground">
                        Maximum daily loss as percentage of starting balance
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="propDailyLossAmount">Daily Loss Limit ($)</Label>
                      <Input
                        id="propDailyLossAmount"
                        type="number"
                        step="1"
                        min="0"
                        value={propMaxDailyLossAmount}
                        onChange={(e) => setPropMaxDailyLossAmount(e.target.value)}
                        placeholder="e.g., 5000"
                      />
                    </div>
                  </div>
                </div>

                {/* Maximum Drawdown */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" />
                    Maximum Drawdown
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="propDrawdownPct">Max Drawdown (%)</Label>
                      <Input
                        id="propDrawdownPct"
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={propMaxDrawdownPct}
                        onChange={(e) => setPropMaxDrawdownPct(e.target.value)}
                        placeholder="e.g., 10"
                      />
                      <p className="text-xs text-muted-foreground">
                        Maximum overall drawdown as percentage
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="propDrawdownAmount">Max Drawdown ($)</Label>
                      <Input
                        id="propDrawdownAmount"
                        type="number"
                        step="1"
                        min="0"
                        value={propMaxDrawdownAmount}
                        onChange={(e) => setPropMaxDrawdownAmount(e.target.value)}
                        placeholder="e.g., 10000"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/50">
                    <div className="space-y-0.5">
                      <Label htmlFor="trailingDrawdown" className="font-medium">Trailing Drawdown</Label>
                      <p className="text-sm text-muted-foreground">
                        Drawdown limit follows high water mark (equity high)
                      </p>
                    </div>
                    <Switch
                      id="trailingDrawdown"
                      checked={propTrailingDrawdown}
                      onCheckedChange={setPropTrailingDrawdown}
                    />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end mt-6">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </Button>
        </div>
      </TabsContent>
    </>
  );
}
