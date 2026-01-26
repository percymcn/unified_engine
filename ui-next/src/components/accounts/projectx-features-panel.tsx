'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, ChevronUp, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ProjectXFeaturesPanelProps {
  accountId: number;
}

interface ApiResult {
  success: boolean;
  data?: unknown;
  error?: string;
  status?: number;
}

type ActionForm = {
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
};

type Action = {
  label: string;
  endpoint: string;
  method: string;
  form?: ActionForm;
};

type Section = {
  id: string;
  title: string;
  actions: Action[];
};

function toStringRecord(input?: Record<string, unknown>): Record<string, string> {
  const out: Record<string, string> = {};
  if (!input) return out;
  for (const [key, value] of Object.entries(input)) {
    out[key] = value == null ? '' : String(value);
  }
  return out;
}

export function ProjectXFeaturesPanel({ accountId }: ProjectXFeaturesPanelProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, ApiResult>>({});
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8765';
  
  const toggleSection = (section: string) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };
  
  const callApi = async (endpoint: string, method: string = 'GET', body?: Record<string, unknown>) => {
    const key = endpoint.split('?')[0].split('/').pop() || endpoint;
    setLoading(key);
    
    try {
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];
      
      const options: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
        },
      };
      
      if (body && method !== 'GET') {
        options.body = JSON.stringify(body);
      }
      
      const url = method === 'GET' && body
        ? `${baseUrl}${endpoint}?${new URLSearchParams(toStringRecord(body)).toString()}`
        : `${baseUrl}${endpoint}`;
      
      const response = await fetch(url, options);
      const data = await response.json();
      
      setResults(prev => ({ ...prev, [key]: { success: response.ok, data, status: response.status } }));
      
      if (response.ok) {
        toast({
          title: 'Success',
          description: `API call successful`,
        });
      } else {
        toast({
          title: 'Error',
          description: data.detail || `API call failed: ${response.status}`,
          variant: 'destructive',
        });
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'API call failed';
      setResults(prev => ({ ...prev, [key]: { success: false, error: errorMessage } }));
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(null);
    }
  };
  
  const sections: Section[] = [
    {
      id: 'orders',
      title: 'Orders',
      actions: [
        {
          label: 'Fetch Orders',
          endpoint: `/api/v1/brokers/projectx/orders?account_id=${accountId}`,
          method: 'GET',
        },
      ],
    },
    {
      id: 'positions',
      title: 'Positions',
      actions: [
        {
          label: 'Fetch Positions',
          endpoint: `/api/v1/brokers/projectx/positions?account_id=${accountId}`,
          method: 'GET',
        },
        {
          label: 'Position History',
          endpoint: `/api/v1/brokers/projectx/positions/history?account_id=${accountId}&symbol=MNQ&days=30`,
          method: 'GET',
        },
      ],
    },
    {
      id: 'market',
      title: 'Market Data',
      actions: [
        {
          label: 'Get Quote',
          endpoint: `/api/v1/brokers/projectx/market/quote?account_id=${accountId}&symbol=MNQ`,
          method: 'GET',
        },
        {
          label: 'Get Orderbook',
          endpoint: `/api/v1/brokers/projectx/market/orderbook?account_id=${accountId}&symbol=MNQ&depth=10`,
          method: 'GET',
        },
      ],
    },
    {
      id: 'stats',
      title: 'Statistics',
      actions: [
        {
          label: 'Session Stats',
          endpoint: `/api/v1/brokers/projectx/stats/session?account_id=${accountId}&symbol=MNQ`,
          method: 'GET',
        },
        {
          label: 'Performance Stats',
          endpoint: `/api/v1/brokers/projectx/stats/performance?account_id=${accountId}&symbol=MNQ`,
          method: 'GET',
        },
      ],
    },
    {
      id: 'bracket',
      title: 'Bracket Order',
      actions: [
        {
          label: 'Place Bracket Order',
          endpoint: `/api/v1/brokers/projectx/orders/bracket`,
          method: 'POST',
          form: {
            symbol: 'MNQ',
            side: 'buy',
            quantity: 1,
            entry_price: null,
            stop_loss: null,
            take_profit: null,
          },
        },
      ],
    },
  ];
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>ProjectX Features</CardTitle>
        <CardDescription>
          Test and interact with ProjectX/TopStep SDK features
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sections.map(section => (
          <Collapsible
            key={section.id}
            open={openSections[section.id]}
            onOpenChange={() => toggleSection(section.id)}
          >
            <CollapsibleTrigger className="flex items-center justify-between w-full p-3 border rounded-lg hover:bg-muted">
              <span className="font-medium">{section.title}</span>
              {openSections[section.id] ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2">
              {section.actions.map((action, idx) => (
                <div key={idx} className="p-3 border rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{action.label}</span>
                    <Button
                      size="sm"
                      onClick={() => callApi(action.endpoint, action.method, action.form)}
                      disabled={loading === action.endpoint.split('/').pop()}
                    >
                      {loading === action.endpoint.split('/').pop() ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Loading...
                        </>
                      ) : (
                        'Execute'
                      )}
                    </Button>
                  </div>
                  
                  {action.form && (
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label>Symbol</Label>
                        <Input
                          defaultValue={action.form.symbol}
                          onChange={(e) => {
                            if (!action.form) return;
                            action.form.symbol = e.target.value;
                          }}
                        />
                      </div>
                      <div>
                        <Label>Side</Label>
                        <select
                          className="w-full p-2 border rounded"
                          defaultValue={action.form.side}
                          onChange={(e) => {
                            if (!action.form) return;
                            action.form.side = e.target.value;
                          }}
                        >
                          <option value="buy">Buy</option>
                          <option value="sell">Sell</option>
                        </select>
                      </div>
                      <div>
                        <Label>Quantity</Label>
                        <Input
                          type="number"
                          defaultValue={action.form.quantity}
                          onChange={(e) => {
                            if (!action.form) return;
                            action.form.quantity = parseFloat(e.target.value);
                          }}
                        />
                      </div>
                      <div>
                        <Label>Entry Price (optional)</Label>
                        <Input
                          type="number"
                          defaultValue={action.form.entry_price || ''}
                          onChange={(e) => {
                            if (!action.form) return;
                            action.form.entry_price = e.target.value ? parseFloat(e.target.value) : null;
                          }}
                        />
                      </div>
                      <div>
                        <Label>Stop Loss</Label>
                        <Input
                          type="number"
                          defaultValue={action.form.stop_loss || ''}
                          onChange={(e) => {
                            if (!action.form) return;
                            action.form.stop_loss = e.target.value ? parseFloat(e.target.value) : null;
                          }}
                        />
                      </div>
                      <div>
                        <Label>Take Profit</Label>
                        <Input
                          type="number"
                          defaultValue={action.form.take_profit || ''}
                          onChange={(e) => {
                            if (!action.form) return;
                            action.form.take_profit = e.target.value ? parseFloat(e.target.value) : null;
                          }}
                        />
                      </div>
                    </div>
                  )}
                  
                  {results[action.endpoint.split('/').pop() || ''] && (
                    <div className="mt-2 p-2 bg-muted rounded text-xs">
                      <div className="flex items-center gap-2 mb-1">
                        {results[action.endpoint.split('/').pop() || ''].success ? (
                          <CheckCircle2 className="h-3 w-3 text-green-500" />
                        ) : (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                        <span>
                          Status: {results[action.endpoint.split('/').pop() || ''].status || 'N/A'}
                        </span>
                      </div>
                      <Textarea
                        readOnly
                        value={JSON.stringify(
                          results[action.endpoint.split('/').pop() || ''].data || results[action.endpoint.split('/').pop() || ''].error,
                          null,
                          2
                        )}
                        className="font-mono text-xs"
                        rows={6}
                      />
                    </div>
                  )}
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        ))}
      </CardContent>
    </Card>
  );
}
