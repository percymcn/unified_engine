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
  Key,
  Loader2,
  RefreshCw,
  Eye,
  EyeOff,
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
    webhookKey: '',
  });
  const [showWebhookKey, setShowWebhookKey] = useState(false);
  const [loadingWebhookKey, setLoadingWebhookKey] = useState(false);

  // Load saved strategies and settings on mount
  useEffect(() => {
    const stored = localStorage.getItem('tradeflow-strategies');
    if (stored) {
      setSavedStrategies(JSON.parse(stored));
    }
    const storedSettings = localStorage.getItem('tradeflow-ai-suite-settings');
    if (storedSettings) {
      const parsed = JSON.parse(storedSettings);
      setSettings(parsed);
      // Apply default symbol from settings
      if (parsed.defaultSymbol) {
        setSelectedSymbol(parsed.defaultSymbol);
      }
    }

    // Fetch webhook key from API
    const fetchWebhookKey = async () => {
      try {
        const response = await fetch('/api/webhooks/primary-key', { credentials: 'include' });
        if (response.ok) {
          const data = await response.json();
          if (data.key) {
            setSettings(prev => ({ ...prev, webhookKey: data.key }));
          }
        }
      } catch (error) {
        console.error('Failed to fetch webhook key:', error);
      }
    };
    fetchWebhookKey();
  }, []);

  // Auto-save feature
  useEffect(() => {
    if (!settings.autoSave || !pineCode.trim()) return;

    const autoSaveTimer = setInterval(() => {
      const autoSaveData = {
        name: `Auto-save ${new Date().toLocaleTimeString()}`,
        code: pineCode,
        symbol: selectedSymbol,
        savedAt: new Date().toISOString(),
        backtestResults: backtestResults,
      };
      localStorage.setItem('tradeflow-autosave', JSON.stringify(autoSaveData));
    }, 5 * 60 * 1000); // Every 5 minutes

    return () => clearInterval(autoSaveTimer);
  }, [settings.autoSave, pineCode, selectedSymbol, backtestResults]);

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
    // Switch to editor tab so user can see the applied code
    setActiveTab('editor');
    // Show visual feedback
    toast({
      title: 'Code Updated!',
      description: 'Suggestion applied - check the Editor tab to see the changes.',
    });
  }, [toast]);

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
    <div className="min-h-screen bg-background pb-20 md:pb-6">
      {/* Header - Responsive with wrapping */}
      <header className="sticky top-0 z-40 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container px-3 sm:px-4">
          {/* Top row: Back button and title */}
          <div className="flex h-12 sm:h-14 items-center justify-between gap-2">
            <div className="flex items-center gap-2 sm:gap-4 min-w-0">
              <Link href="/dashboard">
                <Button variant="ghost" size="sm" className="px-2 sm:px-3">
                  <ArrowLeft className="h-4 w-4" />
                  <span className="hidden sm:inline ml-2">Dashboard</span>
                </Button>
              </Link>
              <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                <Sparkles className="h-4 w-4 sm:h-5 sm:w-5 text-primary flex-shrink-0" />
                <h1 className="text-sm sm:text-lg font-semibold truncate">AI Suite</h1>
                <Badge variant="secondary" className="text-[10px] sm:text-xs hidden xs:inline-flex">
                  Beta
                </Badge>
              </div>
            </div>

            {/* Action buttons - compact on mobile */}
            <div className="flex items-center gap-1 sm:gap-2">
              {savedStrategies.length > 0 && (
                <Button variant="outline" size="sm" className="h-8 px-2 sm:px-3" onClick={() => setLoadDialogOpen(true)}>
                  <FolderOpen className="h-4 w-4" />
                  <span className="hidden sm:inline ml-2">Load ({savedStrategies.length})</span>
                </Button>
              )}
              <Button variant="outline" size="sm" className="h-8 px-2 sm:px-3" onClick={handleSaveStrategy}>
                <Save className="h-4 w-4" />
                <span className="hidden sm:inline ml-2">Save</span>
              </Button>
              <Button variant="outline" size="sm" className="h-8 px-2 sm:px-3 hidden xs:flex" onClick={handleShareStrategy}>
                <Share2 className="h-4 w-4" />
                <span className="hidden sm:inline ml-2">Share</span>
              </Button>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={handleOpenSettings}>
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-3 sm:px-4 py-4 sm:py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4 sm:space-y-6">
          {/* Responsive Tabs - hidden on mobile (use bottom nav instead) */}
          <TabsList className="hidden sm:grid w-full grid-cols-5 lg:w-auto lg:inline-grid h-auto">
            <TabsTrigger value="chart" className="gap-1.5 sm:gap-2 py-2 px-2 sm:px-4 text-xs sm:text-sm">
              <LineChart className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden md:inline">Chart</span>
            </TabsTrigger>
            <TabsTrigger value="editor" className="gap-1.5 sm:gap-2 py-2 px-2 sm:px-4 text-xs sm:text-sm">
              <Code2 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden md:inline">Editor</span>
            </TabsTrigger>
            <TabsTrigger value="backtest" className="gap-1.5 sm:gap-2 py-2 px-2 sm:px-4 text-xs sm:text-sm">
              <BarChart3 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden md:inline">Backtest</span>
            </TabsTrigger>
            <TabsTrigger value="coach" className="gap-1.5 sm:gap-2 py-2 px-2 sm:px-4 text-xs sm:text-sm">
              <Brain className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden md:inline">AI Coach</span>
            </TabsTrigger>
            <TabsTrigger value="converter" className="gap-1.5 sm:gap-2 py-2 px-2 sm:px-4 text-xs sm:text-sm">
              <Wand2 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden md:inline">Converter</span>
            </TabsTrigger>
          </TabsList>

          {/* Chart Tab - Responsive height */}
          <TabsContent value="chart" className="space-y-4 mt-0 sm:mt-2">
            <TradingViewChart
              symbol={selectedSymbol}
              onSymbolChange={setSelectedSymbol}
              className="w-full min-h-[350px] sm:min-h-[450px] md:min-h-[500px] lg:min-h-[600px] h-[calc(100vh-180px)] sm:h-[calc(100vh-200px)]"
            />
          </TabsContent>

          {/* Editor Tab - Stack on mobile, side-by-side on desktop */}
          <TabsContent value="editor" className="space-y-4 mt-0 sm:mt-2">
            <div className="flex flex-col lg:grid lg:grid-cols-2 gap-4 lg:gap-6">
              {/* Editor comes first on mobile for better UX */}
              <div className="order-1">
                <PineScriptEditor
                  onCodeChange={handleCodeChange}
                  onWebhookGenerated={handleWebhookGenerated}
                  initialCode={pineCode}
                  webhookKey={settings.webhookKey}
                />
              </div>
              {/* Chart and stats - hidden on mobile to save space, shown on tablet+ */}
              <div className="order-2 space-y-4 hidden md:block">
                <TradingViewChart
                  symbol={selectedSymbol}
                  onSymbolChange={setSelectedSymbol}
                  className="h-[300px] lg:h-[400px]"
                />
                {backtestResults && (
                  <div className="grid grid-cols-3 gap-2 sm:gap-4">
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

          {/* Backtest Tab - Stack on mobile */}
          <TabsContent value="backtest" className="space-y-4 mt-0 sm:mt-2">
            <div className="flex flex-col lg:grid lg:grid-cols-3 gap-4 lg:gap-6">
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

          {/* AI Coach Tab - Stack on mobile */}
          <TabsContent value="coach" className="space-y-4 mt-0 sm:mt-2">
            <div className="flex flex-col lg:grid lg:grid-cols-2 gap-4 lg:gap-6">
              {/* AI Coach first on all devices */}
              <div className="order-1">
                <AICoach
                  code={pineCode}
                  backtestResults={backtestResults}
                  className="h-full"
                  onApplySuggestion={handleApplySuggestion}
                />
              </div>
              {/* Editor second - collapses on mobile */}
              <div className="order-2">
                <PineScriptEditor
                  onCodeChange={handleCodeChange}
                  initialCode={pineCode}
                  webhookKey={settings.webhookKey}
                />
              </div>
            </div>
          </TabsContent>

          {/* Script Converter Tab */}
          <TabsContent value="converter" className="space-y-4 mt-0 sm:mt-2">
            <ScriptConverter webhookKey={settings.webhookKey} />
          </TabsContent>
        </Tabs>
      </main>

      {/* Quick Actions Bar - Fixed bottom navigation for mobile */}
      <div className="fixed bottom-0 left-0 right-0 z-50 sm:bottom-4 sm:left-1/2 sm:right-auto sm:-translate-x-1/2">
        <div className="flex items-center justify-center gap-1 sm:gap-2 p-2 pb-safe sm:p-2 sm:rounded-full bg-background/95 border-t sm:border shadow-lg backdrop-blur">
          <Button
            variant={activeTab === 'chart' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1 sm:flex-none h-10 sm:h-8 rounded-lg sm:rounded-full flex-col sm:flex-row gap-0.5 sm:gap-0"
            onClick={() => setActiveTab('chart')}
          >
            <LineChart className="h-4 w-4" />
            <span className="text-[10px] sm:hidden">Chart</span>
          </Button>
          <Button
            variant={activeTab === 'editor' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1 sm:flex-none h-10 sm:h-8 rounded-lg sm:rounded-full flex-col sm:flex-row gap-0.5 sm:gap-0"
            onClick={() => setActiveTab('editor')}
          >
            <Code2 className="h-4 w-4" />
            <span className="text-[10px] sm:hidden">Editor</span>
          </Button>
          <Button
            variant={activeTab === 'backtest' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1 sm:flex-none h-10 sm:h-8 rounded-lg sm:rounded-full flex-col sm:flex-row gap-0.5 sm:gap-0"
            onClick={() => setActiveTab('backtest')}
          >
            <BarChart3 className="h-4 w-4" />
            <span className="text-[10px] sm:hidden">Test</span>
          </Button>
          <Button
            variant={activeTab === 'coach' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1 sm:flex-none h-10 sm:h-8 rounded-lg sm:rounded-full flex-col sm:flex-row gap-0.5 sm:gap-0"
            onClick={() => setActiveTab('coach')}
          >
            <Brain className="h-4 w-4" />
            <span className="text-[10px] sm:hidden">Coach</span>
          </Button>
          <Button
            variant={activeTab === 'converter' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1 sm:flex-none h-10 sm:h-8 rounded-lg sm:rounded-full flex-col sm:flex-row gap-0.5 sm:gap-0"
            onClick={() => setActiveTab('converter')}
          >
            <Wand2 className="h-4 w-4" />
            <span className="text-[10px] sm:hidden">Convert</span>
          </Button>
        </div>
      </div>

      {/* Save Strategy Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent className="max-w-[95vw] sm:max-w-lg mx-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base sm:text-lg">
              <Save className="h-4 w-4 sm:h-5 sm:w-5" />
              Save Strategy
            </DialogTitle>
            <DialogDescription className="text-sm">
              Save your Pine Script strategy locally for later use.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 sm:py-4">
            <div className="space-y-2">
              <Label htmlFor="strategy-name" className="text-sm">Strategy Name</Label>
              <Input
                id="strategy-name"
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
                placeholder="Enter a name for your strategy"
                className="h-9 sm:h-10"
              />
            </div>
            <div className="text-xs sm:text-sm text-muted-foreground space-y-1">
              <p>Symbol: {selectedSymbol}</p>
              <p>Code length: {pineCode.length} characters</p>
              {backtestResults && (
                <p>Includes backtest results: Win Rate {backtestResults.winRate}%</p>
              )}
            </div>
          </div>
          <DialogFooter className="flex-col-reverse sm:flex-row gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)} className="w-full sm:w-auto">
              Cancel
            </Button>
            <Button onClick={confirmSaveStrategy} className="w-full sm:w-auto">
              <Check className="h-4 w-4 mr-2" />
              Save Strategy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Load Strategy Dialog */}
      <Dialog open={loadDialogOpen} onOpenChange={setLoadDialogOpen}>
        <DialogContent className="max-w-[95vw] sm:max-w-2xl mx-auto max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base sm:text-lg">
              <FolderOpen className="h-4 w-4 sm:h-5 sm:w-5" />
              Load Strategy
            </DialogTitle>
            <DialogDescription className="text-sm">
              Select a previously saved strategy to load into the editor.
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto space-y-2 max-h-[50vh] sm:max-h-[400px]">
            {savedStrategies.length === 0 ? (
              <p className="text-center text-muted-foreground py-8 text-sm">No saved strategies yet.</p>
            ) : (
              savedStrategies.map((strategy, index) => (
                <div
                  key={index}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg border hover:bg-muted/50 gap-2"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-sm truncate">{strategy.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Saved: {new Date(strategy.savedAt).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button size="sm" className="flex-1 sm:flex-none h-8" onClick={() => loadStrategy(strategy)}>
                      Load
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      className="flex-1 sm:flex-none h-8"
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
        <DialogContent className="max-w-[95vw] sm:max-w-lg mx-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base sm:text-lg">
              <Share2 className="h-4 w-4 sm:h-5 sm:w-5" />
              Share Strategy
            </DialogTitle>
            <DialogDescription className="text-sm">
              Share your Pine Script code with others.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 sm:py-4">
            <div className="p-3 sm:p-4 rounded-lg bg-muted overflow-hidden">
              <pre className="text-[10px] sm:text-xs overflow-x-auto max-h-[150px] sm:max-h-[200px]">
                {pineCode.slice(0, 500)}{pineCode.length > 500 ? '...' : ''}
              </pre>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <Button variant="outline" onClick={copyToClipboard} className="h-9 sm:h-10">
                <Copy className="h-4 w-4 mr-2" />
                Copy to Clipboard
              </Button>
              <Button variant="outline" onClick={downloadAsFile} className="h-9 sm:h-10">
                <Download className="h-4 w-4 mr-2" />
                Download .pine
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShareDialogOpen(false)} className="w-full sm:w-auto">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen}>
        <DialogContent className="max-w-[95vw] sm:max-w-lg mx-auto max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base sm:text-lg">
              <Settings className="h-4 w-4 sm:h-5 sm:w-5" />
              AI Suite Settings
            </DialogTitle>
            <DialogDescription className="text-sm">
              Configure your AI Strategy Suite preferences.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 sm:space-y-6 py-2 sm:py-4">
            {/* Symbol and Timeframe in grid on tablet+ */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm">Default Symbol</Label>
                <Select
                  value={settings.defaultSymbol}
                  onValueChange={(v) => setSettings({ ...settings, defaultSymbol: v })}
                >
                  <SelectTrigger className="h-9 sm:h-10">
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
                <Label className="text-sm">Default Timeframe</Label>
                <Select
                  value={settings.defaultTimeframe}
                  onValueChange={(v) => setSettings({ ...settings, defaultTimeframe: v })}
                >
                  <SelectTrigger className="h-9 sm:h-10">
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
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div className="space-y-0.5">
                <Label className="text-sm">Auto-save</Label>
                <p className="text-xs text-muted-foreground">
                  Save work every 5 minutes
                </p>
              </div>
              <Switch
                checked={settings.autoSave}
                onCheckedChange={(checked) => setSettings({ ...settings, autoSave: checked })}
              />
            </div>

            {/* Webhook Key Section */}
            <div className="pt-3 sm:pt-4 border-t space-y-3">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4 text-primary" />
                <Label className="text-sm font-medium">Webhook Key Integration</Label>
              </div>
              <p className="text-xs text-muted-foreground">
                Auto-embedded in generated scripts and templates.
              </p>
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showWebhookKey ? 'text' : 'password'}
                    value={settings.webhookKey}
                    onChange={(e) => setSettings({ ...settings, webhookKey: e.target.value })}
                    placeholder="Enter or paste your webhook key"
                    className="pr-10 font-mono text-xs sm:text-sm h-9 sm:h-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
                    onClick={() => setShowWebhookKey(!showWebhookKey)}
                  >
                    {showWebhookKey ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-9 sm:h-10 px-3"
                  onClick={async () => {
                    setLoadingWebhookKey(true);
                    try {
                      const response = await fetch('/api/webhooks/primary-key', { credentials: 'include' });
                      if (response.ok) {
                        const data = await response.json();
                        if (data.key) {
                          setSettings(prev => ({ ...prev, webhookKey: data.key }));
                          toast({
                            title: 'Webhook Key Loaded',
                            description: 'Your primary webhook key has been loaded.',
                          });
                        }
                      } else {
                        toast({
                          title: 'No Webhook Key Found',
                          description: 'Create one in Settings > API Keys.',
                          variant: 'destructive',
                        });
                      }
                    } catch {
                      toast({
                        title: 'Failed to Load',
                        description: 'Could not fetch webhook key.',
                        variant: 'destructive',
                      });
                    }
                    setLoadingWebhookKey(false);
                  }}
                  disabled={loadingWebhookKey}
                >
                  {loadingWebhookKey ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 sm:mr-2" />
                      <span className="hidden sm:inline">Load</span>
                    </>
                  )}
                </Button>
              </div>
              {settings.webhookKey && (
                <div className="flex items-center gap-2 p-2 rounded bg-emerald-500/10 border border-emerald-500/30">
                  <Check className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span className="text-xs text-emerald-400">
                    Webhook key configured
                  </span>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Don&apos;t have a webhook key?{' '}
                <Link href="/dashboard/settings" className="text-primary hover:underline">
                  Create one in Settings
                </Link>
              </p>
            </div>
          </div>
          <DialogFooter className="flex-col-reverse sm:flex-row gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setSettingsDialogOpen(false)} className="w-full sm:w-auto">
              Cancel
            </Button>
            <Button onClick={saveSettings} className="w-full sm:w-auto">
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
