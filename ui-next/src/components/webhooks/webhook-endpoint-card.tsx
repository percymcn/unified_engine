'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Settings } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WebhookUrlDisplay } from './webhook-url-display';
import { PayloadExample } from './payload-example';
import { WebhookEndpoint } from '@/types/webhook';
import Link from 'next/link';

interface WebhookEndpointCardProps {
  endpoint: WebhookEndpoint;
  webhookUrl: string;
  isConfigured?: boolean;
}

export function WebhookEndpointCard({ endpoint, webhookUrl, isConfigured }: WebhookEndpointCardProps) {
  const [showPayload, setShowPayload] = useState(false);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl">{endpoint.name}</CardTitle>
            <CardDescription className="mt-2">{endpoint.description}</CardDescription>
          </div>
          {isConfigured && (
            <Badge variant="outline" className="text-green-600 border-green-600">
              Active
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Webhook URL */}
        <div>
          <label className="text-sm font-medium mb-2 block">Webhook URL</label>
          <WebhookUrlDisplay url={webhookUrl} isConfigured={isConfigured} />
        </div>

        {/* Required Fields */}
        <div>
          <label className="text-sm font-medium mb-2 block">Required Fields</label>
          <div className="flex flex-wrap gap-2">
            {endpoint.required_fields.map((field) => (
              <Badge key={field} variant="secondary">
                {field}
              </Badge>
            ))}
          </div>
        </div>

        {/* Example Payload */}
        <div>
          <button
            onClick={() => setShowPayload(!showPayload)}
            className="flex items-center gap-2 text-sm font-medium hover:underline"
          >
            {showPayload ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            Example Payload
          </button>
          {showPayload && (
            <div className="mt-2">
              <PayloadExample payload={endpoint.example_payload} />
            </div>
          )}
        </div>

        {/* Configure Routing Link */}
        <div className="pt-2 border-t">
          <Link href="/dashboard/settings/routing">
            <Button variant="outline" size="sm" className="w-full">
              <Settings className="h-4 w-4 mr-2" />
              {isConfigured ? 'Manage Routing' : 'Configure Routing'}
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
