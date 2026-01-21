'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Plus, Loader2 } from 'lucide-react';
import { Account, AccountCreate } from '@/types/account';
import { AccountCard } from './account-card';
import { AccountForm } from './account-form';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  getAccounts,
  createAccount,
  updateAccount,
  deleteAccount,
} from '@/lib/api/accounts';
import { useToast } from '@/hooks/use-toast';
import { parseAccountError, formatErrorForToast } from '@/lib/errors/account-errors';

// Helper to get error message from OAuth error codes
function getOAuthErrorMessage(error: string): { title: string; description: string } {
  switch (error) {
    case 'access_denied':
      return {
        title: 'Authorization Denied',
        description: 'You denied access to your Tradovate account. Click the OAuth button to try again.',
      };
    case 'missing_params':
      return {
        title: 'OAuth Incomplete',
        description: 'The OAuth response was incomplete. Please try connecting again.',
      };
    case 'token_exchange_failed':
      return {
        title: 'Token Exchange Failed',
        description: 'Failed to complete OAuth authorization. Please try again or use manual credentials.',
      };
    case 'expired':
      return {
        title: 'Session Expired',
        description: 'Your authorization session expired. Please start the connection process again.',
      };
    default:
      return {
        title: 'Connection Error',
        description: `An error occurred during OAuth: ${error}. Please try again.`,
      };
  }
}

export function AccountList() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | undefined>();
  const [deletingAccount, setDeletingAccount] = useState<Account | undefined>();
  const [deleting, setDeleting] = useState(false);
  const [processingOAuth, setProcessingOAuth] = useState(false);

  const searchParams = useSearchParams();
  const { toast } = useToast();

  // Handle OAuth connect with tokens from callback
  const handleOAuthConnect = useCallback(async (tokens: {
    access_token: string;
    refresh_token?: string;
    expires_in: number;
    environment: string;
  }) => {
    try {
      // Create account with OAuth tokens
      const response = await fetch('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: `tradovate_${tokens.environment}_${Date.now()}`,
          broker: 'tradovate',
          account_type: tokens.environment === 'live' ? 'live' : 'demo',
          oauth_tokens: tokens,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw errorData;
      }

      const newAccount = await response.json();
      setAccounts((prev) => [...prev, newAccount]);

      toast({
        title: 'Account Connected',
        description: 'Your Tradovate account has been connected successfully.',
      });
    } catch (error) {
      console.error('OAuth account creation error:', error);
      const userError = parseAccountError(error, 'create');
      toast(formatErrorForToast(userError));
    }
  }, [toast]);

  // Handle OAuth callback on mount
  useEffect(() => {
    // Check for OAuth callback
    const connected = searchParams.get('tradovate_connected');
    const error = searchParams.get('error');

    if (error) {
      const errorInfo = getOAuthErrorMessage(error);
      toast({
        title: errorInfo.title,
        description: errorInfo.description,
        variant: 'destructive',
      });
      // Clean URL
      window.history.replaceState({}, '', '/dashboard/settings/accounts');
      return;
    }

    if (connected === 'true') {
      setProcessingOAuth(true);

      // Extract tokens from URL fragment
      const hash = window.location.hash;
      if (hash.startsWith('#tokens=')) {
        try {
          const tokensJson = decodeURIComponent(hash.slice(8));
          const tokens = JSON.parse(tokensJson);

          // Create account with OAuth tokens
          handleOAuthConnect(tokens).finally(() => {
            setProcessingOAuth(false);
          });
        } catch (e) {
          console.error('Failed to parse tokens:', e);
          toast({
            title: 'Connection Failed',
            description: 'Failed to process OAuth response',
            variant: 'destructive',
          });
          setProcessingOAuth(false);
        }
      } else {
        setProcessingOAuth(false);
      }

      // Clean URL (remove fragment and query params)
      window.history.replaceState({}, '', '/dashboard/settings/accounts');
    }
  }, [searchParams, toast, handleOAuthConnect]);

  // Fetch accounts on mount
  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const data = await getAccounts();
      setAccounts(data);
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
      const userError = parseAccountError(error, 'fetch');
      toast(formatErrorForToast(userError));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (data: AccountCreate) => {
    try {
      const newAccount = await createAccount(data);
      setAccounts((prev) => [...prev, newAccount]);
      toast({
        title: 'Account Created',
        description: 'Your broker account has been connected successfully.',
      });
    } catch (error) {
      console.error('Failed to create account:', error);
      const userError = parseAccountError(error, 'create');
      toast(formatErrorForToast(userError));
      throw error; // Re-throw to prevent form from closing
    }
  };

  const handleUpdate = async (data: AccountCreate) => {
    if (!editingAccount) return;
    try {
      const updated = await updateAccount(editingAccount.id, data);
      setAccounts((prev) =>
        prev.map((acc) => (acc.id === updated.id ? updated : acc))
      );
      setEditingAccount(undefined);
      toast({
        title: 'Account Updated',
        description: 'Your account settings have been saved.',
      });
    } catch (error) {
      console.error('Failed to update account:', error);
      const userError = parseAccountError(error, 'update');
      toast(formatErrorForToast(userError));
      throw error; // Re-throw to prevent form from closing
    }
  };

  const handleDelete = async () => {
    if (!deletingAccount) return;

    try {
      setDeleting(true);
      await deleteAccount(deletingAccount.id);
      setAccounts((prev) => prev.filter((acc) => acc.id !== deletingAccount.id));
      setDeletingAccount(undefined);
      toast({
        title: 'Account Deleted',
        description: 'The broker account has been removed.',
      });
    } catch (error) {
      console.error('Failed to delete account:', error);
      const userError = parseAccountError(error, 'delete');
      toast(formatErrorForToast(userError));
    } finally {
      setDeleting(false);
    }
  };

  const handleSyncComplete = (updatedAccount: Account) => {
    setAccounts((prev) =>
      prev.map((acc) => (acc.id === updatedAccount.id ? updatedAccount : acc))
    );
  };

  if (loading || processingOAuth) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mr-2" />
        <span className="text-muted-foreground">
          {processingOAuth ? 'Connecting Tradovate account...' : 'Loading accounts...'}
        </span>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="space-y-4">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground mb-4">
              No accounts configured yet
            </p>
            <Button onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Your First Account
            </Button>
          </CardContent>
        </Card>

        <AccountForm
          open={showForm}
          onClose={() => setShowForm(false)}
          onSubmit={handleCreate}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Add Account Button */}
      <div className="flex justify-end">
        <Button onClick={() => setShowForm(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Account
        </Button>
      </div>

      {/* Account Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {accounts.map((account) => (
          <AccountCard
            key={account.id}
            account={account}
            onEdit={setEditingAccount}
            onDelete={setDeletingAccount}
            onSyncComplete={handleSyncComplete}
          />
        ))}
      </div>

      {/* Create/Edit Form */}
      <AccountForm
        open={showForm || !!editingAccount}
        onClose={() => {
          setShowForm(false);
          setEditingAccount(undefined);
        }}
        onSubmit={editingAccount ? handleUpdate : handleCreate}
        account={editingAccount}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deletingAccount}
        onOpenChange={() => setDeletingAccount(undefined)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Account</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this account? This action cannot
              be undone.
              {deletingAccount && (
                <span className="block mt-2 font-medium text-foreground">
                  {deletingAccount.broker} - {deletingAccount.account_id}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingAccount(undefined)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete Account'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
