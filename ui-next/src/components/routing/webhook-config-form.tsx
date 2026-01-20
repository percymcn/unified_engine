'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
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
  WebhookConfig,
  WebhookConfigCreate,
  WebhookSource,
  SignalAction,
  RoutingRule,
} from '@/types/routing';
import { Account } from '@/types/account';
import { RoutingRuleBuilder } from './routing-rule-builder';
import { Plus } from 'lucide-react';

interface WebhookConfigFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: WebhookConfigCreate) => Promise<void>;
  accounts: Account[];
  config?: WebhookConfig; // If provided, form is in edit mode
}

const SOURCE_OPTIONS: { value: WebhookSource; label: string }[] = [
  { value: 'tradingview', label: 'TradingView' },
  { value: 'trailhacker', label: 'TrailHacker' },
  { value: 'custom', label: 'Custom' },
];

const ACTION_OPTIONS: { value: SignalAction; label: string }[] = [
  { value: 'buy', label: 'Buy' },
  { value: 'sell', label: 'Sell' },
  { value: 'close', label: 'Close' },
];

export function WebhookConfigForm({
  open,
  onClose,
  onSubmit,
  accounts,
  config,
}: WebhookConfigFormProps) {
  const isEdit = !!config;

  // Form state
  const [name, setName] = useState(config?.name || '');
  const [source, setSource] = useState<WebhookSource>(config?.source || 'tradingview');
  const [defaultAccountId, setDefaultAccountId] = useState<number | undefined>(
    config?.default_account_id
  );
  const [routingRules, setRoutingRules] = useState<RoutingRule[]>(
    config?.routing_rules || []
  );
  const [symbolFilter, setSymbolFilter] = useState<string>(
    config?.symbol_filter?.join(', ') || ''
  );
  const [actionFilter, setActionFilter] = useState<SignalAction[]>(
    config?.action_filter || []
  );
  const [isActive, setIsActive] = useState(config?.is_active ?? true);
  const [submitting, setSubmitting] = useState(false);

  // Reset form when config changes
  useEffect(() => {
    if (config) {
      setName(config.name);
      setSource(config.source);
      setDefaultAccountId(config.default_account_id);
      setRoutingRules(config.routing_rules);
      setSymbolFilter(config.symbol_filter?.join(', ') || '');
      setActionFilter(config.action_filter || []);
      setIsActive(config.is_active);
    }
  }, [config]);

  const handleAddRule = () => {
    const newRule: RoutingRule = {
      id: `rule-${Date.now()}`,
      condition: {
        field: 'symbol',
        operator: 'equals',
        value: '',
      },
      target_account_id: accounts[0]?.id || 0,
      priority: routingRules.length,
    };
    setRoutingRules([...routingRules, newRule]);
  };

  const handleUpdateRule = (index: number, updatedRule: RoutingRule) => {
    const updated = [...routingRules];
    updated[index] = updatedRule;
    setRoutingRules(updated);
  };

  const handleRemoveRule = (index: number) => {
    setRoutingRules(routingRules.filter((_, i) => i !== index));
  };

  const handleActionFilterChange = (action: SignalAction, checked: boolean) => {
    if (checked) {
      setActionFilter([...actionFilter, action]);
    } else {
      setActionFilter(actionFilter.filter((a) => a !== action));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const data: WebhookConfigCreate = {
        name,
        source,
        default_account_id: defaultAccountId,
        routing_rules: routingRules,
        symbol_filter: symbolFilter
          ? symbolFilter.split(',').map((s) => s.trim()).filter(Boolean)
          : undefined,
        action_filter: actionFilter.length > 0 ? actionFilter : undefined,
        is_active: isActive,
      };

      await onSubmit(data);
      onClose();
    } catch (error) {
      console.error('Failed to submit webhook config:', error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'Edit Webhook Configuration' : 'Add New Webhook Configuration'}
          </DialogTitle>
          <DialogDescription>
            Configure signal routing rules to automatically route incoming signals to specific accounts.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Configuration Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Scalping Strategy Router"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="source">Signal Source</Label>
              <Select value={source} onValueChange={(value) => setSource(value as WebhookSource)}>
                <SelectTrigger id="source">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SOURCE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="default-account">Default Account (optional)</Label>
              <Select
                value={defaultAccountId?.toString() || 'none'}
                onValueChange={(value) =>
                  setDefaultAccountId(value === 'none' ? undefined : parseInt(value))
                }
              >
                <SelectTrigger id="default-account">
                  <SelectValue placeholder="No default account" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No default account</SelectItem>
                  {accounts.map((account) => (
                    <SelectItem key={account.id} value={account.id.toString()}>
                      {account.account_id} ({account.broker})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Signals that don't match any rule will be sent to this account
              </p>
            </div>
          </div>

          {/* Filters */}
          <div className="space-y-4 pt-4 border-t border-border">
            <h3 className="text-sm font-semibold">Filters (optional)</h3>

            <div className="space-y-2">
              <Label htmlFor="symbol-filter">Symbol Filter</Label>
              <Input
                id="symbol-filter"
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value)}
                placeholder="EURUSD, GBPUSD, GOLD (comma-separated)"
              />
              <p className="text-xs text-muted-foreground">
                Only process signals for these symbols. Leave empty to accept all.
              </p>
            </div>

            <div className="space-y-2">
              <Label>Action Filter</Label>
              <div className="flex gap-4">
                {ACTION_OPTIONS.map((action) => (
                  <div key={action.value} className="flex items-center space-x-2">
                    <Checkbox
                      id={`action-${action.value}`}
                      checked={actionFilter.includes(action.value)}
                      onCheckedChange={(checked) =>
                        handleActionFilterChange(action.value, checked as boolean)
                      }
                    />
                    <Label
                      htmlFor={`action-${action.value}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {action.label}
                    </Label>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Only process signals with these actions. Leave empty to accept all.
              </p>
            </div>
          </div>

          {/* Routing Rules */}
          <div className="space-y-4 pt-4 border-t border-border">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Routing Rules</h3>
                <p className="text-xs text-muted-foreground">
                  Rules are evaluated in priority order (lowest first)
                </p>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={handleAddRule}>
                <Plus className="h-4 w-4 mr-2" />
                Add Rule
              </Button>
            </div>

            {routingRules.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No routing rules. Add a rule to route signals based on conditions.
              </div>
            ) : (
              <div className="space-y-3">
                {routingRules.map((rule, index) => (
                  <RoutingRuleBuilder
                    key={rule.id}
                    rule={rule}
                    accounts={accounts}
                    onChange={(updatedRule) => handleUpdateRule(index, updatedRule)}
                    onRemove={() => handleRemoveRule(index)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Active Status */}
          <div className="flex items-center space-x-2 pt-4 border-t border-border">
            <Checkbox
              id="is-active"
              checked={isActive}
              onCheckedChange={(checked) => setIsActive(checked as boolean)}
            />
            <Label htmlFor="is-active" className="text-sm font-normal cursor-pointer">
              Configuration is active
            </Label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Saving...' : isEdit ? 'Update Configuration' : 'Create Configuration'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
