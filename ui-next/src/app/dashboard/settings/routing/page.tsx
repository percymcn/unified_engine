'use client';

import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
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
import { WebhookConfigCard } from '@/components/routing/webhook-config-card';
import { WebhookConfigForm } from '@/components/routing/webhook-config-form';
import {
  WebhookConfig,
  WebhookConfigCreate,
  WebhookConfigUpdate,
} from '@/types/routing';
import { Account } from '@/types/account';
import {
  getWebhookConfigs,
  createWebhookConfig,
  updateWebhookConfig,
  deleteWebhookConfig,
  regenerateWebhookKey,
} from '@/lib/api/routing';
import { getAccounts } from '@/lib/api/accounts';
import { Plus, RefreshCw } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export default function RoutingConfigPage() {
  const [configs, setConfigs] = useState<WebhookConfig[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<WebhookConfig | undefined>();
  const [deletingConfig, setDeletingConfig] = useState<WebhookConfig | undefined>();
  const queryClient = useQueryClient();

  // Load data
  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const handleFocus = () => {
      loadData();
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [configsData, accountsData] = await Promise.all([
        getWebhookConfigs(),
        getAccounts(),
      ]);
      setConfigs(configsData || []);
      setAccounts(accountsData || []);
      await queryClient.invalidateQueries({ queryKey: ['accounts'] });

      // Only show error if accounts fail AND we have no configs (likely no accounts connected)
      if ((accountsData?.length || 0) === 0 && (configsData?.length || 0) === 0) {
        // Don't set error - will show empty state instead
        setError(null);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      // Only show error if it's a real connection issue, not just no accounts
      const accounts = await getAccounts().catch(() => []);
      if ((accounts?.length || 0) === 0) {
        setError(null); // Will show empty state
      } else {
        setError('Unable to load configurations. Please check your connection and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (data: WebhookConfigCreate) => {
    try {
      await createWebhookConfig(data);
      await loadData();
      setFormOpen(false);
    } catch (error) {
      console.error('Failed to create webhook config:', error);
      throw error;
    }
  };

  const handleUpdate = async (data: WebhookConfigCreate) => {
    if (!editingConfig) return;

    try {
      await updateWebhookConfig(editingConfig.id, data as WebhookConfigUpdate);
      await loadData();
      setEditingConfig(undefined);
      setFormOpen(false);
    } catch (error) {
      console.error('Failed to update webhook config:', error);
      throw error;
    }
  };

  const handleDelete = async () => {
    if (!deletingConfig) return;

    try {
      await deleteWebhookConfig(deletingConfig.id);
      await loadData();
      setDeletingConfig(undefined);
    } catch (error) {
      console.error('Failed to delete webhook config:', error);
    }
  };

  const handleToggleActive = async (config: WebhookConfig, active: boolean) => {
    try {
      await updateWebhookConfig(config.id, { is_active: active });
      await loadData();
    } catch (error) {
      console.error('Failed to toggle webhook config:', error);
    }
  };

  const handleRegenerateKey = async (config: WebhookConfig) => {
    if (
      !confirm(
        'Are you sure you want to regenerate this webhook key? The old URL will stop working.'
      )
    ) {
      return;
    }

    try {
      await regenerateWebhookKey(config.id);
      await loadData();
    } catch (error) {
      console.error('Failed to regenerate webhook key:', error);
    }
  };

  const handleOpenCreate = () => {
    setEditingConfig(undefined);
    setFormOpen(true);
  };

  const handleOpenEdit = (config: WebhookConfig) => {
    setEditingConfig(config);
    setFormOpen(true);
  };

  const handleCloseForm = () => {
    setFormOpen(false);
    setEditingConfig(undefined);
  };

  // Loading state with skeletons
  if (loading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-9 w-48" />
            <Skeleton className="h-5 w-80" />
          </div>
          <Skeleton className="h-10 w-40" />
        </div>
        {/* Card skeletons */}
        <div className="grid gap-6">
          <Skeleton className="h-48 w-full rounded-lg" />
          <Skeleton className="h-48 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  // Error state with retry (only for real errors, not empty state)
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Signal Routing</h1>
          <p className="text-muted-foreground">
            Configure webhook endpoints and routing rules for incoming signals
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTitle>Error Loading Configurations</AlertTitle>
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
  
  // Empty state when no accounts connected
  if ((accounts?.length || 0) === 0 && !loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Signal Routing</h1>
          <p className="text-muted-foreground">
            Configure webhook endpoints and routing rules for incoming signals
          </p>
        </div>
        <div className="flex flex-col items-center justify-center h-96 border border-dashed border-border rounded-lg">
          <div className="text-center space-y-4">
            <div className="text-muted-foreground">
              Connect an account to enable this feature.
            </div>
            <Button asChild>
              <a href="/dashboard/settings/accounts">
                <Plus className="h-4 w-4 mr-2" />
                Connect Account
              </a>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Signal Routing</h1>
          <p className="text-muted-foreground">
            Configure webhook endpoints and routing rules for incoming signals
          </p>
        </div>
        <Button onClick={handleOpenCreate}>
          <Plus className="h-4 w-4 mr-2" />
          Add Configuration
        </Button>
      </div>

      {/* Configurations List */}
      {(configs?.length || 0) === 0 ? (
        <div className="flex flex-col items-center justify-center h-96 border border-dashed border-border rounded-lg">
          <div className="text-center space-y-4">
            <div className="text-muted-foreground">
              No webhook configurations yet
            </div>
            <Button onClick={handleOpenCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Configuration
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-6">
          {configs.map((config) => (
            <WebhookConfigCard
              key={config.id}
              config={config}
              onEdit={handleOpenEdit}
              onDelete={setDeletingConfig}
              onToggleActive={handleToggleActive}
              onRegenerateKey={handleRegenerateKey}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Form */}
      <WebhookConfigForm
        open={formOpen}
        onClose={handleCloseForm}
        onSubmit={editingConfig ? handleUpdate : handleCreate}
        accounts={accounts}
        config={editingConfig}
      />

      {/* Delete Confirmation */}
      <AlertDialog
        open={!!deletingConfig}
        onOpenChange={(open) => !open && setDeletingConfig(undefined)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Webhook Configuration?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deletingConfig?.name}&quot;? This action
              cannot be undone. The webhook URL will stop working immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
