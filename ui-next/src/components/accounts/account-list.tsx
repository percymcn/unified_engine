'use client';

import { useState, useEffect } from 'react';
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

export function AccountList() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | undefined>();
  const [deletingAccount, setDeletingAccount] = useState<Account | undefined>();
  const [deleting, setDeleting] = useState(false);

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
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (data: AccountCreate) => {
    const newAccount = await createAccount(data);
    setAccounts((prev) => [...prev, newAccount]);
  };

  const handleUpdate = async (data: AccountCreate) => {
    if (!editingAccount) return;
    const updated = await updateAccount(editingAccount.id, data);
    setAccounts((prev) =>
      prev.map((acc) => (acc.id === updated.id ? updated : acc))
    );
    setEditingAccount(undefined);
  };

  const handleDelete = async () => {
    if (!deletingAccount) return;

    try {
      setDeleting(true);
      await deleteAccount(deletingAccount.id);
      setAccounts((prev) => prev.filter((acc) => acc.id !== deletingAccount.id));
      setDeletingAccount(undefined);
    } catch (error) {
      console.error('Failed to delete account:', error);
    } finally {
      setDeleting(false);
    }
  };

  const handleSyncComplete = (updatedAccount: Account) => {
    setAccounts((prev) =>
      prev.map((acc) => (acc.id === updatedAccount.id ? updatedAccount : acc))
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
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
