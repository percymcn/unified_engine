'use client';

import { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, Save, X, Loader2, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useToast } from '@/hooks/use-toast';
import {
  SymbolSetting,
  SymbolSettingInput,
  RiskUnitType,
  getSymbolSettings,
  saveSymbolSetting,
  deleteSymbolSetting,
} from '@/lib/api/accounts';

interface SymbolSettingsPanelProps {
  accountId: number;
  broker: string;
}

const COMMON_SYMBOLS = [
  'XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'ETHUSD',
  'NAS100', 'US30', 'SPX500', 'GER40', 'UK100',
  'USOIL', 'UKOIL', 'XAGUSD',
];

const UNIT_TYPES: { value: RiskUnitType; label: string; description: string }[] = [
  { value: 'pips', label: 'Pips', description: 'Standard forex pip measurement' },
  { value: 'points', label: 'Points', description: 'Index/crypto point measurement' },
  { value: 'percent', label: 'Percent', description: 'Percentage of entry price' },
  { value: 'price', label: 'Price', description: 'Absolute price difference' },
];

export function SymbolSettingsPanel({ accountId, broker }: SymbolSettingsPanelProps) {
  const { toast } = useToast();
  const [settings, setSettings] = useState<SymbolSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSymbol, setEditingSymbol] = useState<SymbolSetting | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<SymbolSettingInput>({
    symbol: '',
    defaultStopLoss: null,
    defaultTakeProfit: null,
    slType: 'pips',
    tpType: 'pips',
    positionSizeOverride: null,
    maxPositions: null,
    notes: '',
  });

  useEffect(() => {
    loadSettings();
  }, [accountId]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await getSymbolSettings(accountId);
      setSettings(data);
    } catch (err) {
      console.error('Failed to load symbol settings:', err);
      toast({
        title: 'Error',
        description: 'Failed to load symbol settings',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAdd = () => {
    setEditingSymbol(null);
    setFormData({
      symbol: '',
      defaultStopLoss: null,
      defaultTakeProfit: null,
      slType: 'pips',
      tpType: 'pips',
      positionSizeOverride: null,
      maxPositions: null,
      notes: '',
    });
    setDialogOpen(true);
  };

  const handleOpenEdit = (setting: SymbolSetting) => {
    setEditingSymbol(setting);
    setFormData({
      symbol: setting.symbol,
      defaultStopLoss: setting.defaultStopLoss,
      defaultTakeProfit: setting.defaultTakeProfit,
      slType: setting.slType,
      tpType: setting.tpType,
      positionSizeOverride: setting.positionSizeOverride,
      maxPositions: setting.maxPositions,
      notes: setting.notes || '',
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!formData.symbol.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Symbol is required',
        variant: 'destructive',
      });
      return;
    }

    try {
      setSaving(true);
      await saveSymbolSetting(accountId, formData);
      toast({
        title: 'Success',
        description: `Symbol settings for ${formData.symbol.toUpperCase()} saved`,
      });
      setDialogOpen(false);
      loadSettings();
    } catch (err) {
      console.error('Failed to save symbol setting:', err);
      toast({
        title: 'Error',
        description: 'Failed to save symbol settings',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (symbol: string) => {
    try {
      setSaving(true);
      await deleteSymbolSetting(accountId, symbol);
      toast({
        title: 'Deleted',
        description: `Symbol settings for ${symbol} removed`,
      });
      setDeleteConfirm(null);
      loadSettings();
    } catch (err) {
      console.error('Failed to delete symbol setting:', err);
      toast({
        title: 'Error',
        description: 'Failed to delete symbol settings',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  Symbol-Specific SL/TP
                  <Tooltip>
                    <TooltipTrigger>
                      <HelpCircle className="h-4 w-4 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>Configure stop loss and take profit for specific symbols. These settings override your account defaults when trading that symbol.</p>
                    </TooltipContent>
                  </Tooltip>
                </CardTitle>
                <CardDescription>
                  Override default SL/TP for specific symbols. Account defaults apply when no symbol override exists.
                </CardDescription>
              </div>
              <Button onClick={handleOpenAdd} size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Symbol
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {settings.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No symbol-specific settings configured.</p>
                <p className="text-sm mt-1">Account default SL/TP will be used for all symbols.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {settings.map((setting) => (
                  <div
                    key={setting.id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-semibold text-lg">
                          {setting.symbol}
                        </span>
                        {setting.notes && (
                          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                            {setting.notes}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                        {setting.defaultStopLoss !== null && (
                          <span>
                            SL: {setting.defaultStopLoss} {setting.slType}
                          </span>
                        )}
                        {setting.defaultTakeProfit !== null && (
                          <span>
                            TP: {setting.defaultTakeProfit} {setting.tpType}
                          </span>
                        )}
                        {setting.positionSizeOverride !== null && (
                          <span>
                            Lot: {setting.positionSizeOverride}
                          </span>
                        )}
                        {setting.maxPositions !== null && (
                          <span>
                            Max: {setting.maxPositions}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleOpenEdit(setting)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeleteConfirm(setting.symbol)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Add/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>
                {editingSymbol ? `Edit ${editingSymbol.symbol}` : 'Add Symbol Settings'}
              </DialogTitle>
              <DialogDescription>
                Configure SL/TP and position settings for a specific symbol.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* Symbol */}
              <div className="space-y-2">
                <Label htmlFor="symbol">Symbol</Label>
                {editingSymbol ? (
                  <Input
                    id="symbol"
                    value={formData.symbol}
                    disabled
                    className="font-mono"
                  />
                ) : (
                  <div className="space-y-2">
                    <Input
                      id="symbol"
                      value={formData.symbol}
                      onChange={(e) =>
                        setFormData({ ...formData, symbol: e.target.value.toUpperCase() })
                      }
                      placeholder="e.g., XAUUSD, EURUSD, NAS100"
                      className="font-mono"
                    />
                    <div className="flex flex-wrap gap-1">
                      {COMMON_SYMBOLS.filter(s => !settings.some(ss => ss.symbol === s)).slice(0, 8).map((sym) => (
                        <Button
                          key={sym}
                          variant="outline"
                          size="sm"
                          className="h-6 text-xs"
                          onClick={() => setFormData({ ...formData, symbol: sym })}
                        >
                          {sym}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Stop Loss */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="sl">Stop Loss</Label>
                  <Input
                    id="sl"
                    type="number"
                    step="0.01"
                    value={formData.defaultStopLoss ?? ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        defaultStopLoss: e.target.value ? parseFloat(e.target.value) : null,
                      })
                    }
                    placeholder="Optional"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="slType">SL Unit</Label>
                  <Select
                    value={formData.slType}
                    onValueChange={(v) =>
                      setFormData({ ...formData, slType: v as RiskUnitType })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {UNIT_TYPES.map((ut) => (
                        <SelectItem key={ut.value} value={ut.value}>
                          {ut.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Take Profit */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tp">Take Profit</Label>
                  <Input
                    id="tp"
                    type="number"
                    step="0.01"
                    value={formData.defaultTakeProfit ?? ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        defaultTakeProfit: e.target.value ? parseFloat(e.target.value) : null,
                      })
                    }
                    placeholder="Optional"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tpType">TP Unit</Label>
                  <Select
                    value={formData.tpType}
                    onValueChange={(v) =>
                      setFormData({ ...formData, tpType: v as RiskUnitType })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {UNIT_TYPES.map((ut) => (
                        <SelectItem key={ut.value} value={ut.value}>
                          {ut.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Position Override */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="lotSize">Position Size Override</Label>
                  <Input
                    id="lotSize"
                    type="number"
                    step="0.01"
                    value={formData.positionSizeOverride ?? ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        positionSizeOverride: e.target.value ? parseFloat(e.target.value) : null,
                      })
                    }
                    placeholder="Optional (lots)"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maxPos">Max Positions</Label>
                  <Input
                    id="maxPos"
                    type="number"
                    step="1"
                    value={formData.maxPositions ?? ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        maxPositions: e.target.value ? parseInt(e.target.value) : null,
                      })
                    }
                    placeholder="Optional"
                  />
                </div>
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Input
                  id="notes"
                  value={formData.notes || ''}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Optional description"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Delete Symbol Settings</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete settings for {deleteConfirm}? Account defaults will be used instead.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
                disabled={saving}
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
}
