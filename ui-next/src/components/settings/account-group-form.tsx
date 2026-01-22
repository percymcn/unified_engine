'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Folder, Briefcase, Building, Star, Shield, Users } from 'lucide-react';
import { AccountGroup, CreateAccountGroupRequest, UpdateAccountGroupRequest } from '@/types/account';
import { cn } from '@/lib/utils';

interface AccountGroupFormProps {
  group?: AccountGroup;
  onSubmit: (data: CreateAccountGroupRequest | UpdateAccountGroupRequest) => Promise<void>;
  onCancel: () => void;
}

// Available colors for groups
const COLOR_OPTIONS = [
  { value: '#6366f1', name: 'Indigo' },
  { value: '#8b5cf6', name: 'Violet' },
  { value: '#ec4899', name: 'Pink' },
  { value: '#ef4444', name: 'Red' },
  { value: '#f97316', name: 'Orange' },
  { value: '#eab308', name: 'Yellow' },
  { value: '#22c55e', name: 'Green' },
  { value: '#14b8a6', name: 'Teal' },
  { value: '#3b82f6', name: 'Blue' },
  { value: '#64748b', name: 'Slate' },
];

// Available icons for groups
const ICON_OPTIONS = [
  { value: 'folder', name: 'Folder', icon: Folder },
  { value: 'briefcase', name: 'Briefcase', icon: Briefcase },
  { value: 'building', name: 'Building', icon: Building },
  { value: 'star', name: 'Star', icon: Star },
  { value: 'shield', name: 'Shield', icon: Shield },
  { value: 'users', name: 'Users', icon: Users },
];

export function AccountGroupForm({
  group,
  onSubmit,
  onCancel,
}: AccountGroupFormProps) {
  const isEdit = !!group;

  const [name, setName] = useState(group?.name || '');
  const [description, setDescription] = useState(group?.description || '');
  const [color, setColor] = useState(group?.color || '#6366f1');
  const [icon, setIcon] = useState(group?.icon || 'folder');
  const [submitting, setSubmitting] = useState(false);

  // Reset form when group changes
  useEffect(() => {
    if (group) {
      setName(group.name);
      setDescription(group.description || '');
      setColor(group.color);
      setIcon(group.icon);
    } else {
      setName('');
      setDescription('');
      setColor('#6366f1');
      setIcon('folder');
    }
  }, [group]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      if (isEdit) {
        await onSubmit({
          name,
          description: description || undefined,
          color,
          icon,
        });
      } else {
        await onSubmit({
          name,
          description: description || undefined,
          color,
          icon,
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Name */}
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Prop Firm Accounts"
          required
          maxLength={100}
        />
      </div>

      {/* Description */}
      <div className="space-y-2">
        <Label htmlFor="description">Description (optional)</Label>
        <Input
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Brief description of this group"
          maxLength={500}
        />
      </div>

      {/* Color Selection */}
      <div className="space-y-2">
        <Label>Color</Label>
        <div className="flex flex-wrap gap-2">
          {COLOR_OPTIONS.map((colorOption) => (
            <button
              key={colorOption.value}
              type="button"
              onClick={() => setColor(colorOption.value)}
              className={cn(
                'w-8 h-8 rounded-full border-2 transition-all',
                color === colorOption.value
                  ? 'border-foreground scale-110'
                  : 'border-transparent hover:border-muted-foreground/50'
              )}
              style={{ backgroundColor: colorOption.value }}
              title={colorOption.name}
            />
          ))}
        </div>
      </div>

      {/* Icon Selection */}
      <div className="space-y-2">
        <Label>Icon</Label>
        <div className="flex flex-wrap gap-2">
          {ICON_OPTIONS.map((iconOption) => {
            const IconComponent = iconOption.icon;
            return (
              <button
                key={iconOption.value}
                type="button"
                onClick={() => setIcon(iconOption.value)}
                className={cn(
                  'p-2.5 rounded-lg border-2 transition-all',
                  icon === iconOption.value
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-muted-foreground/50'
                )}
                title={iconOption.name}
              >
                <IconComponent
                  className="h-5 w-5"
                  style={{ color: icon === iconOption.value ? color : undefined }}
                />
              </button>
            );
          })}
        </div>
      </div>

      {/* Preview */}
      <div className="space-y-2">
        <Label>Preview</Label>
        <div
          className="flex items-center gap-3 p-3 rounded-lg border"
          style={{ borderColor: color }}
        >
          <div
            className="p-2 rounded-lg"
            style={{ backgroundColor: `${color}20` }}
          >
            {(() => {
              const IconComponent = ICON_OPTIONS.find((i) => i.value === icon)?.icon || Folder;
              return <IconComponent className="h-5 w-5" style={{ color }} />;
            })()}
          </div>
          <div>
            <p className="font-medium">{name || 'Group Name'}</p>
            <p className="text-sm text-muted-foreground">
              {description || 'No description'}
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting || !name.trim()}>
          {submitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {isEdit ? 'Updating...' : 'Creating...'}
            </>
          ) : isEdit ? (
            'Update Group'
          ) : (
            'Create Group'
          )}
        </Button>
      </div>
    </form>
  );
}
