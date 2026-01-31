'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Brain,
  Lightbulb,
  AlertTriangle,
  Shield,
  TrendingUp,
  Clock,
  Target,
  Zap,
  CheckCircle2,
  XCircle,
  Loader2,
  Send,
  MessageSquare,
  BarChart3,
  Sparkles,
  Copy,
  Save,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import type { BacktestResults, StrategyAnalysis, AICoachMessage } from '../types';

interface AICoachProps {
  code?: string;
  backtestResults?: BacktestResults | null;
  className?: string;
  onApplySuggestion?: (codeSnippet: string) => void;
}

interface AnalysisResult {
  biases: Array<{
    type: string;
    description: string;
    severity: 'low' | 'medium' | 'high';
  }>;
  riskIssues: Array<{
    type: string;
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    recommendation: string;
  }>;
  suggestions: Array<{
    type: string;
    description: string;
    expectedImpact: string;
    codeSnippet?: string;
  }>;
  summary: string;
}

// Severity colors
const severityColors = {
  low: 'text-blue-400 border-blue-400/30 bg-blue-400/10',
  medium: 'text-yellow-400 border-yellow-400/30 bg-yellow-400/10',
  high: 'text-orange-400 border-orange-400/30 bg-orange-400/10',
  critical: 'text-red-400 border-red-400/30 bg-red-400/10',
};

const severityIcons = {
  low: CheckCircle2,
  medium: AlertTriangle,
  high: AlertTriangle,
  critical: XCircle,
};

export function AICoach({ code = '', backtestResults, className, onApplySuggestion }: AICoachProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [chatMessages, setChatMessages] = useState<AICoachMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatting, setIsChatting] = useState(false);
  const [activeTab, setActiveTab] = useState<'analysis' | 'chat'>('analysis');
  const { toast } = useToast();

  // Analyze strategy
  const analyzeStrategy = useCallback(async () => {
    if (!code) {
      toast({
        title: 'No Code',
        description: 'Please enter Pine Script code to analyze.',
        variant: 'destructive',
      });
      return;
    }

    setIsAnalyzing(true);
    setAnalysis(null);

    try {
      const response = await fetch('/api/ai-suite/analyze-strategy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ code }),
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const data = await response.json();

      if (data.success && data.analysis) {
        setAnalysis(data.analysis);
      } else {
        // Generate local analysis if API fails
        setAnalysis(generateLocalAnalysis(code, backtestResults));
      }

      toast({
        title: 'Analysis Complete',
        description: 'Your strategy has been analyzed by AI Coach.',
      });
    } catch (error) {
      console.error('Analysis error:', error);
      // Fallback to local analysis
      setAnalysis(generateLocalAnalysis(code, backtestResults));
      toast({
        title: 'Analysis Complete',
        description: 'Strategy analyzed using local rules.',
      });
    } finally {
      setIsAnalyzing(false);
    }
  }, [code, backtestResults, toast]);

  // Send chat message
  const sendChatMessage = useCallback(async () => {
    if (!chatInput.trim()) return;

    const userMessage: AICoachMessage = {
      role: 'user',
      content: chatInput,
      timestamp: new Date().toISOString(),
    };

    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput('');
    setIsChatting(true);

    try {
      // For now, generate local response
      // In production, this would call the AI API
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const assistantMessage: AICoachMessage = {
        role: 'assistant',
        content: generateChatResponse(chatInput, code, backtestResults),
        timestamp: new Date().toISOString(),
      };

      setChatMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      toast({
        title: 'Chat Error',
        description: 'Failed to get response. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsChatting(false);
    }
  }, [chatInput, code, backtestResults, toast]);

  // Calculate strategy score
  const strategyScore = analysis
    ? calculateStrategyScore(analysis, backtestResults)
    : null;

  return (
    <Card className={cn('cyber-card', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              AI Strategy Coach
            </CardTitle>
            <CardDescription>
              Get AI-powered insights and recommendations
            </CardDescription>
          </div>
          {strategyScore !== null && (
            <div className="text-right">
              <div className="text-2xl font-bold text-primary">{strategyScore}/100</div>
              <div className="text-xs text-muted-foreground">Strategy Score</div>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="analysis">
              <BarChart3 className="h-4 w-4 mr-1" />
              Analysis
            </TabsTrigger>
            <TabsTrigger value="chat">
              <MessageSquare className="h-4 w-4 mr-1" />
              Ask Coach
            </TabsTrigger>
          </TabsList>

          {/* Analysis Tab */}
          <TabsContent value="analysis" className="space-y-4">
            <Button
              onClick={analyzeStrategy}
              disabled={isAnalyzing || !code}
              className="w-full"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing Strategy...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Analyze My Strategy
                </>
              )}
            </Button>

            {analysis && (
              <div className="space-y-4">
                {/* Summary */}
                <Alert>
                  <Brain className="h-4 w-4" />
                  <AlertTitle>AI Assessment</AlertTitle>
                  <AlertDescription>{analysis.summary}</AlertDescription>
                </Alert>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={async () => {
                      const fullAssessment = formatAnalysisAsText(analysis, backtestResults);
                      await navigator.clipboard.writeText(fullAssessment);
                      toast({
                        title: 'Copied!',
                        description: 'Full AI assessment copied to clipboard.',
                      });
                    }}
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Full Assessment
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      saveAnalysisToHistory(analysis, code, backtestResults);
                      toast({
                        title: 'Saved!',
                        description: 'Analysis saved to your history.',
                      });
                    }}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save to History
                  </Button>
                </div>

                {/* Biases */}
                {analysis.biases.length > 0 && (
                  <Accordion type="single" collapsible defaultValue="biases">
                    <AccordionItem value="biases">
                      <AccordionTrigger className="text-sm">
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-blue-400" />
                          Trading Biases ({analysis.biases.length})
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-2">
                          {analysis.biases.map((bias, idx) => {
                            const Icon = severityIcons[bias.severity];
                            return (
                              <div
                                key={idx}
                                className={cn(
                                  'p-3 rounded-lg border',
                                  severityColors[bias.severity]
                                )}
                              >
                                <div className="flex items-center gap-2 font-medium text-sm">
                                  <Icon className="h-4 w-4" />
                                  {bias.type}
                                  <Badge variant="outline" className="ml-auto text-xs">
                                    {bias.severity}
                                  </Badge>
                                </div>
                                <p className="text-sm mt-1 opacity-80">{bias.description}</p>
                              </div>
                            );
                          })}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                )}

                {/* Risk Issues */}
                {analysis.riskIssues.length > 0 && (
                  <Accordion type="single" collapsible defaultValue="risks">
                    <AccordionItem value="risks">
                      <AccordionTrigger className="text-sm">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-red-400" />
                          Risk Issues ({analysis.riskIssues.length})
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-2">
                          {analysis.riskIssues.map((issue, idx) => {
                            const Icon = severityIcons[issue.severity];
                            return (
                              <div
                                key={idx}
                                className={cn(
                                  'p-3 rounded-lg border',
                                  severityColors[issue.severity]
                                )}
                              >
                                <div className="flex items-center gap-2 font-medium text-sm">
                                  <Icon className="h-4 w-4" />
                                  {issue.type}
                                  <Badge variant="outline" className="ml-auto text-xs">
                                    {issue.severity}
                                  </Badge>
                                </div>
                                <p className="text-sm mt-1 opacity-80">{issue.description}</p>
                                <div className="mt-2 p-2 bg-background/50 rounded text-xs">
                                  <span className="font-medium">Recommendation:</span>{' '}
                                  {issue.recommendation}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                )}

                {/* Suggestions */}
                {analysis.suggestions.length > 0 && (
                  <Accordion type="single" collapsible defaultValue="suggestions">
                    <AccordionItem value="suggestions">
                      <AccordionTrigger className="text-sm">
                        <div className="flex items-center gap-2">
                          <Lightbulb className="h-4 w-4 text-yellow-400" />
                          Improvement Suggestions ({analysis.suggestions.length})
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-2">
                          {analysis.suggestions.map((suggestion, idx) => (
                            <div
                              key={idx}
                              className="p-3 rounded-lg border border-yellow-400/30 bg-yellow-400/10"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2 font-medium text-sm text-yellow-400">
                                  <Zap className="h-4 w-4" />
                                  {suggestion.type}
                                </div>
                                <div className="flex gap-1">
                                  {suggestion.codeSnippet && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="h-7 text-xs border-yellow-400/50 hover:bg-yellow-400/20"
                                      onClick={async () => {
                                        await navigator.clipboard.writeText(suggestion.codeSnippet!);
                                        toast({
                                          title: 'Copied!',
                                          description: `${suggestion.type} code copied to clipboard.`,
                                        });
                                      }}
                                    >
                                      <Copy className="h-3 w-3 mr-1" />
                                      Copy
                                    </Button>
                                  )}
                                  {suggestion.codeSnippet && onApplySuggestion && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="h-7 text-xs border-emerald-400/50 hover:bg-emerald-400/20 text-emerald-400"
                                      onClick={() => {
                                        onApplySuggestion(suggestion.codeSnippet!);
                                      }}
                                    >
                                      <CheckCircle2 className="h-3 w-3 mr-1" />
                                      Apply
                                    </Button>
                                  )}
                                </div>
                              </div>
                              <p className="text-sm mt-1 opacity-80">{suggestion.description}</p>
                              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                                <TrendingUp className="h-3 w-3" />
                                Expected Impact: {suggestion.expectedImpact}
                              </div>
                              {suggestion.codeSnippet && (
                                <pre className="mt-2 p-2 bg-background/50 rounded text-xs overflow-x-auto">
                                  {suggestion.codeSnippet}
                                </pre>
                              )}
                            </div>
                          ))}
                        </div>

                        {/* Apply All Suggestions Button */}
                        {onApplySuggestion && analysis.suggestions.some(s => s.codeSnippet) && (
                          <Button
                            className="w-full mt-4"
                            variant="outline"
                            onClick={() => {
                              const allSnippets = analysis.suggestions
                                .filter(s => s.codeSnippet)
                                .map(s => `// ${s.type}\n${s.codeSnippet}`)
                                .join('\n\n');
                              if (allSnippets) {
                                onApplySuggestion(allSnippets);
                                toast({
                                  title: 'All Suggestions Applied',
                                  description: `Added ${analysis.suggestions.filter(s => s.codeSnippet).length} improvements to your strategy.`,
                                });
                              }
                            }}
                          >
                            <Sparkles className="h-4 w-4 mr-2" />
                            Apply All Suggestions
                          </Button>
                        )}
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                )}

                {/* Backtest Integration */}
                {backtestResults && (
                  <Alert
                    className={cn(
                      'border',
                      backtestResults.totalPnl >= 0
                        ? 'border-emerald-400/30 bg-emerald-400/10'
                        : 'border-red-400/30 bg-red-400/10'
                    )}
                  >
                    <Target className="h-4 w-4" />
                    <AlertTitle>Backtest Performance</AlertTitle>
                    <AlertDescription>
                      <div className="grid grid-cols-3 gap-4 mt-2">
                        <div>
                          <div className="text-xs text-muted-foreground">Win Rate</div>
                          <div className="font-bold">{backtestResults.winRate}%</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Profit Factor</div>
                          <div className="font-bold">{backtestResults.profitFactor}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Max DD</div>
                          <div className="font-bold">{backtestResults.maxDrawdownPercent}%</div>
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            {!code && (
              <div className="text-center py-8 text-muted-foreground">
                <Brain className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>Enter Pine Script code to get AI analysis</p>
              </div>
            )}
          </TabsContent>

          {/* Chat Tab */}
          <TabsContent value="chat" className="space-y-4 min-h-[400px]">
            <ScrollArea className="h-[350px] w-full">
              <div className="space-y-4 pr-4">
                {chatMessages.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>Ask the AI Coach about your strategy</p>
                    <div className="mt-4 space-y-2">
                      <p className="text-xs">Try asking:</p>
                      <div className="flex flex-wrap gap-2 justify-center">
                        {[
                          'How can I improve my win rate?',
                          'Is my risk management adequate?',
                          'What filters should I add?',
                        ].map((q) => (
                          <Button
                            key={q}
                            variant="outline"
                            size="sm"
                            className="text-xs"
                            onClick={() => setChatInput(q)}
                          >
                            {q}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {chatMessages.map((message, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      'flex w-full',
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    <div
                      className={cn(
                        'max-w-[90%] p-3 rounded-lg',
                        message.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      )}
                    >
                      <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
                      <div className="text-xs opacity-60 mt-1">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}

                {isChatting && (
                  <div className="flex justify-start">
                    <div className="bg-muted p-3 rounded-lg">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            <div className="flex gap-2 w-full">
              <Textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask the AI Coach..."
                className="min-h-[60px] resize-none flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                  }
                }}
              />
              <Button
                onClick={sendChatMessage}
                disabled={isChatting || !chatInput.trim()}
                className="px-4 h-auto"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// Local analysis generator (fallback when API unavailable)
function generateLocalAnalysis(
  code: string,
  backtestResults?: BacktestResults | null
): AnalysisResult {
  const biases: AnalysisResult['biases'] = [];
  const riskIssues: AnalysisResult['riskIssues'] = [];
  const suggestions: AnalysisResult['suggestions'] = [];

  // Check for biases
  if (!code.includes('session') && !code.includes('time')) {
    biases.push({
      type: 'No Session Filter',
      description: 'Strategy runs 24/7 without time-based filters. Performance may vary significantly during different trading sessions.',
      severity: 'medium',
    });
  }

  if (code.includes('strategy.long') && !code.includes('strategy.short')) {
    biases.push({
      type: 'Long-Only Bias',
      description: 'Strategy only takes long positions. Consider adding short entries for bear markets.',
      severity: 'low',
    });
  }

  if (!code.includes('ta.sma') && !code.includes('ta.ema') && !code.includes('200')) {
    biases.push({
      type: 'No Trend Filter',
      description: 'No trend confirmation detected. Trading against the trend can lead to losses.',
      severity: 'medium',
    });
  }

  // Check for risk issues
  if (!code.includes('stop') && !code.includes('sl') && !code.includes('strategy.exit')) {
    riskIssues.push({
      type: 'No Stop Loss',
      description: 'No stop loss detected in the strategy. This exposes the account to unlimited downside risk.',
      severity: 'critical',
      recommendation: 'Add ATR-based or percentage-based stop loss using strategy.exit()',
    });
  }

  if (!code.includes('strategy.risk') && !code.includes('percent_of_equity')) {
    riskIssues.push({
      type: 'No Position Sizing',
      description: 'Fixed position sizing detected. Risk per trade may vary significantly.',
      severity: 'high',
      recommendation: 'Use strategy.percent_of_equity for consistent risk management',
    });
  }

  // Backtest-based weakness detection
  if (backtestResults) {
    // High drawdown warning
    if (backtestResults.maxDrawdownPercent > 20) {
      riskIssues.push({
        type: 'High Drawdown',
        description: `Max drawdown of ${backtestResults.maxDrawdownPercent}% exceeds recommended 20% threshold for prop firms.`,
        severity: 'high',
        recommendation: 'Reduce position size or tighten stop losses',
      });
    } else if (backtestResults.maxDrawdownPercent > 10) {
      riskIssues.push({
        type: 'Moderate Drawdown',
        description: `Max drawdown of ${backtestResults.maxDrawdownPercent}% is acceptable but could be improved.`,
        severity: 'medium',
        recommendation: 'Consider adding trailing stops or scaling out of positions',
      });
    }

    // Low win rate warning
    if (backtestResults.winRate < 40) {
      riskIssues.push({
        type: 'Low Win Rate',
        description: `Win rate of ${backtestResults.winRate}% is below 40%. This requires high R:R to be profitable.`,
        severity: 'high',
        recommendation: 'Add confirmation filters or improve entry timing',
      });

      suggestions.push({
        type: 'Improve Entry Timing',
        description: 'Add pullback entry or wait for momentum confirmation to improve win rate',
        expectedImpact: '+10-15% win rate improvement',
        codeSnippet: `// Wait for pullback before entry
pullbackEntry = ta.crossover(fastMA, slowMA) and close < ta.highest(close, 3)
longCondition = pullbackEntry and rsi < 60`,
      });
    }

    // Poor profit factor
    if (backtestResults.profitFactor < 1.0) {
      riskIssues.push({
        type: 'Losing Strategy',
        description: `Profit factor of ${backtestResults.profitFactor} means the strategy is losing money.`,
        severity: 'critical',
        recommendation: 'Complete strategy overhaul required - review entry/exit logic',
      });
    } else if (backtestResults.profitFactor < 1.3) {
      riskIssues.push({
        type: 'Marginal Profitability',
        description: `Profit factor of ${backtestResults.profitFactor} leaves little room for slippage/commissions.`,
        severity: 'medium',
        recommendation: 'Target profit factor of 1.5+ for live trading',
      });
    }

    // Poor Sharpe ratio
    if (backtestResults.sharpeRatio < 0.5) {
      biases.push({
        type: 'High Volatility Returns',
        description: `Sharpe ratio of ${backtestResults.sharpeRatio} indicates inconsistent returns relative to risk.`,
        severity: 'medium',
      });
    }

    // Improvement suggestions based on backtest results
    if (backtestResults.winRate < 50 && !code.includes('ta.rsi')) {
      suggestions.push({
        type: 'Add RSI Momentum Filter',
        description: 'Filter entries with RSI to avoid trading in overbought/oversold conditions',
        expectedImpact: '+8-12% win rate, fewer trades',
        codeSnippet: `rsi = ta.rsi(close, 14)
longCondition = longCondition and rsi > 30 and rsi < 70
shortCondition = shortCondition and rsi > 30 and rsi < 70`,
      });
    }

    if (backtestResults.maxDrawdownPercent > 15 && !code.includes('trailing')) {
      suggestions.push({
        type: 'Add Trailing Stop',
        description: 'Trailing stops can lock in profits and reduce drawdown',
        expectedImpact: '-5-10% max drawdown',
        codeSnippet: `// Trailing stop using ATR
trailAtr = ta.atr(14) * 2
strategy.exit("Trail Long", "Long", trail_points=trailAtr * 10, trail_offset=trailAtr * 5)`,
      });
    }

    if (backtestResults.profitFactor < 1.5) {
      suggestions.push({
        type: 'Improve Risk:Reward Ratio',
        description: 'Increase take profit distance or tighten stops to improve R:R',
        expectedImpact: '+0.2-0.3 profit factor',
        codeSnippet: `// 2:1 Risk Reward using ATR
atr = ta.atr(14)
stopDistance = atr * 1.5
takeProfit = close + (stopDistance * 2)  // 2:1 R:R
stopLoss = close - stopDistance`,
      });
    }
  }

  // Generate suggestions based on code analysis
  if (!code.includes('ta.atr')) {
    suggestions.push({
      type: 'Add ATR Volatility Filter',
      description: 'Using ATR for stop loss and take profit adapts to market volatility',
      expectedImpact: '+5-10% win rate improvement',
      codeSnippet: `atr = ta.atr(14)
stopLoss = close - (atr * 1.5)
takeProfit = close + (atr * 3)`,
    });
  }

  if (!code.includes('volume')) {
    suggestions.push({
      type: 'Add Volume Confirmation',
      description: 'Volume confirmation can improve signal quality by filtering low-conviction moves',
      expectedImpact: 'Higher quality trades, fewer false signals',
      codeSnippet: `volSma = ta.sma(volume, 20)
highVolume = volume > volSma * 1.2
longCondition = longCondition and highVolume`,
    });
  }

  if (!code.includes('session') && !code.includes('time(')) {
    suggestions.push({
      type: 'Add Trading Session Filter',
      description: 'Limit trading to high-liquidity sessions (London/NY) for better execution',
      expectedImpact: 'Better fills, reduced slippage',
      codeSnippet: `// London and NY session filter (UTC)
inSession = (hour >= 8 and hour < 12) or (hour >= 13 and hour < 17)
longCondition = longCondition and inSession`,
    });
  }

  // Generate summary
  const criticalCount = riskIssues.filter((r) => r.severity === 'critical').length;
  const highCount = riskIssues.filter((r) => r.severity === 'high').length;
  const issueCount = criticalCount + highCount;
  let summary = '';

  if (criticalCount > 0) {
    summary = `CRITICAL: ${criticalCount} critical issue(s) found. Do NOT trade this strategy live until resolved.`;
  } else if (highCount > 0) {
    summary = `Your strategy has ${highCount} significant issue(s) that should be addressed before live trading.`;
  } else if (backtestResults && backtestResults.profitFactor > 1.5 && backtestResults.winRate > 45) {
    summary = 'Good strategy! Solid metrics. Review the suggestions below for potential improvements.';
  } else if (backtestResults) {
    summary = 'Strategy shows promise but could use optimization. Apply the suggestions to improve performance.';
  } else {
    summary = 'Run a backtest to get detailed performance analysis and personalized recommendations.';
  }

  return { biases, riskIssues, suggestions, summary };
}

// Chat response generator
function generateChatResponse(
  question: string,
  code: string,
  backtestResults?: BacktestResults | null
): string {
  const q = question.toLowerCase();

  if (q.includes('win rate')) {
    if (backtestResults) {
      if (backtestResults.winRate < 40) {
        return `Your current win rate is ${backtestResults.winRate}%, which is below typical profitable levels. Consider:\n\n1. Adding trend filters (like checking if price is above 200 SMA for longs)\n2. Using RSI to avoid overbought/oversold entries\n3. Adding volume confirmation to filter weak signals\n4. Tightening entry criteria even if it means fewer trades`;
      } else if (backtestResults.winRate < 50) {
        return `Your win rate of ${backtestResults.winRate}% is acceptable if your risk-reward ratio compensates. Your current profit factor is ${backtestResults.profitFactor}. To improve:\n\n1. Consider adding a momentum filter\n2. Review losing trades for common patterns\n3. Test different timeframes`;
      } else {
        return `Your win rate of ${backtestResults.winRate}% is solid! Focus on:\n\n1. Maintaining consistent position sizing\n2. Not over-optimizing (curve fitting)\n3. Forward testing on demo before live`;
      }
    }
    return 'Run a backtest first to analyze your win rate. Then I can provide specific recommendations based on your results.';
  }

  if (q.includes('risk') || q.includes('stop loss') || q.includes('position size')) {
    const hasStop = code.includes('stop') || code.includes('sl');
    if (!hasStop) {
      return 'CRITICAL: Your strategy has no stop loss! This is dangerous. Add one immediately:\n\n```pinescript\natr = ta.atr(14)\nstopLoss = close - (atr * 1.5)\nstrategy.exit("Exit Long", "Long", stop=stopLoss)\n```\n\nNever trade without a stop loss.';
    }
    return 'Your risk management looks reasonable. Key principles:\n\n1. Risk no more than 1-2% per trade\n2. Use ATR-based stops that adapt to volatility\n3. Maintain 2:1 minimum reward-to-risk\n4. Never move stops against your position';
  }

  if (q.includes('filter')) {
    return 'Here are filters to consider adding:\n\n**Trend Filter:**\n```pinescript\ntrendFilter = close > ta.sma(close, 200)\n```\n\n**Volatility Filter:**\n```pinescript\natrFilter = ta.atr(14) > ta.sma(ta.atr(14), 50)\n```\n\n**Volume Filter:**\n```pinescript\nvolFilter = volume > ta.sma(volume, 20) * 1.5\n```\n\nCombine with your entry conditions using `and`.';
  }

  if (q.includes('prop firm') || q.includes('funded')) {
    return `For prop firm trading, focus on:\n\n1. **Max Drawdown**: Keep under 5% daily, 10% total\n2. **Consistency**: Aim for steady gains, not home runs\n3. **Risk per trade**: 0.5-1% maximum\n4. **Session times**: Trade during liquid hours only\n\n${backtestResults ? `Your current max drawdown is ${backtestResults.maxDrawdownPercent}%${backtestResults.maxDrawdownPercent > 10 ? ' - this needs to be reduced!' : ' - acceptable for most firms.'}` : 'Run a backtest to check your drawdown levels.'}`;
  }

  // Default response
  return `Great question! Based on your strategy, here are my thoughts:\n\n1. Always prioritize risk management over returns\n2. Test on multiple symbols and timeframes\n3. Use realistic commission and slippage in backtests\n4. Consider market conditions (trending vs ranging)\n\nWant me to analyze any specific aspect of your strategy?`;
}

// Calculate strategy score
function calculateStrategyScore(
  analysis: AnalysisResult,
  backtestResults?: BacktestResults | null
): number {
  let score = 70; // Base score

  // Deduct for issues
  analysis.riskIssues.forEach((issue) => {
    if (issue.severity === 'critical') score -= 20;
    else if (issue.severity === 'high') score -= 10;
    else if (issue.severity === 'medium') score -= 5;
    else score -= 2;
  });

  // Deduct for biases
  analysis.biases.forEach((bias) => {
    if (bias.severity === 'high') score -= 5;
    else if (bias.severity === 'medium') score -= 3;
    else score -= 1;
  });

  // Add for backtest performance
  if (backtestResults) {
    if (backtestResults.profitFactor > 1.5) score += 10;
    else if (backtestResults.profitFactor > 1.2) score += 5;

    if (backtestResults.winRate > 50) score += 5;
    if (backtestResults.sharpeRatio > 1) score += 5;

    if (backtestResults.maxDrawdownPercent < 10) score += 5;
    else if (backtestResults.maxDrawdownPercent > 25) score -= 10;
  }

  return Math.max(0, Math.min(100, score));
}

// Format analysis as copyable text
function formatAnalysisAsText(
  analysis: AnalysisResult,
  backtestResults?: BacktestResults | null
): string {
  let text = '# AI Strategy Assessment\n\n';
  text += `## Summary\n${analysis.summary}\n\n`;

  if (analysis.biases.length > 0) {
    text += '## Trading Biases\n';
    analysis.biases.forEach((bias) => {
      text += `- **${bias.type}** (${bias.severity}): ${bias.description}\n`;
    });
    text += '\n';
  }

  if (analysis.riskIssues.length > 0) {
    text += '## Risk Issues\n';
    analysis.riskIssues.forEach((issue) => {
      text += `- **${issue.type}** (${issue.severity}): ${issue.description}\n`;
      text += `  - Recommendation: ${issue.recommendation}\n`;
    });
    text += '\n';
  }

  if (analysis.suggestions.length > 0) {
    text += '## Improvement Suggestions\n';
    analysis.suggestions.forEach((suggestion) => {
      text += `### ${suggestion.type}\n`;
      text += `${suggestion.description}\n`;
      text += `Expected Impact: ${suggestion.expectedImpact}\n`;
      if (suggestion.codeSnippet) {
        text += '```pinescript\n' + suggestion.codeSnippet + '\n```\n';
      }
      text += '\n';
    });
  }

  if (backtestResults) {
    text += '## Backtest Results\n';
    text += `- Win Rate: ${backtestResults.winRate}%\n`;
    text += `- Profit Factor: ${backtestResults.profitFactor}\n`;
    text += `- Max Drawdown: ${backtestResults.maxDrawdownPercent}%\n`;
    text += `- Sharpe Ratio: ${backtestResults.sharpeRatio}\n`;
  }

  text += '\n---\nGenerated by TradeFlow AI Coach';
  return text;
}

// Save analysis to local storage history
function saveAnalysisToHistory(
  analysis: AnalysisResult,
  code: string,
  backtestResults?: BacktestResults | null
) {
  const historyKey = 'tradeflow-analysis-history';
  const existing = localStorage.getItem(historyKey);
  const history = existing ? JSON.parse(existing) : [];

  const entry = {
    id: Date.now().toString(),
    timestamp: new Date().toISOString(),
    analysis,
    code: code.slice(0, 500) + (code.length > 500 ? '...' : ''), // Store first 500 chars
    backtestResults,
  };

  history.unshift(entry); // Add to beginning
  // Keep only last 20 entries
  if (history.length > 20) history.pop();

  localStorage.setItem(historyKey, JSON.stringify(history));
}
