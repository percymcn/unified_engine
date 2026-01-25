'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, CheckCircle2, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Account } from '@/types/account';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export default function BrokerToolsPage() {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedBroker, setSelectedBroker] = useState<string>('');
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});
  const [symbol, setSymbol] = useState('MNQ');
  const [balance, setBalance] = useState<any | null>(null);
  const [positions, setPositions] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [quote, setQuote] = useState<any | null>(null);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [orderType, setOrderType] = useState<'market' | 'limit' | 'stop'>('market');
  const [orderQuantity, setOrderQuantity] = useState('1');
  const [orderPrice, setOrderPrice] = useState('');
  const [orderStopLoss, setOrderStopLoss] = useState('');
  const [orderTakeProfit, setOrderTakeProfit] = useState('');
  const [selectedPositionId, setSelectedPositionId] = useState<string>('');
  const [closeQuantity, setCloseQuantity] = useState('');
  const [modifyStopLoss, setModifyStopLoss] = useState('');
  const [modifyTakeProfit, setModifyTakeProfit] = useState('');
  
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
    if (!canUseTools) {
      toast({
        title: 'Missing credentials',
        description: 'Update broker credentials in Accounts settings to use Broker Tools.',
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

      const data = await response.json().catch(() => ({}));

      setResults(prev => ({
        ...prev,
        [key]: { success: response.ok, data, status: response.status },
      }));

      if (response.ok) {
        toast({
          title: 'Success',
          description: `API call successful`,
        });
        return data;
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

  const fetchBalance = async () => {
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/balance?account_id=${selectedAccountId}`);
    if (data) {
      setBalance(data);
    }
  };

  const fetchPositions = async () => {
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/positions?account_id=${selectedAccountId}`);
    if (Array.isArray(data)) {
      setPositions(data);
    }
  };

  const fetchOrders = async () => {
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/orders?account_id=${selectedAccountId}`);
    if (Array.isArray(data)) {
      setOrders(data);
    }
  };

  const fetchHistory = async () => {
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/history?account_id=${selectedAccountId}&days=30&symbol=${symbol}`);
    if (Array.isArray(data)) {
      setHistory(data);
    }
  };

  const fetchQuote = async () => {
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/quotes/${encodeURIComponent(symbol)}?account_id=${selectedAccountId}`);
    if (data) {
      setQuote(data);
    }
  };

  const fetchSymbols = async () => {
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/symbols?account_id=${selectedAccountId}`);
    if (Array.isArray(data)) {
      setSymbols(data);
    }
  };

  const handlePlaceOrder = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedBroker || !selectedAccountId || !canUseTools) {
      return;
    }

    const payload: Record<string, any> = {
      account_id: selectedAccountId,
      symbol,
      side: orderSide,
      order_type: orderType,
      quantity: parseFloat(orderQuantity),
    };

    if (orderType !== 'market' && orderPrice) {
      payload.price = parseFloat(orderPrice);
    }
    if (orderStopLoss) {
      payload.stop_loss = parseFloat(orderStopLoss);
    }
    if (orderTakeProfit) {
      payload.take_profit = parseFloat(orderTakeProfit);
    }

    const data = await callApi(`/api/v1/brokers/${selectedBroker}/orders`, 'POST', payload);
    if (data) {
      await fetchOrders();
      await fetchPositions();
    }
  };

  const handleClosePosition = async (positionId: string) => {
    if (!canUseTools) {
      return;
    }
    const payload: Record<string, any> = { account_id: selectedAccountId };
    if (closeQuantity) {
      payload.quantity = parseFloat(closeQuantity);
    }
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/positions/${positionId}/close`, 'POST', payload);
    if (data) {
      await fetchPositions();
    }
  };

  const handleModifyPosition = async () => {
    if (!selectedPositionId) {
      toast({
        title: 'Select a position',
        description: 'Choose a position before updating SL/TP.',
        variant: 'destructive',
      });
      return;
    }
    if (!canUseTools) {
      return;
    }

    const payload: Record<string, any> = { account_id: selectedAccountId };
    if (modifyStopLoss) {
      payload.stop_loss = parseFloat(modifyStopLoss);
    }
    if (modifyTakeProfit) {
      payload.take_profit = parseFloat(modifyTakeProfit);
    }

    const data = await callApi(`/api/v1/brokers/${selectedBroker}/positions/${selectedPositionId}`, 'PATCH', payload);
    if (data) {
      await fetchPositions();
    }
  };

  const handleCancelOrder = async (orderId: string) => {
    if (!canUseTools) {
      return;
    }
    const data = await callApi(`/api/v1/brokers/${selectedBroker}/orders/${orderId}?account_id=${selectedAccountId}`, 'DELETE');
    if (data !== undefined) {
      await fetchOrders();
    }
  };
  
  const filteredAccounts = selectedBroker
    ? accounts.filter(acc => acc.broker === selectedBroker)
    : [];
  
  const brokers = Array.from(new Set(accounts.map(acc => acc.broker)));
  const selectedAccount = accounts.find((acc) => acc.id === selectedAccountId);
  const hasCredentials = selectedAccount ? selectedAccount.is_connected : false;
  const canUseTools = Boolean(selectedAccountId && hasCredentials);
  
  useEffect(() => {
    if (!selectedBroker && brokers.length > 0) {
      const preferred = brokers.includes('tradelocker') ? 'tradelocker' : brokers[0];
      setSelectedBroker(preferred);
    }
  }, [brokers, selectedBroker]);

  useEffect(() => {
    if (selectedBroker && filteredAccounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(filteredAccounts[0].id);
    }
  }, [selectedBroker, filteredAccounts, selectedAccountId]);

  useEffect(() => {
    setBalance(null);
    setPositions([]);
    setOrders([]);
    setHistory([]);
    setQuote(null);
    setSymbols([]);
    setSelectedPositionId('');
  }, [selectedBroker, selectedAccountId]);

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
              <Select
                value={selectedBroker}
                onValueChange={(value) => {
                  setSelectedBroker(value);
                  setSelectedAccountId(null);
                }}
              >
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
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>
          
          <TabsContent value="accounts" className="space-y-4">
            {!hasCredentials && (
              <Alert>
                <AlertTitle>Broker credentials needed</AlertTitle>
                <AlertDescription>
                  This account is not connected. Update credentials in Settings → Accounts, then sync to enable Broker Tools.
                </AlertDescription>
              </Alert>
            )}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Balance Snapshot</CardTitle>
                  <CardDescription>Latest balance and equity values</CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={fetchBalance} disabled={!canUseTools}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {balance ? (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Balance</div>
                      <div className="text-xl font-semibold">{balance.balance}</div>
                    </div>
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Equity</div>
                      <div className="text-xl font-semibold">{balance.equity}</div>
                    </div>
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Free Margin</div>
                      <div className="text-xl font-semibold">{balance.free_margin}</div>
                    </div>
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Leverage</div>
                      <div className="text-xl font-semibold">1:{balance.leverage}</div>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">
                    Click refresh to load balance information.
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Account Operations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button
                  onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/accounts?account_id=${selectedAccountId}`)}
                  disabled={!canUseTools || loading === 'accounts'}
                >
                  {loading === 'accounts' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Get Accounts
                </Button>
                {Array.isArray(results['accounts']?.data) && (
                  <div className="mt-4 rounded-lg border border-border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead className="text-right">Balance</TableHead>
                          <TableHead className="text-right">Equity</TableHead>
                          <TableHead>Currency</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {results['accounts'].data.map((acc: any) => (
                          <TableRow key={acc.account_id}>
                            <TableCell className="font-mono text-xs">{acc.account_id}</TableCell>
                            <TableCell>{acc.account_type}</TableCell>
                            <TableCell className="text-right">{acc.balance}</TableCell>
                            <TableCell className="text-right">{acc.equity}</TableCell>
                            <TableCell>{acc.currency}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
                {results['accounts'] && (
                  <Textarea
                    readOnly
                    value={JSON.stringify(results['accounts'].data, null, 2)}
                    className="font-mono text-xs mt-4"
                    rows={8}
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
                    onClick={fetchPositions}
                    disabled={!canUseTools || loading === 'positions'}
                  >
                    {loading === 'positions' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Get Positions
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/positions/history?account_id=${selectedAccountId}&symbol=${symbol}&days=30`)}
                    disabled={!canUseTools || loading === 'positions/history'}
                  >
                    {loading === 'positions/history' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Position History
                  </Button>
                </div>
                {positions.length > 0 ? (
                  <div className="mt-4 rounded-lg border border-border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead className="text-right">Size</TableHead>
                          <TableHead className="text-right">Entry</TableHead>
                          <TableHead className="text-right">PnL</TableHead>
                          <TableHead>SL/TP</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {positions.map((pos: any) => (
                          <TableRow key={pos.position_id}>
                            <TableCell className="font-medium">{pos.symbol}</TableCell>
                            <TableCell className="uppercase">{pos.side}</TableCell>
                            <TableCell className="text-right">{pos.size}</TableCell>
                            <TableCell className="text-right">{pos.entry_price}</TableCell>
                            <TableCell className="text-right">{pos.unrealized_pnl}</TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              SL {pos.stop_loss ?? '-'} / TP {pos.take_profit ?? '-'}
                            </TableCell>
                            <TableCell className="text-right space-x-2">
                              <Button size="sm" variant="outline" onClick={() => {
                                setSelectedPositionId(pos.position_id);
                                setModifyStopLoss(pos.stop_loss ? String(pos.stop_loss) : '');
                                setModifyTakeProfit(pos.take_profit ? String(pos.take_profit) : '');
                              }}>
                                Edit SL/TP
                              </Button>
                              <Button size="sm" variant="destructive" onClick={() => handleClosePosition(pos.position_id)}>
                                Close
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground mt-4">
                    No open positions loaded yet.
                  </div>
                )}
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Close Quantity (optional)</Label>
                    <Input
                      value={closeQuantity}
                      onChange={(e) => setCloseQuantity(e.target.value)}
                      placeholder="e.g., 0.5"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Modify SL/TP for Position</Label>
                    <Select value={selectedPositionId} onValueChange={setSelectedPositionId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select position" />
                      </SelectTrigger>
                      <SelectContent>
                        {positions.map((pos: any) => (
                          <SelectItem key={pos.position_id} value={pos.position_id}>
                            {pos.symbol} ({pos.position_id})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Stop Loss</Label>
                    <Input
                      value={modifyStopLoss}
                      onChange={(e) => setModifyStopLoss(e.target.value)}
                      placeholder="e.g., 20150"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Take Profit</Label>
                    <Input
                      value={modifyTakeProfit}
                      onChange={(e) => setModifyTakeProfit(e.target.value)}
                      placeholder="e.g., 20350"
                    />
                  </div>
                  <div className="md:col-span-2">
                  <Button onClick={handleModifyPosition} variant="secondary" disabled={!canUseTools}>
                    Update SL/TP
                  </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="orders" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Order Operations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={handlePlaceOrder} className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label>Side</Label>
                    <Select value={orderSide} onValueChange={(value) => setOrderSide(value as 'buy' | 'sell')}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="buy">Buy</SelectItem>
                        <SelectItem value="sell">Sell</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Order Type</Label>
                    <Select value={orderType} onValueChange={(value) => setOrderType(value as 'market' | 'limit' | 'stop')}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="market">Market</SelectItem>
                        <SelectItem value="limit">Limit</SelectItem>
                        <SelectItem value="stop">Stop</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Quantity</Label>
                    <Input value={orderQuantity} onChange={(e) => setOrderQuantity(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>Price</Label>
                    <Input
                      value={orderPrice}
                      onChange={(e) => setOrderPrice(e.target.value)}
                      placeholder={orderType === 'market' ? 'Market price' : 'Limit/Stop price'}
                      disabled={orderType === 'market'}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Stop Loss</Label>
                    <Input value={orderStopLoss} onChange={(e) => setOrderStopLoss(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>Take Profit</Label>
                    <Input value={orderTakeProfit} onChange={(e) => setOrderTakeProfit(e.target.value)} />
                  </div>
                  <div className="md:col-span-3">
                    <Button type="submit" disabled={!canUseTools}>
                      Place Order
                    </Button>
                  </div>
                </form>
                <div className="flex gap-2 flex-wrap">
                  <Button
                    onClick={fetchOrders}
                    disabled={!canUseTools || loading === 'orders'}
                  >
                    {loading === 'orders' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Get Orders
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/orders?account_id=${selectedAccountId}`, 'DELETE')}
                    disabled={!canUseTools || loading === 'orders'}
                    variant="destructive"
                  >
                    Cancel All Orders
                  </Button>
                </div>
                {orders.length > 0 ? (
                  <div className="mt-4 rounded-lg border border-border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead className="text-right">Qty</TableHead>
                          <TableHead className="text-right">Price</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {orders.map((order: any) => (
                          <TableRow key={order.order_id}>
                            <TableCell className="font-medium">{order.symbol}</TableCell>
                            <TableCell className="uppercase">{order.side}</TableCell>
                            <TableCell>{order.order_type}</TableCell>
                            <TableCell className="text-right">{order.quantity}</TableCell>
                            <TableCell className="text-right">{order.price ?? '-'}</TableCell>
                            <TableCell>{order.status}</TableCell>
                            <TableCell className="text-right">
                              <Button size="sm" variant="outline" onClick={() => handleCancelOrder(order.order_id)}>
                                Cancel
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground mt-4">
                    No open orders loaded yet.
                  </div>
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
                    onClick={fetchQuote}
                    disabled={!canUseTools || loading === 'quote'}
                  >
                    {loading === 'quote' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Get Quote
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/market/history?account_id=${selectedAccountId}&symbol=${symbol}&days=1&interval=5`)}
                    disabled={!canUseTools || loading === 'history'}
                  >
                    {loading === 'history' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Price History
                  </Button>
                  <Button
                    onClick={() => callApi(`/api/v1/brokers/${selectedBroker}/market/orderbook?account_id=${selectedAccountId}&symbol=${symbol}&depth=10`)}
                    disabled={!canUseTools || loading === 'orderbook'}
                  >
                    {loading === 'orderbook' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Orderbook
                  </Button>
                  <Button
                    onClick={fetchSymbols}
                    disabled={!canUseTools || loading === 'symbols'}
                    variant="secondary"
                  >
                    {loading === 'symbols' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Symbols
                  </Button>
                </div>
                {quote && (
                  <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Bid</div>
                      <div className="text-xl font-semibold">{quote.bid}</div>
                    </div>
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Ask</div>
                      <div className="text-xl font-semibold">{quote.ask}</div>
                    </div>
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Last</div>
                      <div className="text-xl font-semibold">{quote.last ?? '-'}</div>
                    </div>
                    <div className="rounded-lg border border-border p-4">
                      <div className="text-xs text-muted-foreground">Volume</div>
                      <div className="text-xl font-semibold">{quote.volume ?? '-'}</div>
                    </div>
                  </div>
                )}
                {symbols.length > 0 && (
                  <div className="mt-4 rounded-lg border border-border p-4">
                    <div className="text-sm font-medium mb-2">Symbols ({symbols.length})</div>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-xs text-muted-foreground">
                      {symbols.slice(0, 32).map((sym) => (
                        <div key={sym} className="rounded-md border border-border px-2 py-1">
                          {sym}
                        </div>
                      ))}
                    </div>
                    {symbols.length > 32 && (
                      <div className="text-xs text-muted-foreground mt-2">
                        Showing first 32 symbols. Use search/filter in future update.
                      </div>
                    )}
                  </div>
                )}
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

          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Trade History</CardTitle>
                <CardDescription>Closed positions and deal history</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button onClick={fetchHistory} disabled={!canUseTools || loading === 'history'}>
                  {loading === 'history' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Fetch History
                </Button>
                {history.length > 0 ? (
                  <div className="mt-4 rounded-lg border border-border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead className="text-right">Size</TableHead>
                          <TableHead className="text-right">Entry</TableHead>
                          <TableHead className="text-right">PnL</TableHead>
                          <TableHead>Closed</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {history.map((item: any, index: number) => (
                          <TableRow key={`${item.position_id}-${index}`}>
                            <TableCell>{item.symbol}</TableCell>
                            <TableCell className="uppercase">{item.side}</TableCell>
                            <TableCell className="text-right">{item.size}</TableCell>
                            <TableCell className="text-right">{item.entry_price}</TableCell>
                            <TableCell className="text-right">{item.realized_pnl ?? item.unrealized_pnl}</TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {item.closed_at ?? '-'}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground mt-4">
                    No history loaded yet.
                  </div>
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
