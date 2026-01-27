'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { WebhookConfig } from '@/types/routing';
import {
  Copy,
  Edit,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useToast } from '@/hooks/use-toast';

interface WebhookConfigCardProps {
  config: WebhookConfig;
  onEdit: (config: WebhookConfig) => void;
  onDelete: (config: WebhookConfig) => void;
  onToggleActive: (config: WebhookConfig, active: boolean) => void;
  onRegenerateKey: (config: WebhookConfig) => void;
}

const SOURCE_DISPLAY_NAMES: Record<string, string> = {
  tradingview: 'TradingView',
  trailhacker: 'TrailHacker',
  custom: 'Custom',
};

export function WebhookConfigCard({
  config,
  onEdit,
  onDelete,
  onToggleActive,
  onRegenerateKey,
}: WebhookConfigCardProps) {
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  // Use the backend API URL for webhooks, not the frontend URL
  const webhookBaseUrl = process.env.NEXT_PUBLIC_WEBHOOK_BASE_URL ||
                         process.env.NEXT_PUBLIC_BACKEND_URL ||
                         'https://api.tradeflow.fluxeo.net';
  const webhookUrl = `${webhookBaseUrl}/webhooks/tradingview/${config.webhook_key}`;

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText(webhookUrl);
      setCopied(true);
      toast({ title: 'Copied!' });
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const successRate =
    config.total_signals > 0
      ? ((config.successful_signals / config.total_signals) * 100).toFixed(1)
      : '0';

  return (
    <Card className={config.is_active ? '' : 'opacity-60'}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg">{config.name}</CardTitle>
              <Badge variant="secondary" className="text-xs">
                {SOURCE_DISPLAY_NAMES[config.source] || config.source}
              </Badge>
              {config.is_active ? (
                <Badge variant="default" className="text-xs bg-green-600">
                  Active
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-xs">
                  Inactive
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={config.is_active}
              onCheckedChange={(checked) => onToggleActive(config, checked)}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => onEdit(config)}
            >
              <Edit className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDelete(config)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Webhook URL */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-muted-foreground">
              Webhook URL
            </label>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyUrl}
                className="h-7 text-xs"
              >
                <Copy className="h-3 w-3 mr-1" />
                {copied ? 'Copied!' : 'Copy'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRegenerateKey(config)}
                className="h-7 text-xs"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Regenerate
              </Button>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 bg-muted rounded-md font-mono text-xs break-all">
            {webhookUrl}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Total Signals</div>
            <div className="text-xl font-bold">{config.total_signals}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-600" />
              Success
            </div>
            <div className="text-xl font-bold text-green-600">
              {config.successful_signals}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <XCircle className="h-3 w-3 text-red-600" />
              Failed
            </div>
            <div className="text-xl font-bold text-red-600">
              {config.failed_signals}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Success Rate</div>
            <div className="text-xl font-bold">{successRate}%</div>
          </div>
        </div>

        {/* Last Signal */}
        {config.last_signal_at && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t border-border">
            <Clock className="h-3 w-3" />
            Last signal:{' '}
            {formatDistanceToNow(new Date(config.last_signal_at), {
              addSuffix: true,
            })}
          </div>
        )}

        {/* Routing Info */}
        <div className="space-y-2 pt-2 border-t border-border">
          <div className="text-xs font-medium">Configuration</div>
          <div className="space-y-1 text-xs text-muted-foreground">
            {config.routing_rules.length > 0 && (
              <div>
                {config.routing_rules.length} routing rule
                {config.routing_rules.length !== 1 ? 's' : ''}
              </div>
            )}
            {config.symbol_filter && config.symbol_filter.length > 0 && (
              <div>Symbol filter: {config.symbol_filter.join(', ')}</div>
            )}
            {config.action_filter && config.action_filter.length > 0 && (
              <div>
                Action filter: {config.action_filter.map((a) => a.toUpperCase()).join(', ')}
              </div>
            )}
            {config.default_account_id && (
              <div>Default account: #{config.default_account_id}</div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
