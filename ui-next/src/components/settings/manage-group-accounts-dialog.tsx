'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2, Check } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Account, AccountGroup, BROKER_DISPLAY_NAMES } from '@/types/account';
import { addAccountToGroup, removeAccountFromGroup, getAccountSettings } from '@/lib/api/accounts';
import { useToast } from '@/hooks/use-toast';

interface ManageGroupAccountsDialogProps {
  group: AccountGroup;
  accounts: Account[];
  onClose: () => void;
  onSave: () => void;
}

interface AccountWithGroup {
  account: Account;
  inGroup: boolean;
  groupId: number | null;
}

export function ManageGroupAccountsDialog({
  group,
  accounts,
  onClose,
  onSave,
}: ManageGroupAccountsDialogProps) {
  const [accountsWithGroup, setAccountsWithGroup] = useState<AccountWithGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedAccountIds, setSelectedAccountIds] = useState<Set<number>>(new Set());
  const { toast } = useToast();

  // Load current group membership for all accounts
  useEffect(() => {
    loadAccountGroupInfo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accounts, group]);

  const loadAccountGroupInfo = async () => {
    setLoading(true);
    try {
      // Fetch settings for each account to get their current group
      const accountInfos = await Promise.all(
        accounts.map(async (account) => {
          try {
            const settings = await getAccountSettings(account.id);
            return {
              account,
              inGroup: settings.grouping.groupId === group.id,
              groupId: settings.grouping.groupId,
            };
          } catch {
            // If we can't fetch settings, assume not in group
            return {
              account,
              inGroup: false,
              groupId: null,
            };
          }
        })
      );

      setAccountsWithGroup(accountInfos);

      // Initialize selection with accounts already in this group
      const inGroupIds = new Set(
        accountInfos.filter((a) => a.inGroup).map((a) => a.account.id)
      );
      setSelectedAccountIds(inGroupIds);
    } catch (err) {
      console.error('Failed to load account group info:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAccount = (accountId: number, checked: boolean) => {
    setSelectedAccountIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(accountId);
      } else {
        next.delete(accountId);
      }
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Determine which accounts to add and remove
      const currentInGroup = new Set(
        accountsWithGroup.filter((a) => a.inGroup).map((a) => a.account.id)
      );

      const toAdd = Array.from(selectedAccountIds).filter((id) => !currentInGroup.has(id));
      const toRemove = Array.from(currentInGroup).filter((id) => !selectedAccountIds.has(id));

      // Execute all changes
      await Promise.all([
        ...toAdd.map((accountId) => addAccountToGroup(group.id, accountId)),
        ...toRemove.map((accountId) => removeAccountFromGroup(group.id, accountId)),
      ]);

      toast({
        title: 'Accounts Updated',
        description: `${toAdd.length} added, ${toRemove.length} removed from "${group.name}"`,
      });

      onSave();
    } catch (err) {
      console.error('Failed to update accounts:', err);
      toast({
        title: 'Update Failed',
        description: 'Failed to update account memberships. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  // Check if there are any changes
  const hasChanges = () => {
    const currentInGroup = new Set(
      accountsWithGroup.filter((a) => a.inGroup).map((a) => a.account.id)
    );

    if (currentInGroup.size !== selectedAccountIds.size) return true;

    const selectedArray = Array.from(selectedAccountIds);
    for (const id of selectedArray) {
      if (!currentInGroup.has(id)) return true;
    }

    return false;
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Manage Accounts in &quot;{group.name}&quot;</DialogTitle>
          <DialogDescription>
            Select which accounts should belong to this group.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Loading accounts...</span>
            </div>
          ) : accounts.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No accounts available. Create accounts first.
            </div>
          ) : (
            <div className="space-y-3">
              {accountsWithGroup.map(({ account, inGroup, groupId }) => {
                const isSelected = selectedAccountIds.has(account.id);
                const isInOtherGroup = groupId !== null && groupId !== group.id;

                return (
                  <div
                    key={account.id}
                    className="flex items-center space-x-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                  >
                    <Checkbox
                      id={`account-${account.id}`}
                      checked={isSelected}
                      onCheckedChange={(checked) =>
                        handleToggleAccount(account.id, checked as boolean)
                      }
                    />
                    <div className="flex-1 min-w-0">
                      <Label
                        htmlFor={`account-${account.id}`}
                        className="font-medium cursor-pointer block truncate"
                      >
                        {BROKER_DISPLAY_NAMES[account.broker as keyof typeof BROKER_DISPLAY_NAMES]}
                      </Label>
                      <p className="text-sm text-muted-foreground font-mono truncate">
                        {account.account_id}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {isInOtherGroup && (
                        <Badge variant="outline" className="text-xs">
                          In another group
                        </Badge>
                      )}
                      {inGroup && (
                        <Check className="h-4 w-4 text-green-500" />
                      )}
                      {!account.is_connected && (
                        <Badge variant="secondary" className="text-xs">
                          Disconnected
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <DialogFooter className="border-t pt-4">
          <div className="flex items-center justify-between w-full">
            <p className="text-sm text-muted-foreground">
              {selectedAccountIds.size} account{selectedAccountIds.size !== 1 ? 's' : ''} selected
            </p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={onClose} disabled={saving}>
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving || loading || !hasChanges()}
              >
                {saving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
