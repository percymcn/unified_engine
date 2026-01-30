'use client';

import { useState, useCallback, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  BarChart3,
  Code2,
  Brain,
  LineChart,
  Sparkles,
  ArrowLeft,
  Settings,
  Save,
  Share2,
  Lock,
  Wand2,
  Check,
  Copy,
  Download,
  FolderOpen,
} from 'lucide-react';
import Link from 'next/link';
import {
  TradingViewChart,
  PineScriptEditor,
  BacktestEngine,
  AICoach,
  ScriptConverter,
} from '@/features/ai-suite';
import type { BacktestResults, WebhookPayload } from '@/features/ai-suite/types';
import { useUser } from '@/providers/user-provider';
import { hasFeatureAccess, FEATURES, normalizeTier } from '@/lib/feature-flags';

export default function AIStrategyPage() {
  const { user } = useUser();
  const rawTier = user?.subscription_tier || 'free';
  const userTier = normalizeTier(rawTier);
  const hasAccess = hasFeatureAccess(rawTier, 'AI_SUITE');
  const [pineCode, setPineCode] = useState('');
  const [backtestResults, setBacktestResults] = useState<BacktestResults | null>(null);
  const [webhookPayload, setWebhookPayload] = useState<WebhookPayload | null>(null);
  const [activeTab, setActiveTab] = useState('chart');
  const [selectedSymbol, setSelectedSymbol] = useState('EURUSD');

  // Dialog states
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [strategyName, setStrategyName] = useState('');
  const [savedStrategies, setSavedStrategies] = useState<Array<{name: string; code: string; savedAt: string}>>([]);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);

  // Settings state
  const [settings, setSettings] = useState({
    defaultSymbol: 'EURUSD',
    defaultTimeframe: '60',
    autoSave: false,
    darkTheme: true,
  });

  // Load saved strategies on mount
  useEffect(() => {
    const stored = localStorage.getItem('tradeflow-strategies');
    if (stored) {
      setSavedStrategies(JSON.parse(stored));
    }
    const storedSettings = localStorage.getItem('tradeflow-ai-suite-settings');
    if (storedSettings) {
      setSettings(JSON.parse(storedSettings));
    }
  }, []);

  const handleCodeChange = useCallback((code: string) => {
    setPineCode(code);
  }, []);

  const handleBacktestResults = useCallback((results: BacktestResults | null) => {
    setBacktestResults(results);
  }, []);

  const { toast } = useToast();

  // Open save dialog
  const handleSaveStrategy = useCallback(() => {
    if (!pineCode.trim()) {
      toast({
        title: 'Nothing to Save',
        description: 'Please enter some code in the editor first.',
        variant: 'destructive',
      });
      return;
    }
    setStrategyName(`Strategy ${savedStrategies.length + 1}`);
    setSaveDialogOpen(true);
  }, [pineCode, savedStrategies.length, toast]);

  // Actually save the strategy
  const confirmSaveStrategy = useCallback(() => {
    const strategyData = {
      name: strategyName || `Strategy ${savedStrategies.length + 1}`,
      code: pineCode,
      symbol: selectedSymbol,
      savedAt: new Date().toISOString(),
      backtestResults: backtestResults,
    };

    const updated = [...savedStrategies, strategyData];
    setSavedStrategies(updated);
    localStorage.setItem('tradeflow-strategies', JSON.stringify(updated));
    setSaveDialogOpen(false);

    toast({
      title: 'Strategy Saved!',
      description: `"${strategyData.name}" has been saved. You now have ${updated.length} saved strategies.`,
    });
  }, [strategyName, pineCode, selectedSymbol, backtestResults, savedStrategies, toast]);

  // Load a saved strategy
  const loadStrategy = useCallback((strategy: typeof savedStrategies[0]) => {
    setPineCode(strategy.code);
    setLoadDialogOpen(false);
    toast({
      title: 'Strategy Loaded',
      description: `"${strategy.name}" has been loaded into the editor.`,
    });
  }, [toast]);

  // Delete a saved strategy
  const deleteStrategy = useCallback((index: number) => {
    const updated = savedStrategies.filter((_, i) => i !== index);
    setSavedStrategies(updated);
    localStorage.setItem('tradeflow-strategies', JSON.stringify(updated));
    toast({
      title: 'Strategy Deleted',
      description: 'The strategy has been removed.',
    });
  }, [savedStrategies, toast]);

  // Open share dialog
  const handleShareStrategy = useCallback(() => {
    if (!pineCode.trim()) {
      toast({
        title: 'Nothing to Share',
        description: 'Please enter some code in the editor first.',
        variant: 'destructive',
      });
      return;
    }
    setShareDialogOpen(true);
  }, [pineCode, toast]);

  // Copy code to clipboard
  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(pineCode);
      toast({
        title: 'Copied!',
        description: 'Pine Script code copied to clipboard.',
      });
    } catch {
      toast({
        title: 'Copy Failed',
        description: 'Could not copy to clipboard.',
        variant: 'destructive',
      });
    }
  }, [pineCode, toast]);

  // Download as file
  const downloadAsFile = useCallback(() => {
    const blob = new Blob([pineCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${strategyName || 'strategy'}.pine`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast({
      title: 'Downloaded!',
      description: 'Pine Script saved as .pine file.',
    });
  }, [pineCode, strategyName, toast]);

  // Open settings dialog
  const handleOpenSettings = useCallback(() => {
    setSettingsDialogOpen(true);
  }, []);

  // Save settings
  const saveSettings = useCallback(() => {
    localStorage.setItem('tradeflow-ai-suite-settings', JSON.stringify(settings));
    setSettingsDialogOpen(false);
    toast({
      title: 'Settings Saved',
      description: 'Your preferences have been updated.',
    });
  }, [settings, toast]);

  const handleWebhookGenerated = useCallback((payload: WebhookPayload) => {
    setWebhookPayload(payload);
  }, []);

  // Handle applying AI suggestions to the code
  const handleApplySuggestion = useCallback((codeSnippet: string) => {
    setPineCode((prevCode) => {
      // Add a newline separator and append the suggestion
      const separator = prevCode.trim() ? '\n\n// === AI Coach Suggestion ===\n' : '';
      return prevCode + separator + codeSnippet;
    });
  }, []);

  // Show upgrade prompt for users without Pro tier
  if (!hasAccess) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="max-w-lg w-full">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Lock className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="flex items-center justify-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI Strategy Suite
              <Badge variant="secondary">Pro</Badge>
            </CardTitle>
            <CardDescription className="mt-2">
              {FEATURES.AI_SUITE.description}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Code2 className="h-4 w-4 text-muted-foreground" />
                <span>Pine Script AI Fixer</span>
              </div>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
                <span>Backtest Engine</span>
              </div>
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-muted-foreground" />
                <span>AI Trading Coach</span>
              </div>
              <div className="flex items-center gap-2">
                <LineChart className="h-4 w-4 text-muted-foreground" />
                <span>Live Charts</span>
              </div>
              <div className="flex items-center gap-2 col-span-2">
                <Wand2 className="h-4 w-4 text-muted-foreground" />
                <span>Script to TradeFlow Converter</span>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <Link href="/dashboard/settings/billing">
                <Button className="w-full">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Upgrade to Pro
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="outline" className="w-full">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
            </div>
            <p className="text-xs text-muted-foreground text-center">
              Current plan: <span className="font-medium capitalize">{userTier}</span>
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <h1 className="text-lg font-semibold">AI Strategy Suite</h1>
              <Badge variant="secondary" className="text-xs">
                Beta
              </Badge>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {savedStrategies.length > 0 && (
              <Button variant="outline" size="sm" onClick={() => setLoadDialogOpen(true)}>
                <FolderOpen className="h-4 w-4 mr-2" />
                Load ({savedStrategies.length})
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={handleSaveStrategy}>
              <Save className="h-4 w-4 mr-2" />
              Save
            </Button>
            <Button variant="outline" size="sm" onClick={handleShareStrategy}>
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </Button>
            <Button variant="ghost" size="sm" onClick={handleOpenSettings}>
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5 lg:w-auto lg:inline-grid">
            <TabsTrigger value="chart" className="gap-2">
              <LineChart className="h-4 w-4" />
              <span className="hidden sm:inline">Chart</span>
            </TabsTrigger>
            <TabsTrigger value="editor" className="gap-2">
              <Code2 className="h-4 w-4" />
              <span className="hidden sm:inline">Editor</span>
            </TabsTrigger>
            <TabsTrigger value="backtest" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Backtest</span>
            </TabsTrigger>
            <TabsTrigger value="coach" className="gap-2">
              <Brain className="h-4 w-4" />
              <span className="hidden sm:inline">AI Coach</span>
            </TabsTrigger>
            <TabsTrigger value="converter" className="gap-2">
              <Wand2 className="h-4 w-4" />
              <span className="hidden sm:inline">Converter</span>
            </TabsTrigger>
          </TabsList>

          {/* Chart Tab */}
          <TabsContent value="chart" className="space-y-4">
            <TradingViewChart
              symbol={selectedSymbol}
              onSymbolChange={setSelectedSymbol}
              className="w-full min-h-[600px] h-[calc(100vh-200px)]"
            />
          </TabsContent>

          {/* Editor Tab */}
          <TabsContent value="editor" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PineScriptEditor
                onCodeChange={handleCodeChange}
                onWebhookGenerated={handleWebhookGenerated}
                initialCode={pineCode}
              />
              <div className="space-y-4">
                <TradingViewChart
                  symbol={selectedSymbol}
                  onSymbolChange={setSelectedSymbol}
                  className="h-[400px]"
                />
                {backtestResults && (
                  <div className="grid grid-cols-3 gap-4">
                    <QuickStat
                      label="Win Rate"
                      value={`${backtestResults.winRate}%`}
                      positive={backtestResults.winRate > 50}
                    />
                    <QuickStat
                      label="Profit Factor"
                      value={backtestResults.profitFactor.toFixed(2)}
                      positive={backtestResults.profitFactor > 1}
                    />
                    <QuickStat
                      label="Max DD"
                      value={`${backtestResults.maxDrawdownPercent}%`}
                      positive={backtestResults.maxDrawdownPercent < 15}
                    />
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Backtest Tab */}
          <TabsContent value="backtest" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <BacktestEngine
                  code={pineCode}
                  onResultsChange={handleBacktestResults}
                />
              </div>
              <div className="space-y-4">
                <AICoach
                  code={pineCode}
                  backtestResults={backtestResults}
                  onApplySuggestion={handleApplySuggestion}
                />
              </div>
            </div>
          </TabsContent>

          {/* AI Coach Tab */}
          <TabsContent value="coach" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <AICoach
                code={pineCode}
                backtestResults={backtestResults}
                className="h-full"
                onApplySuggestion={handleApplySuggestion}
              />
              <div className="space-y-4">
                <PineScriptEditor
                  onCodeChange={handleCodeChange}
                  initialCode={pineCode}
                />
              </div>
            </div>
          </TabsContent>

          {/* Script Converter Tab */}
          <TabsContent value="converter" className="space-y-4">
            <ScriptConverter />
          </TabsContent>
        </Tabs>

        {/* Quick Actions Bar */}
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
          <div className="flex items-center gap-2 p-2 rounded-full bg-background/95 border shadow-lg backdrop-blur">
            <Button
              variant={activeTab === 'chart' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-full"
              onClick={() => setActiveTab('chart')}
            >
              <LineChart className="h-4 w-4" />
            </Button>
            <Button
              variant={activeTab === 'editor' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-full"
              onClick={() => setActiveTab('editor')}
            >
              <Code2 className="h-4 w-4" />
            </Button>
            <Button
              variant={activeTab === 'backtest' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-full"
              onClick={() => setActiveTab('backtest')}
            >
              <BarChart3 className="h-4 w-4" />
            </Button>
            <Button
              variant={activeTab === 'coach' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-full"
              onClick={() => setActiveTab('coach')}
            >
              <Brain className="h-4 w-4" />
            </Button>
            <Button
              variant={activeTab === 'converter' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-full"
              onClick={() => setActiveTab('converter')}
            >
              <Wand2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </main>

      {/* Save Strategy Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Save className="h-5 w-5" />
              Save Strategy
            </DialogTitle>
            <DialogDescription>
              Save your Pine Script strategy locally for later use.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="strategy-name">Strategy Name</Label>
              <Input
                id="strategy-name"
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
                placeholder="Enter a name for your strategy"
              />
            </div>
            <div className="text-sm text-muted-foreground">
              <p>Symbol: {selectedSymbol}</p>
              <p>Code length: {pineCode.length} characters</p>
              {backtestResults && (
                <p>Includes backtest results: Win Rate {backtestResults.winRate}%</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={confirmSaveStrategy}>
              <Check className="h-4 w-4 mr-2" />
              Save Strategy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Load Strategy Dialog */}
      <Dialog open={loadDialogOpen} onOpenChange={setLoadDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5" />
              Load Strategy
            </DialogTitle>
            <DialogDescription>
              Select a previously saved strategy to load into the editor.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[400px] overflow-y-auto space-y-2">
            {savedStrategies.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No saved strategies yet.</p>
            ) : (
              savedStrategies.map((strategy, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50"
                >
                  <div>
                    <p className="font-medium">{strategy.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Saved: {new Date(strategy.savedAt).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => loadStrategy(strategy)}>
                      Load
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => deleteStrategy(index)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Share Strategy Dialog */}
      <Dialog open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Share2 className="h-5 w-5" />
              Share Strategy
            </DialogTitle>
            <DialogDescription>
              Share your Pine Script code with others.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="p-4 rounded-lg bg-muted overflow-hidden">
              <pre className="text-xs overflow-x-auto max-h-[200px]">
                {pineCode.slice(0, 500)}{pineCode.length > 500 ? '...' : ''}
              </pre>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" onClick={copyToClipboard}>
                <Copy className="h-4 w-4 mr-2" />
                Copy to Clipboard
              </Button>
              <Button variant="outline" onClick={downloadAsFile}>
                <Download className="h-4 w-4 mr-2" />
                Download .pine File
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShareDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              AI Suite Settings
            </DialogTitle>
            <DialogDescription>
              Configure your AI Strategy Suite preferences.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="space-y-2">
              <Label>Default Symbol</Label>
              <Select
                value={settings.defaultSymbol}
                onValueChange={(v) => setSettings({ ...settings, defaultSymbol: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="EURUSD">EUR/USD</SelectItem>
                  <SelectItem value="GBPUSD">GBP/USD</SelectItem>
                  <SelectItem value="USDJPY">USD/JPY</SelectItem>
                  <SelectItem value="XAUUSD">XAU/USD (Gold)</SelectItem>
                  <SelectItem value="BTCUSD">BTC/USD</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Default Timeframe</Label>
              <Select
                value={settings.defaultTimeframe}
                onValueChange={(v) => setSettings({ ...settings, defaultTimeframe: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 Minute</SelectItem>
                  <SelectItem value="5">5 Minutes</SelectItem>
                  <SelectItem value="15">15 Minutes</SelectItem>
                  <SelectItem value="60">1 Hour</SelectItem>
                  <SelectItem value="240">4 Hours</SelectItem>
                  <SelectItem value="D">Daily</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Auto-save</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically save your work every 5 minutes
                </p>
              </div>
              <Switch
                checked={settings.autoSave}
                onCheckedChange={(checked) => setSettings({ ...settings, autoSave: checked })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSettingsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={saveSettings}>
              <Check className="h-4 w-4 mr-2" />
              Save Settings
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Quick Stat component
function QuickStat({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive: boolean;
}) {
  return (
    <div className="p-3 rounded-lg bg-muted/50 border border-border/50 text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={`text-lg font-bold ${positive ? 'text-emerald-400' : 'text-red-400'}`}
      >
        {value}
      </div>
    </div>
  );
}
