import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Loader2, ArrowLeft, Download } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface SyncResult {
  account_id: string;
  account_number: string;
  broker: string;
  status: 'success' | 'failed' | 'partial';
  message: string;
  synced_at: string;
  items_synced?: number;
  errors?: string[];
}

interface SyncResultsPageProps {
  onBack: () => void;
  onRetry?: (accountId: string) => void;
}

export function SyncResultsPage({ onBack, onRetry }: SyncResultsPageProps) {
  const [results, setResults] = useState<SyncResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);

  useEffect(() => {
    fetchSyncResults();
  }, []);

  const fetchSyncResults = async () => {
    setLoading(true);
    try {
      // Mock data - replace with real API call
      const mockResults: SyncResult[] = [
        {
          account_id: '1',
          account_number: 'PA-123456',
          broker: 'Topstep',
          status: 'success',
          message: 'Successfully synced all positions and orders',
          synced_at: '2025-10-18T10:30:00Z',
          items_synced: 15
        },
        {
          account_id: '2',
          account_number: 'TL-789012',
          broker: 'TradeLocker',
          status: 'success',
          message: 'Account data synchronized',
          synced_at: '2025-10-18T10:29:45Z',
          items_synced: 8
        },
        {
          account_id: '3',
          account_number: 'MT4-456789',
          broker: 'MT4',
          status: 'failed',
          message: 'Connection timeout',
          synced_at: '2025-10-18T10:29:30Z',
          errors: ['Failed to connect to MT4 server', 'Connection timeout after 30s']
        },
        {
          account_id: '4',
          account_number: 'PA-345678',
          broker: 'Topstep',
          status: 'partial',
          message: 'Some items failed to sync',
          synced_at: '2025-10-18T10:29:15Z',
          items_synced: 5,
          errors: ['Failed to sync 2 pending orders']
        }
      ];
      
      setTimeout(() => {
        setResults(mockResults);
        setLoading(false);
      }, 800);
    } catch (error) {
      toast.error('Failed to load sync results');
      setLoading(false);
    }
  };

  const handleRetrySync = async (accountId: string) => {
    setRetrying(accountId);
    try {
      // Replace with real API call
      // await apiClient.post(`/api/accounts/sync/${accountId}`);
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      toast.success('Sync retry initiated');
      fetchSyncResults();
    } catch (error) {
      toast.error('Failed to retry sync');
    } finally {
      setRetrying(null);
    }
  };

  const handleExportResults = () => {
    const csvContent = [
      ['Account', 'Broker', 'Status', 'Message', 'Items Synced', 'Synced At'],
      ...results.map(r => [
        r.account_number,
        r.broker,
        r.status,
        r.message,
        r.items_synced?.toString() || 'N/A',
        new Date(r.synced_at).toLocaleString()
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sync-results-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    toast.success('Results exported');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'partial':
        return <AlertCircle className="w-5 h-5 text-amber-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return <Badge className="bg-green-100 text-green-700 border-green-200">Success</Badge>;
      case 'failed':
        return <Badge className="bg-red-100 text-red-700 border-red-200">Failed</Badge>;
      case 'partial':
        return <Badge className="bg-amber-100 text-amber-700 border-amber-200">Partial</Badge>;
      default:
        return null;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const successCount = results.filter(r => r.status === 'success').length;
  const failedCount = results.filter(r => r.status === 'failed').length;
  const partialCount = results.filter(r => r.status === 'partial').length;

  const overallStatus = failedCount > 0 ? 'error' : partialCount > 0 ? 'warning' : 'success';

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading sync results...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={onBack}
            className="mb-4 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Accounts
          </Button>
          
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-semibold mb-2">Account Sync Results</h1>
              <p className="text-muted-foreground">
                Review synchronization status for all connected accounts
              </p>
            </div>
            <Button
              variant="outline"
              onClick={handleExportResults}
              className="gap-2"
            >
              <Download className="w-4 h-4" />
              Export
            </Button>
          </div>
        </div>

        {/* Status Banner */}
        {overallStatus === 'success' && (
          <Alert className="mb-6 bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800">
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            <AlertDescription className="text-green-800 dark:text-green-200">
              <strong>Sync completed successfully!</strong> All {results.length} accounts synchronized without errors.
            </AlertDescription>
          </Alert>
        )}

        {overallStatus === 'warning' && (
          <Alert className="mb-6 bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800">
            <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <AlertDescription className="text-amber-800 dark:text-amber-200">
              <strong>Sync completed with warnings.</strong> Some accounts had partial synchronization.
            </AlertDescription>
          </Alert>
        )}

        {overallStatus === 'error' && (
          <Alert className="mb-6 bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800">
            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <AlertDescription className="text-red-800 dark:text-red-200">
              <strong>Sync failed for some accounts.</strong> {failedCount} account{failedCount !== 1 ? 's' : ''} failed to synchronize.
            </AlertDescription>
          </Alert>
        )}

        {/* Summary Cards */}
        <div className="grid md:grid-cols-3 gap-4 mb-6">
          <Card className="border-2 border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <CheckCircle className="w-8 h-8 text-green-500" />
                <span className="text-3xl font-bold text-green-700 dark:text-green-400">
                  {successCount}
                </span>
              </div>
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                Successful
              </p>
              <p className="text-xs text-green-600 dark:text-green-300 mt-1">
                All data synced
              </p>
            </CardContent>
          </Card>

          <Card className="border-2 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <AlertCircle className="w-8 h-8 text-amber-500" />
                <span className="text-3xl font-bold text-amber-700 dark:text-amber-400">
                  {partialCount}
                </span>
              </div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                Partial
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-300 mt-1">
                Some items failed
              </p>
            </CardContent>
          </Card>

          <Card className="border-2 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <XCircle className="w-8 h-8 text-red-500" />
                <span className="text-3xl font-bold text-red-700 dark:text-red-400">
                  {failedCount}
                </span>
              </div>
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Failed
              </p>
              <p className="text-xs text-red-600 dark:text-red-300 mt-1">
                Sync errors
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Results Table */}
        <Card>
          <CardHeader>
            <CardTitle>Detailed Results</CardTitle>
            <CardDescription>
              Individual sync status for each account
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="w-12"></TableHead>
                    <TableHead>Account</TableHead>
                    <TableHead>Broker</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Items Synced</TableHead>
                    <TableHead>Timestamp</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((result) => (
                    <React.Fragment key={result.account_id}>
                      <TableRow className="group">
                        <TableCell>{getStatusIcon(result.status)}</TableCell>
                        <TableCell className="font-semibold">
                          {result.account_number}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {result.broker}
                        </TableCell>
                        <TableCell>{getStatusBadge(result.status)}</TableCell>
                        <TableCell>
                          {result.items_synced !== undefined ? (
                            <span className="font-medium">{result.items_synced}</span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(result.synced_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          {result.status === 'failed' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRetrySync(result.account_id)}
                              disabled={retrying === result.account_id}
                              className="gap-2"
                            >
                              {retrying === result.account_id ? (
                                <>
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                  Retrying...
                                </>
                              ) : (
                                <>
                                  <RefreshCw className="w-3 h-3" />
                                  Retry
                                </>
                              )}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                      {/* Error details row */}
                      {(result.errors && result.errors.length > 0) && (
                        <TableRow className="bg-red-50 dark:bg-red-950/20">
                          <TableCell colSpan={7} className="p-0">
                            <div className="px-14 py-3 text-sm">
                              <p className="font-medium text-red-700 dark:text-red-300 mb-2">
                                {result.message}
                              </p>
                              <ul className="list-disc list-inside space-y-1 text-red-600 dark:text-red-400">
                                {result.errors.map((error, idx) => (
                                  <li key={idx}>{error}</li>
                                ))}
                              </ul>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="mt-6 flex justify-between">
          <Button variant="outline" onClick={onBack}>
            Return to Accounts
          </Button>
          {failedCount > 0 && (
            <Button
              onClick={() => toast.info('Retry all feature coming soon')}
              className="gap-2 bg-primary hover:bg-primary/90"
            >
              <RefreshCw className="w-4 h-4" />
              Retry All Failed
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
