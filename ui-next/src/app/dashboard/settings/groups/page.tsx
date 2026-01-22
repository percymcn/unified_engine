'use client';

import { useEffect, useState } from 'react';
import { Plus, FolderOpen, RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { AccountGroupCard } from '@/components/settings/account-group-card';
import { AccountGroupForm } from '@/components/settings/account-group-form';
import { ManageGroupAccountsDialog } from '@/components/settings/manage-group-accounts-dialog';
import { AccountGroup, Account, CreateAccountGroupRequest, UpdateAccountGroupRequest } from '@/types/account';
import {
  getAccountGroups,
  createAccountGroup,
  updateAccountGroup,
  deleteAccountGroup,
  getAccounts,
} from '@/lib/api/accounts';
import { useToast } from '@/hooks/use-toast';
import { Skeleton } from '@/components/ui/skeleton';

export default function AccountGroupsPage() {
  const [groups, setGroups] = useState<AccountGroup[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingGroup, setEditingGroup] = useState<AccountGroup | undefined>();
  const [deletingGroup, setDeletingGroup] = useState<AccountGroup | undefined>();
  const [manageGroup, setManageGroup] = useState<AccountGroup | undefined>();
  const [deleting, setDeleting] = useState(false);

  const { toast } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [groupsData, accountsData] = await Promise.all([
        getAccountGroups(),
        getAccounts(),
      ]);
      setGroups(groupsData);
      setAccounts(accountsData);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Unable to load account groups. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (data: CreateAccountGroupRequest) => {
    try {
      const newGroup = await createAccountGroup(data);
      setGroups((prev) => [...prev, newGroup]);
      setShowForm(false);
      toast({
        title: 'Group Created',
        description: `"${data.name}" has been created successfully.`,
      });
    } catch (err) {
      console.error('Failed to create group:', err);
      toast({
        title: 'Create Failed',
        description: 'Failed to create account group. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleUpdate = async (data: UpdateAccountGroupRequest) => {
    if (!editingGroup) return;

    try {
      const updatedGroup = await updateAccountGroup(editingGroup.id, data);
      setGroups((prev) =>
        prev.map((g) => (g.id === updatedGroup.id ? updatedGroup : g))
      );
      setEditingGroup(undefined);
      setShowForm(false);
      toast({
        title: 'Group Updated',
        description: 'Account group has been updated successfully.',
      });
    } catch (err) {
      console.error('Failed to update group:', err);
      toast({
        title: 'Update Failed',
        description: 'Failed to update account group. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingGroup) return;

    try {
      setDeleting(true);
      await deleteAccountGroup(deletingGroup.id);
      setGroups((prev) => prev.filter((g) => g.id !== deletingGroup.id));
      setDeletingGroup(undefined);
      toast({
        title: 'Group Deleted',
        description: 'Account group has been deleted. Accounts have been unassigned.',
      });
    } catch (err) {
      console.error('Failed to delete group:', err);
      toast({
        title: 'Delete Failed',
        description: 'Failed to delete account group. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setDeleting(false);
    }
  };

  const handleOpenCreate = () => {
    setEditingGroup(undefined);
    setShowForm(true);
  };

  const handleOpenEdit = (group: AccountGroup) => {
    setEditingGroup(group);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingGroup(undefined);
  };

  const handleAccountsChanged = () => {
    // Reload data to update account counts
    loadData();
    setManageGroup(undefined);
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-9 w-48" />
            <Skeleton className="h-5 w-80" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-48 w-full rounded-lg" />
          <Skeleton className="h-48 w-full rounded-lg" />
          <Skeleton className="h-48 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Account Groups</h1>
          <p className="text-muted-foreground">
            Organize your trading accounts into groups
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTitle>Error Loading Groups</AlertTitle>
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={loadData} className="ml-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Account Groups</h1>
          <p className="text-muted-foreground">
            Organize your trading accounts into groups
          </p>
        </div>
        <Button onClick={handleOpenCreate}>
          <Plus className="h-4 w-4 mr-2" />
          New Group
        </Button>
      </div>

      {/* Groups Grid */}
      {groups.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-96 border border-dashed border-border rounded-lg">
          <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
          <div className="text-center space-y-2">
            <h3 className="font-semibold text-lg">No account groups</h3>
            <p className="text-muted-foreground">
              Create groups to organize your trading accounts
            </p>
            <Button onClick={handleOpenCreate} className="mt-4">
              <Plus className="h-4 w-4 mr-2" />
              Create Group
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {groups.map((group) => (
            <AccountGroupCard
              key={group.id}
              group={group}
              onEdit={handleOpenEdit}
              onDelete={setDeletingGroup}
              onManageAccounts={setManageGroup}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={showForm} onOpenChange={handleCloseForm}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingGroup ? 'Edit Group' : 'Create New Group'}
            </DialogTitle>
            <DialogDescription>
              {editingGroup
                ? 'Update the group details below.'
                : 'Create a group to organize your trading accounts.'}
            </DialogDescription>
          </DialogHeader>
          {editingGroup ? (
            <AccountGroupForm
              group={editingGroup}
              onSubmit={handleUpdate}
              onCancel={handleCloseForm}
            />
          ) : (
            <AccountGroupForm
              onSubmit={handleCreate}
              onCancel={handleCloseForm}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog
        open={!!deletingGroup}
        onOpenChange={(open) => !open && setDeletingGroup(undefined)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Account Group?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deletingGroup?.name}&quot;?
              <br />
              <br />
              {deletingGroup?.accountCount && deletingGroup.accountCount > 0 ? (
                <>
                  This group has <strong>{deletingGroup.accountCount} accounts</strong>.
                  They will be unassigned from this group but not deleted.
                </>
              ) : (
                'This action cannot be undone.'
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive hover:bg-destructive/90"
              disabled={deleting}
            >
              {deleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete Group'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Manage Accounts Dialog */}
      {manageGroup && (
        <ManageGroupAccountsDialog
          group={manageGroup}
          accounts={accounts}
          onClose={() => setManageGroup(undefined)}
          onSave={handleAccountsChanged}
        />
      )}
    </div>
  );
}
