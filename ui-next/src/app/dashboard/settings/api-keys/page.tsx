'use client';

import { useState, useEffect } from 'react';
import { ApiKey, ApiKeyCreate, ApiKeyCreateResponse } from '@/types/api-key';
import { getApiKeys, createApiKey, revokeApiKey } from '@/lib/api/api-keys';
import { ApiKeyList } from '@/components/api-keys/api-key-list';
import { ApiKeyForm } from '@/components/api-keys/api-key-form';
import { ApiKeyCreatedModal } from '@/components/api-keys/api-key-created-modal';
import { Button } from '@/components/ui/button';
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
import { Plus, Lock, Sparkles } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useUser } from '@/providers/user-provider';
import { hasFeatureAccess, FEATURES, SubscriptionTier } from '@/lib/feature-flags';
import Link from 'next/link';

export default function ApiKeysPage() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyCreateResponse | null>(null);
  const [createdModalOpen, setCreatedModalOpen] = useState(false);
  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false);
  const [keyToRevoke, setKeyToRevoke] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();
  const { user } = useUser();

  const userTier = (user?.subscription_tier || 'free') as SubscriptionTier;
  const hasAccess = hasFeatureAccess(userTier, 'API_KEYS');

  useEffect(() => {
    if (hasAccess) {
      loadApiKeys();
    } else {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasAccess]);

  const loadApiKeys = async () => {
    setIsLoading(true);
    try {
      const keys = await getApiKeys();
      setApiKeys(keys);
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to load API keys',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async (data: ApiKeyCreate) => {
    setIsSubmitting(true);
    try {
      const newKey = await createApiKey(data);
      setCreatedKey(newKey);
      setCreateDialogOpen(false);
      setCreatedModalOpen(true);
      await loadApiKeys();
      toast({
        title: 'Success',
        description: 'API key created successfully',
      });
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to create API key',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevokeClick = (id: number) => {
    setKeyToRevoke(id);
    setRevokeDialogOpen(true);
  };

  const handleRevokeConfirm = async () => {
    if (!keyToRevoke) return;

    try {
      await revokeApiKey(keyToRevoke);
      await loadApiKeys();
      toast({
        title: 'Success',
        description: 'API key revoked successfully',
      });
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to revoke API key',
        variant: 'destructive',
      });
    } finally {
      setRevokeDialogOpen(false);
      setKeyToRevoke(null);
    }
  };

  const handleCreatedModalClose = () => {
    setCreatedModalOpen(false);
    setCreatedKey(null);
  };

  // Show upgrade prompt if user doesn't have access
  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">API Keys</h1>
          <p className="text-muted-foreground mt-2">
            Manage API keys for programmatic access to your trading account
          </p>
        </div>

        <div className="rounded-lg border bg-card p-8 text-center space-y-4">
          <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Lock className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-xl font-semibold">Pro Feature</h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            {FEATURES.API_KEYS.description}. Upgrade to Pro or higher to unlock API key management.
          </p>
          <div className="flex gap-3 justify-center">
            <Link href="/dashboard/settings/billing">
              <Button>
                <Sparkles className="h-4 w-4 mr-2" />
                Upgrade to Pro
              </Button>
            </Link>
          </div>
          <p className="text-xs text-muted-foreground">
            Current plan: <span className="font-medium capitalize">{userTier}</span>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">API Keys</h1>
          <p className="text-muted-foreground mt-2">
            Manage API keys for programmatic access to your trading account
          </p>
        </div>
        {apiKeys.length > 0 && (
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create API Key
          </Button>
        )}
      </div>

      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-2">What are API keys?</h2>
        <p className="text-sm text-muted-foreground">
          API keys allow you to authenticate with the trading API without using your username and password.
          Each key can have different permissions and expiration dates. Keep your API keys secure and never
          share them publicly.
        </p>
      </div>

      <ApiKeyList
        apiKeys={apiKeys}
        onCreateClick={() => setCreateDialogOpen(true)}
        onRevoke={handleRevokeClick}
        isLoading={isLoading}
      />

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Create a new API key to access the trading API programmatically.
            </DialogDescription>
          </DialogHeader>
          <ApiKeyForm
            onSubmit={handleCreate}
            onCancel={() => setCreateDialogOpen(false)}
            isLoading={isSubmitting}
          />
        </DialogContent>
      </Dialog>

      <ApiKeyCreatedModal
        apiKey={createdKey}
        open={createdModalOpen}
        onClose={handleCreatedModalClose}
      />

      <AlertDialog open={revokeDialogOpen} onOpenChange={setRevokeDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke API Key</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to revoke this API key? This action cannot be undone.
              Any applications using this key will no longer be able to authenticate.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRevokeConfirm} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
