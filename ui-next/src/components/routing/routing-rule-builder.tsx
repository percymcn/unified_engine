'use client';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  RoutingRule,
  RoutingConditionField,
  RoutingConditionOperator,
} from '@/types/routing';
import { Account } from '@/types/account';
import { X } from 'lucide-react';

interface RoutingRuleBuilderProps {
  rule: RoutingRule;
  accounts: Account[];
  onChange: (rule: RoutingRule) => void;
  onRemove: () => void;
}

const FIELD_LABELS: Record<RoutingConditionField, string> = {
  symbol: 'Symbol',
  action: 'Action',
  source: 'Source',
  strategy: 'Strategy',
};

const OPERATOR_LABELS: Record<RoutingConditionOperator, string> = {
  equals: 'Equals',
  contains: 'Contains',
  startsWith: 'Starts with',
  endsWith: 'Ends with',
};

export function RoutingRuleBuilder({
  rule,
  accounts,
  onChange,
  onRemove,
}: RoutingRuleBuilderProps) {
  const updateCondition = (
    updates: Partial<{
      field: RoutingConditionField;
      operator: RoutingConditionOperator;
      value: string;
    }>
  ) => {
    onChange({
      ...rule,
      condition: {
        ...rule.condition,
        ...updates,
      },
    });
  };

  return (
    <div className="flex items-end gap-3 p-4 border border-border rounded-lg bg-card">
      {/* Condition Field */}
      <div className="flex-1 space-y-2">
        <Label>Field</Label>
        <Select
          value={rule.condition.field}
          onValueChange={(value) =>
            updateCondition({ field: value as RoutingConditionField })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(FIELD_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Operator */}
      <div className="flex-1 space-y-2">
        <Label>Operator</Label>
        <Select
          value={rule.condition.operator}
          onValueChange={(value) =>
            updateCondition({ operator: value as RoutingConditionOperator })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(OPERATOR_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Value */}
      <div className="flex-1 space-y-2">
        <Label>Value</Label>
        <Input
          value={rule.condition.value}
          onChange={(e) => updateCondition({ value: e.target.value })}
          placeholder="e.g., EURUSD"
        />
      </div>

      {/* Target Account */}
      <div className="flex-1 space-y-2">
        <Label>Target Account</Label>
        <Select
          value={rule.target_account_id.toString()}
          onValueChange={(value) =>
            onChange({ ...rule, target_account_id: parseInt(value) })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {accounts.map((account) => (
              <SelectItem key={account.id} value={account.id.toString()}>
                {account.account_id} ({account.broker})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Priority */}
      <div className="w-24 space-y-2">
        <Label>Priority</Label>
        <Input
          type="number"
          value={rule.priority}
          onChange={(e) =>
            onChange({ ...rule, priority: parseInt(e.target.value) || 0 })
          }
          min="0"
        />
      </div>

      {/* Remove Button */}
      <Button
        type="button"
        variant="outline"
        size="icon"
        onClick={onRemove}
        className="flex-shrink-0"
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}
