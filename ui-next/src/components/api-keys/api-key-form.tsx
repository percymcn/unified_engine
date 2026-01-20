'use client';

import { useState } from 'react';
import { ApiKeyCreate } from '@/types/api-key';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface ApiKeyFormProps {
  onSubmit: (data: ApiKeyCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function ApiKeyForm({ onSubmit, onCancel, isLoading }: ApiKeyFormProps) {
  const [name, setName] = useState('');
  const [expiration, setExpiration] = useState<string>('never');
  const [permissions, setPermissions] = useState<string[]>(['read']);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const data: ApiKeyCreate = {
      name,
      permissions,
    };

    if (expiration !== 'never') {
      data.expires_days = parseInt(expiration, 10);
    }

    onSubmit(data);
  };

  const togglePermission = (permission: string) => {
    setPermissions((prev) =>
      prev.includes(permission)
        ? prev.filter((p) => p !== permission)
        : [...prev, permission]
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          placeholder="My API Key"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          disabled={isLoading}
        />
        <p className="text-sm text-muted-foreground">
          A descriptive name for this API key
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="expiration">Expiration</Label>
        <Select value={expiration} onValueChange={setExpiration} disabled={isLoading}>
          <SelectTrigger id="expiration">
            <SelectValue placeholder="Select expiration" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="never">Never</SelectItem>
            <SelectItem value="30">30 days</SelectItem>
            <SelectItem value="90">90 days</SelectItem>
            <SelectItem value="365">1 year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Permissions</Label>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="read"
              checked={permissions.includes('read')}
              onCheckedChange={() => togglePermission('read')}
              disabled={isLoading}
            />
            <label
              htmlFor="read"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Read
            </label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="write"
              checked={permissions.includes('write')}
              onCheckedChange={() => togglePermission('write')}
              disabled={isLoading}
            />
            <label
              htmlFor="write"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Write
            </label>
          </div>
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Creating...' : 'Create API Key'}
        </Button>
      </div>
    </form>
  );
}
