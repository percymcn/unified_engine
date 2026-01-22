'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RoutingStrategy, RoutingRule } from '@/types/routing';
import { Account, BROKER_DISPLAY_NAMES } from '@/types/account';
import { RoutingRuleBuilder } from '@/components/routing/routing-rule-builder';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

interface RoutingConfigProps {
  strategy: RoutingStrategy;
  defaultAccountId?: number;
  specificAccountIds: number[];
  routingRules: RoutingRule[];
  accounts: Account[];
  onStrategyChange: (strategy: RoutingStrategy) => void;
  onDefaultAccountChange: (accountId: number | undefined) => void;
  onSpecificAccountsChange: (accountIds: number[]) => void;
  onRoutingRulesChange: (rules: RoutingRule[]) => void;
}

const STRATEGY_OPTIONS: { value: RoutingStrategy; label: string; description: string }[] = [
  {
    value: 'all_accounts',
    label: 'All Accounts',
    description: 'Send signals to all signal-enabled accounts',
  },
  {
    value: 'specific_accounts',
    label: 'Specific Accounts',
    description: 'Send signals only to selected accounts',
  },
  {
    value: 'rules_based',
    label: 'Rules-Based',
    description: 'Route signals based on conditions (symbol, action, etc.)',
  },
  {
    value: 'default_only',
    label: 'Default Account Only',
    description: 'Send signals only to the default account',
  },
];

export function RoutingConfig({
  strategy,
  defaultAccountId,
  specificAccountIds,
  routingRules,
  accounts,
  onStrategyChange,
  onDefaultAccountChange,
  onSpecificAccountsChange,
  onRoutingRulesChange,
}: RoutingConfigProps) {
  const handleAccountToggle = (accountId: number, checked: boolean) => {
    if (checked) {
      onSpecificAccountsChange([...specificAccountIds, accountId]);
    } else {
      onSpecificAccountsChange(specificAccountIds.filter((id) => id !== accountId));
    }
  };

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
    onRoutingRulesChange([...routingRules, newRule]);
  };

  const handleUpdateRule = (index: number, updatedRule: RoutingRule) => {
    const updated = [...routingRules];
    updated[index] = updatedRule;
    onRoutingRulesChange(updated);
  };

  const handleRemoveRule = (index: number) => {
    onRoutingRulesChange(routingRules.filter((_, i) => i !== index));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Signal Routing</CardTitle>
        <CardDescription>
          Choose how signals from this webhook are routed to your accounts
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Strategy Selection */}
        <RadioGroup
          value={strategy}
          onValueChange={(value) => onStrategyChange(value as RoutingStrategy)}
          className="space-y-3"
        >
          {STRATEGY_OPTIONS.map((option) => (
            <div key={option.value} className="flex items-start space-x-3">
              <RadioGroupItem value={option.value} id={option.value} className="mt-1" />
              <div className="grid gap-0.5">
                <Label htmlFor={option.value} className="font-medium cursor-pointer">
                  {option.label}
                </Label>
                <p className="text-sm text-muted-foreground">{option.description}</p>
              </div>
            </div>
          ))}
        </RadioGroup>

        {/* Strategy-specific configuration */}
        {strategy === 'specific_accounts' && (
          <div className="space-y-3 pt-4 border-t border-border">
            <Label>Select Accounts</Label>
            {accounts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No accounts available. Create accounts first.
              </p>
            ) : (
              <div className="space-y-2">
                {accounts.map((account) => (
                  <div key={account.id} className="flex items-center space-x-3">
                    <Checkbox
                      id={`specific-${account.id}`}
                      checked={specificAccountIds.includes(account.id)}
                      onCheckedChange={(checked) =>
                        handleAccountToggle(account.id, checked as boolean)
                      }
                    />
                    <Label
                      htmlFor={`specific-${account.id}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {BROKER_DISPLAY_NAMES[account.broker as keyof typeof BROKER_DISPLAY_NAMES]} -{' '}
                      {account.account_id}
                    </Label>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {strategy === 'rules_based' && (
          <div className="space-y-4 pt-4 border-t border-border">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm font-semibold">Routing Rules</Label>
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
              <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
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

            {/* Fallback account for rules-based */}
            <div className="pt-4 border-t border-border">
              <Label htmlFor="fallback-account">Fallback Account (if no rules match)</Label>
              <Select
                value={defaultAccountId?.toString() || 'none'}
                onValueChange={(value) =>
                  onDefaultAccountChange(value === 'none' ? undefined : parseInt(value))
                }
              >
                <SelectTrigger id="fallback-account" className="mt-2">
                  <SelectValue placeholder="No fallback (signal will fail)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No fallback</SelectItem>
                  {accounts.map((account) => (
                    <SelectItem key={account.id} value={account.id.toString()}>
                      {BROKER_DISPLAY_NAMES[account.broker as keyof typeof BROKER_DISPLAY_NAMES]} -{' '}
                      {account.account_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {(strategy === 'default_only' || strategy === 'all_accounts') && (
          <div className="pt-4 border-t border-border">
            <Label htmlFor="default-account">Default Account</Label>
            <Select
              value={defaultAccountId?.toString() || 'none'}
              onValueChange={(value) =>
                onDefaultAccountChange(value === 'none' ? undefined : parseInt(value))
              }
            >
              <SelectTrigger id="default-account" className="mt-2">
                <SelectValue placeholder="Select default account" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No default account</SelectItem>
                {accounts.map((account) => (
                  <SelectItem key={account.id} value={account.id.toString()}>
                    {BROKER_DISPLAY_NAMES[account.broker as keyof typeof BROKER_DISPLAY_NAMES]} -{' '}
                    {account.account_id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              {strategy === 'all_accounts'
                ? 'Primary account for logging and fallback purposes'
                : 'All signals will be sent to this account only'}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
