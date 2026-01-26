'use client';

import { useState, useMemo } from 'react';
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
import { CheckCircle2, XCircle, Loader2, Wifi } from 'lucide-react';
import {
  Account,
  AccountCreate,
  BrokerType,
  AccountType,
  BROKER_DISPLAY_NAMES,
  ACCOUNT_TYPE_DISPLAY_NAMES,
} from '@/types/account';
import {
  getBrokerCredentialSchema,
  mapCredentialsToBackend,
  type CredentialField,
} from '@/lib/brokers/credentialSchemas';
import { TradovateOAuthButton } from './tradovate-oauth-button';
import { testConnection, TestConnectionResult, discoverAccounts, DiscoveredAccount } from '@/lib/api/accounts';
import { Checkbox } from '@/components/ui/checkbox';

/**
 * Credential field input component
 * Handles different field types (text, password, select) with proper labels
 */
function CredentialFieldInput({
  field,
  value,
  onChange,
  required,
  broker,
}: {
  field: CredentialField;
  value: string;
  onChange: (value: string) => void;
  required: boolean;
  broker: BrokerType;
}) {
  // Special label handling for TradeLocker username field
  const displayLabel =
    field.name === 'username' && broker === 'tradelocker'
      ? 'Email'
      : field.label;

  if (field.type === 'select' && field.options) {
    return (
      <div className="space-y-2">
        <Label htmlFor={field.name}>{displayLabel}</Label>
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger id={field.name}>
            <SelectValue placeholder={field.description || `Select ${displayLabel}`} />
          </SelectTrigger>
          <SelectContent>
            {field.options.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {field.description && (
          <p className="text-xs text-muted-foreground">{field.description}</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={field.name}>{displayLabel}</Label>
      <Input
        id={field.name}
        name={field.name}
        type={field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.description || field.label}
        required={required}
      />
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  );
}

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
  const [currency, setCurrency] = useState(account?.currency || 'USD');
  const [leverage, setLeverage] = useState(account?.leverage?.toString() || '100');
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [discoveredAccounts, setDiscoveredAccounts] = useState<DiscoveredAccount[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<Set<string>>(new Set());
  const [defaultAccountId, setDefaultAccountId] = useState<string>('');
  const [discovering, setDiscovering] = useState(false);
  const [manualAccountId, setManualAccountId] = useState<string>('');
  const [showManualInput, setShowManualInput] = useState(false);

  // Get broker-specific credential schema
  const credentialSchema = getBrokerCredentialSchema(broker);
  const isBrokerSupported = credentialSchema !== null;
  
  const allFields = useMemo(() => {
    if (!credentialSchema) return [];
    return [...credentialSchema.requiredFields, ...credentialSchema.optionalFields];
  }, [credentialSchema]);

  // Check if all required credentials are filled
  const hasRequiredCredentials = useMemo(() => {
    if (!credentialSchema) return false;
    return credentialSchema.requiredFields.every((field) => {
      const value = credentials[field.name];
      return value && value.trim().length > 0;
    });
  }, [credentialSchema, credentials]);

  // Handle test connection
  const handleTestConnection = async () => {
    if (!hasRequiredCredentials) return;

    setTesting(true);
    setTestResult(null);

    try {
      // Map UI credentials to backend format
      const backendCredentials = mapCredentialsToBackend(broker, credentials);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Test connection - credential keys:', Object.keys(backendCredentials));
      }
      
      // Convert to Record<string, string> for testConnection API
      const stringCredentials: Record<string, string> = {};
      for (const [key, value] of Object.entries(backendCredentials)) {
        stringCredentials[key] = String(value);
      }
      
      const result = await testConnection(broker, stringCredentials);
      setTestResult(result);
      
      // If connection successful, discover accounts
      if (result.success) {
        setDiscovering(true);
        try {
          const discoverResult = await discoverAccounts(broker, stringCredentials);
          setDiscoveredAccounts(discoverResult.accounts || []);
          
          // Auto-select accounts based on count
          if (discoverResult.accounts && discoverResult.accounts.length > 0) {
            if (discoverResult.accounts.length === 1) {
              // Exactly one account - auto-select it
              const acc = discoverResult.accounts[0];
              const accId = acc.broker_account_id || acc.id || '';
              setSelectedAccountIds(new Set([accId]));
              setDefaultAccountId(accId);
            } else if (discoverResult.accounts.length <= 5) {
              // Few accounts (2-5) - auto-select all
              const allIds = new Set(discoverResult.accounts.map(acc => acc.broker_account_id || acc.id || '').filter(Boolean));
              setSelectedAccountIds(allIds);
              if (allIds.size > 0) {
                setDefaultAccountId(Array.from(allIds)[0]);
              }
            } else {
              // Many accounts (6+) - don't auto-select, let user choose
              // Just set first active account as default for convenience
              const activeAccounts = discoverResult.accounts.filter(acc => acc.status === 'active');
              if (activeAccounts.length > 0) {
                const firstActiveId = activeAccounts[0].broker_account_id || activeAccounts[0].id || '';
                setSelectedAccountIds(new Set([firstActiveId]));
                setDefaultAccountId(firstActiveId);
              }
            }
          }
          // Show manual input if no accounts discovered
          if (!discoverResult.accounts || discoverResult.accounts.length === 0) {
            setShowManualInput(true);
          } else {
            setShowManualInput(false);
          }
        } catch (error) {
          console.error('Account discovery error:', error);
          // Don't fail the form if discovery fails - show manual input
          setDiscoveredAccounts([]);
          setShowManualInput(true);
        } finally {
          setDiscovering(false);
        }
      } else {
        // Clear discovered accounts on failed connection
        setDiscoveredAccounts([]);
        setSelectedAccountIds(new Set());
        setDefaultAccountId('');
        setShowManualInput(false);
      }
    } catch (error) {
      console.error('Test connection error:', error);
      setTestResult({
        success: false,
        status: 'failed',
        message: 'An unexpected error occurred while testing the connection.',
      });
      setDiscoveredAccounts([]);
      setSelectedAccountIds(new Set());
      setShowManualInput(false);
      setDefaultAccountId('');
    } finally {
      setTesting(false);
    }
  };

  // Clear test result when broker or credentials change
  const handleCredentialChange = (name: string, value: string) => {
    setCredentials((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear previous test result when credentials change
    setTestResult(null);
  };

  // Clear test result when broker changes
  const handleBrokerChange = (value: BrokerType) => {
    setBroker(value);
    setCredentials({});
    setTestResult(null);
    setDiscoveredAccounts([]);
    setSelectedAccountIds(new Set());
    setDefaultAccountId('');
    setManualAccountId('');
    setShowManualInput(false);
  };
  
  // Handle account selection toggle
  const handleAccountToggle = (accountId: string, checked: boolean) => {
    const newSelected = new Set(selectedAccountIds);
    if (checked) {
      newSelected.add(accountId);
    } else {
      newSelected.delete(accountId);
      // If unselected account was default, clear default
      if (defaultAccountId === accountId) {
        setDefaultAccountId('');
      }
    }
    setSelectedAccountIds(newSelected);
    
    // If no default and we have selections, set first as default
    if (!defaultAccountId && newSelected.size > 0) {
      setDefaultAccountId(Array.from(newSelected)[0]);
    }
  };
  
  // Handle default account change
  const handleDefaultChange = (accountId: string) => {
    // Only allow setting default if account is selected
    if (selectedAccountIds.has(accountId)) {
      setDefaultAccountId(accountId);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Block submit for unsupported brokers
    if (!isBrokerSupported) {
      setFormError('This broker is not yet supported. Please select a supported broker.');
      return;
    }
    
    setSubmitting(true);
    setFormError(null);

    try {
      // Map UI credentials to backend format
      const backendCredentials = mapCredentialsToBackend(broker, credentials);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Create account - credential keys:', Object.keys(backendCredentials));
      }

      // Determine account_id: use existing if editing, otherwise use default account ID or manual input
      const finalAccountId = isEdit
        ? account?.account_id || ''
        : (defaultAccountId || manualAccountId || '');

      // Build broker_config with credentials
      const brokerConfigWithAccounts = {
        ...backendCredentials,
      };

      // Include discovered account selections
      const accountData: AccountCreate = {
        account_id: finalAccountId,
        broker,
        account_type: accountType,
        currency,
        leverage: parseInt(leverage),
        broker_config: brokerConfigWithAccounts,
      };
      
      // Add broker account selection if accounts were discovered
      if (discoveredAccounts.length > 0 && selectedAccountIds.size > 0) {
        accountData.enabled_broker_account_ids = Array.from(selectedAccountIds);
        if (defaultAccountId && selectedAccountIds.has(defaultAccountId)) {
          accountData.default_broker_account_id = defaultAccountId;
        }
        // Cache discovered accounts metadata
        accountData.discovered_accounts_cache = discoveredAccounts.map(acc => ({
          broker_account_id: acc.broker_account_id || acc.id,
          account_number: acc.account_number,
          display_name: acc.display_name || acc.name,
          status: acc.status,
          account_type: acc.account_type,
          meta: acc.meta || {},
        }));
      }

      await onSubmit(accountData);
      onClose();
    } catch (error) {
      console.error('Failed to submit account:', error);
      // Form stays open, parent handles toast notification
      // Show brief inline error as feedback
      setFormError('Save failed. Please check details above and try again.');
    } finally {
      setSubmitting(false);
    }
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
              onValueChange={(value) => handleBrokerChange(value as BrokerType)}
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

          {/* Account ID removed - now comes from account discovery or is auto-generated */}

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
            {!isBrokerSupported ? (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
              <AlertDescription className="ml-2">
                This broker isn&apos;t mapped yet. Credential schemas are only available for brokers with confirmed backend support.
              </AlertDescription>
              </Alert>
            ) : broker === 'tradovate' && !isEdit ? (
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
                  {allFields.map((field) => (
                    <CredentialFieldInput
                      key={field.name}
                      field={field}
                      value={credentials[field.name] || ''}
                      onChange={(value) => handleCredentialChange(field.name, value)}
                      required={false}
                      broker={broker}
                    />
                  ))}

                  {/* Test Connection Button for Tradovate credentials */}
                  <div className="space-y-3 pt-2">
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full"
                      onClick={handleTestConnection}
                      disabled={!hasRequiredCredentials || testing}
                    >
                      {testing ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Testing Connection...
                        </>
                      ) : (
                        <>
                          <Wifi className="mr-2 h-4 w-4" />
                          Test Connection
                        </>
                      )}
                    </Button>

                    {/* Test Result Display */}
                    {testResult && (
                      <Alert
                        variant={testResult.success ? 'default' : 'destructive'}
                        className={testResult.success ? 'border-chart-2' : ''}
                      >
                        {testResult.success ? (
                          <CheckCircle2 className="h-4 w-4 text-chart-2" />
                        ) : (
                          <XCircle className="h-4 w-4" />
                        )}
                        <AlertDescription className="ml-2">
                          {testResult.message}
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    {/* Account Discovery */}
                    {discovering && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Discovering available accounts...
                      </div>
                    )}
                    
                    {discoveredAccounts.length > 0 && (
                      <div className="space-y-3 pt-2 border-t border-border">
                        <div className="flex items-center justify-between">
                          <div>
                            <Label className="text-sm font-semibold">Available Accounts ({discoveredAccounts.length})</Label>
                            <p className="text-xs text-muted-foreground mt-1">
                              Select accounts to connect. One will be set as default.
                            </p>
                          </div>
                          {discoveredAccounts.length > 3 && (
                            <div className="flex gap-2">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const allIds = new Set(discoveredAccounts.map(acc => acc.broker_account_id || acc.id || '').filter(Boolean));
                                  setSelectedAccountIds(allIds);
                                  if (!defaultAccountId && allIds.size > 0) {
                                    setDefaultAccountId(Array.from(allIds)[0]);
                                  }
                                }}
                              >
                                Select All
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedAccountIds(new Set());
                                  setDefaultAccountId('');
                                }}
                              >
                                Deselect All
                              </Button>
                            </div>
                          )}
                        </div>

                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {discoveredAccounts.map((acc) => {
                            const accId = acc.broker_account_id || acc.id || '';
                            const displayName = acc.display_name || acc.name || accId;
                            return (
                              <div key={accId} className="flex items-start gap-3 p-2 border rounded-md">
                                <Checkbox
                                  id={`account-${accId}`}
                                  checked={selectedAccountIds.has(accId)}
                                  onCheckedChange={(checked) =>
                                    handleAccountToggle(accId, checked as boolean)
                                  }
                                  className="mt-1"
                                />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <Label
                                      htmlFor={`account-${accId}`}
                                      className="font-medium cursor-pointer"
                                    >
                                      {displayName}
                                    </Label>
                                    {acc.status === 'active' && (
                                      <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                                        Active
                                      </span>
                                    )}
                                    {acc.status === 'inactive' && (
                                      <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded">
                                        Inactive
                                      </span>
                                    )}
                                    {acc.status === 'blown' && (
                                      <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded">
                                        Blown
                                      </span>
                                    )}
                                    <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                                      {acc.account_type}
                                    </span>
                                  </div>
                                  <div className="text-xs text-muted-foreground mt-1">
                                    {String((acc.meta as Record<string, unknown>)?.currency ?? acc.currency ?? 'USD')} •
                                    Balance: ${Number(acc.meta?.balance || acc.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </div>
                                  {acc.account_number && acc.account_number !== accId && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                      Account #: {acc.account_number}
                                    </div>
                                  )}
                                </div>
                                {selectedAccountIds.has(accId) && (
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="radio"
                                      id={`default-${accId}`}
                                      name="defaultAccount"
                                      checked={defaultAccountId === accId}
                                      onChange={() => handleDefaultChange(accId)}
                                      className="cursor-pointer"
                                    />
                                    <Label
                                      htmlFor={`default-${accId}`}
                                      className="text-xs text-muted-foreground cursor-pointer"
                                    >
                                      Default
                                    </Label>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                        
                        {selectedAccountIds.size === 0 && (
                          <p className="text-xs text-muted-foreground">
                            Select at least one account to continue.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
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

                {allFields.map((field) => {
                  const isRequired = field.required && !isEdit;
                  
                  return (
                    <CredentialFieldInput
                      key={field.name}
                      field={field}
                      value={credentials[field.name] || ''}
                      onChange={(value) => handleCredentialChange(field.name, value)}
                      required={isRequired}
                      broker={broker}
                    />
                  );
                })}

                {/* Test Connection Button */}
                {!isEdit && (
                  <div className="space-y-3 pt-2">
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full"
                      onClick={handleTestConnection}
                      disabled={!hasRequiredCredentials || testing}
                    >
                      {testing ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Testing Connection...
                        </>
                      ) : (
                        <>
                          <Wifi className="mr-2 h-4 w-4" />
                          Test & Validate
                        </>
                      )}
                    </Button>

                    {/* Test Result Display */}
                    {testResult && (
                      <Alert
                        variant={testResult.success ? 'default' : 'destructive'}
                        className={testResult.success ? 'border-chart-2' : ''}
                      >
                        {testResult.success ? (
                          <CheckCircle2 className="h-4 w-4 text-chart-2" />
                        ) : (
                          <XCircle className="h-4 w-4" />
                        )}
                        <AlertDescription className="ml-2">
                          {testResult.message}
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    {/* Account Discovery */}
                    {discovering && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Discovering available accounts...
                      </div>
                    )}
                    
                    {discoveredAccounts.length > 0 && (
                      <div className="space-y-3 pt-2 border-t border-border">
                        <div className="flex items-center justify-between">
                          <div>
                            <Label className="text-sm font-semibold">Available Accounts ({discoveredAccounts.length})</Label>
                            <p className="text-xs text-muted-foreground mt-1">
                              Select accounts to connect. One will be set as default.
                            </p>
                          </div>
                          {discoveredAccounts.length > 3 && (
                            <div className="flex gap-2">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const allIds = new Set(discoveredAccounts.map(acc => acc.broker_account_id || acc.id || '').filter(Boolean));
                                  setSelectedAccountIds(allIds);
                                  if (!defaultAccountId && allIds.size > 0) {
                                    setDefaultAccountId(Array.from(allIds)[0]);
                                  }
                                }}
                              >
                                Select All
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedAccountIds(new Set());
                                  setDefaultAccountId('');
                                }}
                              >
                                Deselect All
                              </Button>
                            </div>
                          )}
                        </div>

                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {discoveredAccounts.map((acc) => {
                            const accId = acc.broker_account_id || acc.id || '';
                            const displayName = acc.display_name || acc.name || accId;
                            return (
                              <div key={accId} className="flex items-start gap-3 p-2 border rounded-md">
                                <Checkbox
                                  id={`account-${accId}`}
                                  checked={selectedAccountIds.has(accId)}
                                  onCheckedChange={(checked) =>
                                    handleAccountToggle(accId, checked as boolean)
                                  }
                                  className="mt-1"
                                />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <Label
                                      htmlFor={`account-${accId}`}
                                      className="font-medium cursor-pointer"
                                    >
                                      {displayName}
                                    </Label>
                                    {acc.status === 'active' && (
                                      <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                                        Active
                                      </span>
                                    )}
                                    {acc.status === 'inactive' && (
                                      <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded">
                                        Inactive
                                      </span>
                                    )}
                                    {acc.status === 'blown' && (
                                      <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded">
                                        Blown
                                      </span>
                                    )}
                                    <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                                      {acc.account_type}
                                    </span>
                                  </div>
                                  <div className="text-xs text-muted-foreground mt-1">
                                    {String((acc.meta as Record<string, unknown>)?.currency ?? acc.currency ?? 'USD')} •
                                    Balance: ${Number(acc.meta?.balance || acc.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </div>
                                  {acc.account_number && acc.account_number !== accId && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                      Account #: {acc.account_number}
                                    </div>
                                  )}
                                </div>
                                {selectedAccountIds.has(accId) && (
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="radio"
                                      id={`default-${accId}`}
                                      name="defaultAccount"
                                      checked={defaultAccountId === accId}
                                      onChange={() => handleDefaultChange(accId)}
                                      className="cursor-pointer"
                                    />
                                    <Label
                                      htmlFor={`default-${accId}`}
                                      className="text-xs text-muted-foreground cursor-pointer"
                                    >
                                      Default
                                    </Label>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                        
                        {selectedAccountIds.size === 0 && (
                          <p className="text-xs text-muted-foreground">
                            Select at least one account to continue.
                          </p>
                        )}
                      </div>
                    )}

                    {/* Manual Account ID Input - shown when discovery returns empty */}
                    {showManualInput && discoveredAccounts.length === 0 && testResult?.success && (
                      <div className="space-y-3 pt-2 border-t border-border">
                        <div>
                          <Label className="text-sm font-semibold">Manual Account ID</Label>
                          <p className="text-xs text-muted-foreground mt-1">
                            No accounts were discovered. Enter your account ID manually.
                          </p>
                        </div>
                        <Input
                          id="manual-account-id"
                          value={manualAccountId}
                          onChange={(e) => setManualAccountId(e.target.value)}
                          placeholder="Enter account ID (e.g., 12345)"
                        />
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Form Error Display */}
          {formError && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription className="ml-2">{formError}</AlertDescription>
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
            <Button
              type="submit"
              disabled={
                submitting ||
                !isBrokerSupported ||
                (discoveredAccounts.length > 0 && selectedAccountIds.size === 0) ||
                (showManualInput && discoveredAccounts.length === 0 && !manualAccountId.trim())
              }
            >
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
