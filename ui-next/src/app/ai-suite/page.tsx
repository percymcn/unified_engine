'use client';

import { useState, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
} from 'lucide-react';
import Link from 'next/link';
import {
  TradingViewChart,
  PineScriptEditor,
  BacktestEngine,
  AICoach,
} from '@/features/ai-suite';
import type { BacktestResults, WebhookPayload } from '@/features/ai-suite/types';

export default function AIStrategyPage() {
  const [pineCode, setPineCode] = useState('');
  const [backtestResults, setBacktestResults] = useState<BacktestResults | null>(null);
  const [webhookPayload, setWebhookPayload] = useState<WebhookPayload | null>(null);
  const [activeTab, setActiveTab] = useState('chart');
  const [selectedSymbol, setSelectedSymbol] = useState('EURUSD');

  const handleCodeChange = useCallback((code: string) => {
    setPineCode(code);
  }, []);

  const handleBacktestResults = useCallback((results: BacktestResults | null) => {
    setBacktestResults(results);
  }, []);

  const handleWebhookGenerated = useCallback((payload: WebhookPayload) => {
    setWebhookPayload(payload);
  }, []);

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
            <Button variant="outline" size="sm">
              <Save className="h-4 w-4 mr-2" />
              Save Strategy
            </Button>
            <Button variant="outline" size="sm">
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </Button>
            <Button variant="ghost" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
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
              />
              <div className="space-y-4">
                <PineScriptEditor
                  onCodeChange={handleCodeChange}
                  initialCode={pineCode}
                />
              </div>
            </div>
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
          </div>
        </div>
      </main>
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
