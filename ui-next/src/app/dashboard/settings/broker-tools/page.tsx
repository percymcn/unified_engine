'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Account } from '@/types/account';

export default function BrokerToolsPage() {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedBroker, setSelectedBroker] = useState<string>('');
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Record<string, any>>({});
  const [symbol, setSymbol] = useState('MNQ');
  
  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      // Use BFF route which handles auth via httpOnly cookie
      const response = await fetch('/api/accounts');

      if (response.ok) {
        const data = await response.json();
        // Backend returns {accounts: [], total}
        setAccounts(data.accounts || data || []);
      }
    } catch (error) {
      console.error('Failed to load accounts:', error);
    }
  };
  
  const callApi = async (endpoint: string, method: string = 'GET', body?: any) => {
    if (!selectedBroker || !selectedAccountId) {
      toast({
        title: 'Error',
        description: 'Please select a broker and account',
        variant: 'destructive',
      });
      return;
    }

    const key = endpoint.split('?')[0].split('/').pop() || endpoint;
    setLoading(key);

    try {
      // Use BFF proxy which handles auth via httpOnly cookie
      const response = await fetch('/api/broker-tools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          endpoint,
          method,
          body: method !== 'GET' ? body : undefined,
        }),
      });

      const data = await response.json();

      setResults(prev => ({
        ...prev,
        [key]: { success: response.ok, data, status: response.status },
      }));

      if (response.ok) {
        toast({
          title: 'Success',
          description: `API call successful`,
        });
      } else {
        toast({
          title: 'Error',
          description: data.detail || data.error || `API call failed: ${response.status}`,
          variant: 'destructive',
        });
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'API call failed';
      setResults(prev => ({ ...prev, [key]: { success: false, error: message } }));
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setLoading(null);
    }
  };
  
  const filteredAccounts = selectedBroker
    ? accounts.filter(acc => acc.broker === selectedBroker)
    : [];
  
  const brokers = Array.from(new Set(accounts.map(acc => acc.broker)));
  
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Broker Tools</h1>
        <p className="text-muted-foreground mt-2">
          Test and interact with broker SDK features
        </p>
      </div>
      
      {/* Broker & Account Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Broker & Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Broker</Label>
              <Select value={selectedBroker} onValueChange={setSelectedBroker}>
                <SelectTrigger>
                  <SelectValue placeholder="Select broker" />
                </SelectTrigger>
                <SelectContent>
                  {brokers.map(broker => (
                    <SelectItem key={broker} value={broker}>
                      {broker}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Account</Label>
              <Select
                value={selectedAccountId?.toString() || ''}
                onValueChange={(v) => setSelectedAccountId(v ? parseInt(v) : null)}
                disabled={!selectedBroker}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select account" />
                </SelectTrigger>
                <SelectContent>
                  {filteredAccounts.map(acc => (
                    <SelectItem key={acc.id} value={acc.id.toString()}>
                      {acc.account_id} ({acc.broker})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label>Symbol</Label>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="e.g., MNQ, MES"
            />
          </div>
        </CardContent>
      </Card>
      
      {selectedBroker && selectedAccountId && (
        <Tabs defaultValue="accounts" className="space-y-4">
          <TabsList>
            <TabsTrigger value="accounts">Accounts</TabsTrigger>
            <TabsTrigger value="positions">Positions</TabsTrigger>
            <TabsTrigger value="orders">Orders</TabsTrigger>
            <TabsTrigger value="market">Market Data</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>
          
          <TabsContent value="accounts" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Account Operations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button
                  onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/accounts?account_id=${selectedAccountId}`)}
                  disabled={loading === 'accounts'}
                >
                  {loading === 'accounts' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Get Accounts
                </Button>
                {results['accounts'] && (
                  <Textarea
                    readOnly
                    value={JSON.stringify(results['accounts'].data, null, 2)}
                    className="font-mono text-xs mt-2"
                    rows={10}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="positions" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Position Operations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex gap-2">
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/positions?account_id=${selectedAccountId}`)}
                    disabled={loading === 'positions'}
                  >
                    {loading === 'positions' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Get Positions
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/positions/history?account_id=${selectedAccountId}&symbol=${symbol}&days=30`)}
                    disabled={loading === 'positions/history'}
                  >
                    {loading === 'positions/history' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Position History
                  </Button>
                </div>
                {(results['positions'] || results['positions/history']) && (
                  <Textarea
                    readOnly
                    value={JSON.stringify(
                      results['positions']?.data || results['positions/history']?.data,
                      null,
                      2
                    )}
                    className="font-mono text-xs mt-2"
                    rows={10}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="orders" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Order Operations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex gap-2 flex-wrap">
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/orders?account_id=${selectedAccountId}`)}
                    disabled={loading === 'orders'}
                  >
                    {loading === 'orders' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Get Orders
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/orders?account_id=${selectedAccountId}`, 'DELETE')}
                    disabled={loading === 'orders'}
                    variant="destructive"
                  >
                    Cancel All Orders
                  </Button>
                </div>
                {results['orders'] && (
                  <Textarea
                    readOnly
                    value={JSON.stringify(results['orders'].data, null, 2)}
                    className="font-mono text-xs mt-2"
                    rows={10}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="market" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Market Data</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex gap-2 flex-wrap">
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/market/quote?account_id=${selectedAccountId}&symbol=${symbol}`)}
                    disabled={loading === 'quote'}
                  >
                    {loading === 'quote' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Get Quote
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/market/history?account_id=${selectedAccountId}&symbol=${symbol}&days=1&interval=5`)}
                    disabled={loading === 'history'}
                  >
                    {loading === 'history' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Price History
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/market/orderbook?account_id=${selectedAccountId}&symbol=${symbol}&depth=10`)}
                    disabled={loading === 'orderbook'}
                  >
                    {loading === 'orderbook' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Orderbook
                  </Button>
                </div>
                {(results['quote'] || results['history'] || results['orderbook']) && (
                  <Textarea
                    readOnly
                    value={JSON.stringify(
                      results['quote']?.data || results['history']?.data || results['orderbook']?.data,
                      null,
                      2
                    )}
                    className="font-mono text-xs mt-2"
                    rows={10}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="analytics" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Analytics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex gap-2 flex-wrap">
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/stats/session?account_id=${selectedAccountId}&symbol=${symbol}`)}
                    disabled={loading === 'session'}
                  >
                    {loading === 'session' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Session Stats
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/stats/performance?account_id=${selectedAccountId}&symbol=${symbol}`)}
                    disabled={loading === 'performance'}
                  >
                    {loading === 'performance' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Performance Stats
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/stats/portfolio?account_id=${selectedAccountId}`)}
                    disabled={loading === 'portfolio'}
                  >
                    {loading === 'portfolio' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Portfolio Metrics
                  </Button>
                </div>
                {(results['session'] || results['performance'] || results['portfolio']) && (
                  <Textarea
                    readOnly
                    value={JSON.stringify(
                      results['session']?.data || results['performance']?.data || results['portfolio']?.data,
                      null,
                      2
                    )}
                    className="font-mono text-xs mt-2"
                    rows={10}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
