'use client';

import { useEffect, useState } from 'react';
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
import { Plus, Loader2 } from 'lucide-react';

export default function RoutingConfigPage() {
  const [configs, setConfigs] = useState<WebhookConfig[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<WebhookConfig | undefined>();
  const [deletingConfig, setDeletingConfig] = useState<WebhookConfig | undefined>();

  // Load data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configsData, accountsData] = await Promise.all([
        getWebhookConfigs(),
        getAccounts(),
      ]);
      setConfigs(configsData);
      setAccounts(accountsData);
    } catch (error) {
      console.error('Failed to load data:', error);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
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
      {configs.length === 0 ? (
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
