'use client';

import { ApiKey } from '@/types/api-key';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ApiKeyCardProps {
  apiKey: ApiKey;
  onRevoke: (id: number) => void;
}

export function ApiKeyCard({ apiKey, onRevoke }: ApiKeyCardProps) {
  const formatDate = (date?: string) => {
    if (!date) return 'Never';
    return formatDistanceToNow(new Date(date), { addSuffix: true });
  };

  const isExpired = apiKey.expires_at
    ? new Date(apiKey.expires_at) < new Date()
    : false;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{apiKey.name}</CardTitle>
            <div className="flex gap-2 mt-2">
              <Badge variant={apiKey.is_active && !isExpired ? 'default' : 'secondary'}>
                {apiKey.is_active ? (isExpired ? 'Expired' : 'Active') : 'Revoked'}
              </Badge>
              {apiKey.permissions.map((permission) => (
                <Badge key={permission} variant="outline">
                  {permission}
                </Badge>
              ))}
            </div>
          </div>
          {apiKey.is_active && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onRevoke(apiKey.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 text-sm text-muted-foreground">
          <div className="flex justify-between">
            <span>Created:</span>
            <span>{formatDate(apiKey.created_at)}</span>
          </div>
          {apiKey.expires_at && (
            <div className="flex justify-between">
              <span>Expires:</span>
              <span className={isExpired ? 'text-destructive' : ''}>
                {formatDate(apiKey.expires_at)}
              </span>
            </div>
          )}
          <div className="flex justify-between">
            <span>Last used:</span>
            <span>{formatDate(apiKey.last_used_at)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
