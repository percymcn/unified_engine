'use client';

import { useState, useEffect } from 'react';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, XCircle } from 'lucide-react';
import { SymbolAlias, CreateSymbolAliasRequest, UpdateSymbolAliasRequest } from '@/types/symbol-alias';
import { BROKER_DISPLAY_NAMES, BrokerType } from '@/types/account';
import { createSymbolAlias, updateSymbolAlias } from '@/lib/api/symbol-aliases';

interface SymbolAliasFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  alias?: SymbolAlias; // If provided, form is in edit mode
  connectedBrokers: string[]; // List of broker types user has accounts for
}

export function SymbolAliasForm({
  open,
  onClose,
  onSuccess,
  alias,
  connectedBrokers,
}: SymbolAliasFormProps) {
  const isEdit = !!alias;

  // Form state
  const [brokerType, setBrokerType] = useState(alias?.brokerType || '');
  const [sourceSymbol, setSourceSymbol] = useState(alias?.sourceSymbol || '');
  const [targetSymbol, setTargetSymbol] = useState(alias?.targetSymbol || '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens/closes or alias changes
  useEffect(() => {
    if (open) {
      if (alias) {
        setBrokerType(alias.brokerType);
        setSourceSymbol(alias.sourceSymbol);
        setTargetSymbol(alias.targetSymbol);
      } else {
        setBrokerType(connectedBrokers[0] || '');
        setSourceSymbol('');
        setTargetSymbol('');
      }
      setError(null);
    }
  }, [open, alias, connectedBrokers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (isEdit) {
        // Update existing alias
        const data: UpdateSymbolAliasRequest = {
          targetSymbol: targetSymbol.trim(),
        };
        await updateSymbolAlias(alias.id, data);
      } else {
        // Create new alias
        const data: CreateSymbolAliasRequest = {
          brokerType: brokerType,
          sourceSymbol: sourceSymbol.trim().toUpperCase(),
          targetSymbol: targetSymbol.trim(),
        };
        await createSymbolAlias(data);
      }

      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to save symbol alias:', err);
      setError(err instanceof Error ? err.message : 'Failed to save symbol mapping');
    } finally {
      setSubmitting(false);
    }
  };

  const isValid = brokerType && sourceSymbol.trim() && targetSymbol.trim();

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'Edit Symbol Mapping' : 'Add Symbol Mapping'}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update the broker symbol for this mapping.'
              : 'Create a mapping from a TradingView symbol to your broker\'s format.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Broker Selection */}
          <div className="space-y-2">
            <Label htmlFor="broker">Broker</Label>
            <Select
              value={brokerType}
              onValueChange={setBrokerType}
              disabled={isEdit}
            >
              <SelectTrigger id="broker">
                <SelectValue placeholder="Select broker" />
              </SelectTrigger>
              <SelectContent>
                {connectedBrokers.map((broker) => (
                  <SelectItem key={broker} value={broker}>
                    {BROKER_DISPLAY_NAMES[broker as BrokerType] || broker}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {!isEdit && connectedBrokers.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Connect a broker account first to add symbol mappings.
              </p>
            )}
          </div>

          {/* TradingView Symbol */}
          <div className="space-y-2">
            <Label htmlFor="source-symbol">TradingView Symbol</Label>
            <Input
              id="source-symbol"
              value={sourceSymbol}
              onChange={(e) => setSourceSymbol(e.target.value.toUpperCase())}
              placeholder="e.g., US30"
              disabled={isEdit}
              required
            />
            <p className="text-xs text-muted-foreground">
              The symbol you use in TradingView alerts
            </p>
          </div>

          {/* Broker Symbol */}
          <div className="space-y-2">
            <Label htmlFor="target-symbol">Broker Symbol</Label>
            <Input
              id="target-symbol"
              value={targetSymbol}
              onChange={(e) => setTargetSymbol(e.target.value)}
              placeholder="e.g., US30.pro"
              required
            />
            <p className="text-xs text-muted-foreground">
              The symbol your broker uses (case-sensitive)
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription className="ml-2">{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !isValid}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : isEdit ? (
                'Update Mapping'
              ) : (
                'Add Mapping'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
