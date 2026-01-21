'use client';

import { useState } from 'react';
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
import {
  Account,
  AccountCreate,
  BrokerType,
  AccountType,
  BROKER_DISPLAY_NAMES,
  ACCOUNT_TYPE_DISPLAY_NAMES,
  BROKER_CREDENTIAL_CONFIG,
} from '@/types/account';
import { TradovateOAuthButton } from './tradovate-oauth-button';

interface AccountFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: AccountCreate) => Promise<void>;
  account?: Account; // If provided, form is in edit mode
}

export function AccountForm({
  open,
  onClose,
  onSubmit,
  account,
}: AccountFormProps) {
  const isEdit = !!account;

  // Form state
  const [broker, setBroker] = useState<BrokerType>(
    account?.broker || 'tradelocker'
  );
  const [accountType, setAccountType] = useState<AccountType>(
    account?.account_type || 'live'
  );
  const [accountId, setAccountId] = useState(account?.account_id || '');
  const [currency, setCurrency] = useState(account?.currency || 'USD');
  const [leverage, setLeverage] = useState(account?.leverage?.toString() || '100');
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  // Get broker-specific credential fields
  const credentialConfig = BROKER_CREDENTIAL_CONFIG[broker];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const data: AccountCreate = {
        account_id: accountId,
        broker,
        account_type: accountType,
        currency,
        leverage: parseInt(leverage),
        ...credentials,
      };

      await onSubmit(data);
      onClose();
    } catch (error) {
      console.error('Failed to submit account:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCredentialChange = (name: string, value: string) => {
    setCredentials((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'Edit Account' : 'Add New Account'}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update account settings. Credentials are only required if changing them.'
              : 'Connect a new broker account. Your credentials are encrypted and stored securely.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Broker Selection */}
          <div className="space-y-2">
            <Label htmlFor="broker">Broker</Label>
            <Select
              value={broker}
              onValueChange={(value) => setBroker(value as BrokerType)}
              disabled={isEdit}
            >
              <SelectTrigger id="broker">
                <SelectValue placeholder="Select broker" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(BROKER_DISPLAY_NAMES).map(([key, name]) => (
                  <SelectItem key={key} value={key}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Account Type */}
          <div className="space-y-2">
            <Label htmlFor="account-type">Account Type</Label>
            <Select
              value={accountType}
              onValueChange={(value) => setAccountType(value as AccountType)}
            >
              <SelectTrigger id="account-type">
                <SelectValue placeholder="Select account type" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(ACCOUNT_TYPE_DISPLAY_NAMES).map(
                  ([key, name]) => (
                    <SelectItem key={key} value={key}>
                      {name}
                    </SelectItem>
                  )
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Account ID */}
          <div className="space-y-2">
            <Label htmlFor="account-id">Account ID</Label>
            <Input
              id="account-id"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder="Enter account identifier"
              required
              disabled={isEdit}
            />
          </div>

          {/* Currency */}
          <div className="space-y-2">
            <Label htmlFor="currency">Currency</Label>
            <Input
              id="currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              placeholder="USD, EUR, GBP, etc."
              maxLength={3}
            />
          </div>

          {/* Leverage */}
          <div className="space-y-2">
            <Label htmlFor="leverage">Leverage</Label>
            <Input
              id="leverage"
              type="number"
              value={leverage}
              onChange={(e) => setLeverage(e.target.value)}
              placeholder="100"
              min="1"
              max="1000"
            />
          </div>

          {/* Broker-Specific Credentials */}
          <div className="space-y-4 pt-4 border-t border-border">
            {broker === 'tradovate' && !isEdit ? (
              <>
                {/* OAuth option for Tradovate */}
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2">Connect via OAuth</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    Securely connect your Tradovate account using OAuth.
                    You will be redirected to Tradovate to authorize access.
                  </p>
                  <TradovateOAuthButton />
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground">
                      Or use credentials
                    </span>
                  </div>
                </div>

                {/* Fallback credential fields */}
                <div className="space-y-4 opacity-75">
                  <div>
                    <Label className="text-sm font-semibold">Credentials</Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      Alternative: Enter credentials manually
                    </p>
                  </div>
                  {credentialConfig.fields.map((field) => (
                    <div key={field.name} className="space-y-2">
                      <Label htmlFor={field.name}>{field.label}</Label>
                      <Input
                        id={field.name}
                        name={field.name}
                        type={field.type}
                        value={credentials[field.name] || ''}
                        onChange={(e) =>
                          handleCredentialChange(field.name, e.target.value)
                        }
                        placeholder={field.placeholder}
                        required={false}
                      />
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <>
                {/* Standard credential fields for other brokers */}
                <div>
                  <Label className="text-sm font-semibold">
                    {isEdit ? 'Update Credentials (optional)' : 'Credentials'}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-1">
                    {isEdit
                      ? 'Leave blank to keep existing credentials'
                      : 'Required to connect to broker API'}
                  </p>
                </div>

                {credentialConfig.fields.map((field) => (
                  <div key={field.name} className="space-y-2">
                    <Label htmlFor={field.name}>{field.label}</Label>
                    <Input
                      id={field.name}
                      name={field.name}
                      type={field.type}
                      value={credentials[field.name] || ''}
                      onChange={(e) =>
                        handleCredentialChange(field.name, e.target.value)
                      }
                      placeholder={field.placeholder}
                      required={!isEdit && field.required}
                    />
                  </div>
                ))}
              </>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting
                ? 'Saving...'
                : isEdit
                ? 'Update Account'
                : 'Add Account'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
