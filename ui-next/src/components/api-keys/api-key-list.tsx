'use client';

import { ApiKey } from '@/types/api-key';
import { ApiKeyCard } from './api-key-card';
import { Button } from '@/components/ui/button';
import { Plus, Key } from 'lucide-react';

interface ApiKeyListProps {
  apiKeys: ApiKey[];
  onCreateClick: () => void;
  onRevoke: (id: number) => void;
  isLoading?: boolean;
}

export function ApiKeyList({ apiKeys, onCreateClick, onRevoke, isLoading }: ApiKeyListProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="text-sm text-muted-foreground">Loading API keys...</p>
        </div>
      </div>
    );
  }

  if (apiKeys.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <div className="rounded-full bg-muted p-6">
          <Key className="h-12 w-12 text-muted-foreground" />
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-lg font-semibold">No API keys</h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            You haven't created any API keys yet. Create one to start using the API.
          </p>
        </div>
        <Button onClick={onCreateClick}>
          <Plus className="h-4 w-4 mr-2" />
          Create your first API key
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {apiKeys.map((apiKey) => (
          <ApiKeyCard key={apiKey.id} apiKey={apiKey} onRevoke={onRevoke} />
        ))}
      </div>
    </div>
  );
}
