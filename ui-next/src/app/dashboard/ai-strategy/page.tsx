"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Brain, TrendingUp, TrendingDown, AlertTriangle, BarChart3, Target, Shield, DollarSign, LineChart, Zap, Building2 } from "lucide-react";
import { toast } from "sonner";

interface AnalysisResult {
  analysis_type: string;
  ticker: string;
  timestamp: string;
  recommendation: string;
  confidence: number;
  summary: string;
  data: Record<string, any>;
  from_cache: boolean;
  processing_time_ms: number;
}

interface CompositeResult {
  ticker: string;
  analyses: Record<string, AnalysisResult>;
  composite: {
    composite_recommendation: string;
    composite_confidence: number;
    agreement_level: string;
    signal_strength: number;
    individual_scores: Record<string, any>;
  };
  timestamp: string;
}

const ANALYSIS_TYPES = [
  { id: "technical", name: "Citadel Technical", icon: LineChart, description: "Technical indicators & patterns" },
  { id: "dcf_valuation", name: "Morgan Stanley DCF", icon: DollarSign, description: "Discounted cash flow valuation" },
  { id: "risk", name: "Bridgewater Risk", icon: Shield, description: "Portfolio risk assessment" },
  { id: "earnings", name: "JPMorgan Earnings", icon: BarChart3, description: "Earnings analysis" },
  { id: "patterns", name: "RenTech Patterns", icon: Zap, description: "Statistical patterns & edges" },
  { id: "macro", name: "McKinsey Macro", icon: Building2, description: "Macro impact analysis" },
  { id: "competitive", name: "Bain Competitive", icon: Target, description: "Competitive advantage" },
];

const getRecommendationColor = (rec: string) => {
  const r = rec?.toLowerCase() || "";
  if (r.includes("strong_buy") || r.includes("buy")) return "bg-green-500";
  if (r.includes("strong_sell") || r.includes("sell")) return "bg-red-500";
  return "bg-yellow-500";
};

const getRecommendationIcon = (rec: string) => {
  const r = rec?.toLowerCase() || "";
  if (r.includes("buy")) return <TrendingUp className="h-4 w-4" />;
  if (r.includes("sell")) return <TrendingDown className="h-4 w-4" />;
  return <AlertTriangle className="h-4 w-4" />;
};

export default function AIStrategyPage() {
  const [ticker, setTicker] = useState("SPY");
  const [loading, setLoading] = useState(false);
  const [selectedAnalyses, setSelectedAnalyses] = useState<string[]>(["technical", "patterns", "macro"]);
  const [result, setResult] = useState<CompositeResult | null>(null);
  const [singleResult, setSingleResult] = useState<AnalysisResult | null>(null);
  const [activeTab, setActiveTab] = useState("full");

  const apiBase = process.env.NEXT_PUBLIC_BACKEND_URL || "";

  const runFullAnalysis = async () => {
    if (!ticker) {
      toast.error("Please enter a ticker symbol");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${apiBase}/api/v1/ai-strategy/full-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          analyses: selectedAnalyses,
        }),
      });

      if (!response.ok) {
        throw new Error("Analysis failed");
      }

      const data = await response.json();
      setResult(data);
      setSingleResult(null);
      toast.success(`Analysis complete for ${ticker.toUpperCase()}`);
    } catch (error) {
      toast.error("Failed to run analysis");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const runSingleAnalysis = async (analysisType: string) => {
    if (!ticker) {
      toast.error("Please enter a ticker symbol");
      return;
    }

    setLoading(true);
    try {
      const endpoint = analysisType === "dcf_valuation" ? "dcf-valuation" : analysisType;
      const response = await fetch(`${apiBase}/api/v1/ai-strategy/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
        }),
      });

      if (!response.ok) {
        throw new Error("Analysis failed");
      }

      const data = await response.json();
      setSingleResult(data);
      setResult(null);
      toast.success(`${analysisType} analysis complete`);
    } catch (error) {
      toast.error("Failed to run analysis");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const toggleAnalysis = (id: string) => {
    setSelectedAnalyses((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    );
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Brain className="h-8 w-8 text-primary" />
            AI Strategy Suite
          </h1>
          <p className="text-muted-foreground mt-1">
            Institutional-grade analysis powered by Claude AI
          </p>
        </div>
      </div>

      {/* Input Section */}
      <Card>
        <CardHeader>
          <CardTitle>Analyze Symbol</CardTitle>
          <CardDescription>
            Enter a ticker symbol and select analysis types
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Input
              placeholder="Enter ticker (e.g., SPY, AAPL, NVDA)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="max-w-xs"
            />
            <Button onClick={runFullAnalysis} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Brain className="mr-2 h-4 w-4" />
                  Run Full Analysis
                </>
              )}
            </Button>
          </div>

          {/* Analysis Type Selection */}
          <div className="flex flex-wrap gap-2">
            {ANALYSIS_TYPES.map((analysis) => {
              const Icon = analysis.icon;
              const isSelected = selectedAnalyses.includes(analysis.id);
              return (
                <Badge
                  key={analysis.id}
                  variant={isSelected ? "default" : "outline"}
                  className={`cursor-pointer transition-all ${
                    isSelected ? "bg-primary" : "hover:bg-muted"
                  }`}
                  onClick={() => toggleAnalysis(analysis.id)}
                >
                  <Icon className="h-3 w-3 mr-1" />
                  {analysis.name}
                </Badge>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Individual Analysis Buttons */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Analysis</CardTitle>
          <CardDescription>Run individual analysis types</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
            {ANALYSIS_TYPES.map((analysis) => {
              const Icon = analysis.icon;
              return (
                <Button
                  key={analysis.id}
                  variant="outline"
                  size="sm"
                  onClick={() => runSingleAnalysis(analysis.id)}
                  disabled={loading}
                  className="flex flex-col h-20 items-center justify-center gap-1"
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-xs text-center">{analysis.name}</span>
                </Button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  {ticker.toUpperCase()} Analysis Results
                  <Badge className={getRecommendationColor(result.composite.composite_recommendation)}>
                    {getRecommendationIcon(result.composite.composite_recommendation)}
                    {result.composite.composite_recommendation.toUpperCase().replace("_", " ")}
                  </Badge>
                </CardTitle>
                <CardDescription>
                  Composite confidence: {result.composite.composite_confidence.toFixed(0)}% |
                  Agreement: {result.composite.agreement_level} |
                  Signal Strength: {result.composite.signal_strength.toFixed(0)}%
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="composite">
              <TabsList>
                <TabsTrigger value="composite">Composite</TabsTrigger>
                {Object.keys(result.analyses).map((type) => (
                  <TabsTrigger key={type} value={type}>
                    {type.replace("_", " ")}
                  </TabsTrigger>
                ))}
              </TabsList>

              <TabsContent value="composite" className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg bg-muted">
                    <div className="text-sm text-muted-foreground">Recommendation</div>
                    <div className="text-xl font-bold">
                      {result.composite.composite_recommendation.replace("_", " ")}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted">
                    <div className="text-sm text-muted-foreground">Confidence</div>
                    <div className="text-xl font-bold">
                      {result.composite.composite_confidence.toFixed(0)}%
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted">
                    <div className="text-sm text-muted-foreground">Agreement</div>
                    <div className="text-xl font-bold capitalize">
                      {result.composite.agreement_level}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted">
                    <div className="text-sm text-muted-foreground">Signal Strength</div>
                    <div className="text-xl font-bold">
                      {result.composite.signal_strength.toFixed(0)}%
                    </div>
                  </div>
                </div>

                {/* Individual Scores */}
                <div className="space-y-2">
                  <h4 className="font-semibold">Individual Analysis Scores</h4>
                  <div className="space-y-2">
                    {Object.entries(result.composite.individual_scores || {}).map(([type, score]: [string, any]) => (
                      <div key={type} className="flex items-center justify-between p-2 rounded bg-muted/50">
                        <span className="capitalize">{type.replace("_", " ")}</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{score.recommendation}</Badge>
                          <span className="text-sm text-muted-foreground">
                            {score.confidence?.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>

              {Object.entries(result.analyses).map(([type, analysis]) => (
                <TabsContent key={type} value={type}>
                  <div className="space-y-4">
                    <div className="flex items-center gap-4">
                      <Badge className={getRecommendationColor(analysis.recommendation)}>
                        {analysis.recommendation.replace("_", " ")}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        Confidence: {analysis.confidence.toFixed(0)}%
                      </span>
                      {analysis.from_cache && (
                        <Badge variant="outline">Cached</Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {analysis.processing_time_ms}ms
                      </span>
                    </div>

                    <div className="p-4 rounded-lg bg-muted">
                      <h4 className="font-semibold mb-2">Summary</h4>
                      <p>{analysis.summary}</p>
                    </div>

                    <div className="p-4 rounded-lg bg-muted">
                      <h4 className="font-semibold mb-2">Detailed Analysis</h4>
                      <pre className="text-xs overflow-auto max-h-96 whitespace-pre-wrap">
                        {JSON.stringify(analysis.data, null, 2)}
                      </pre>
                    </div>
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Single Analysis Result */}
      {singleResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {ticker.toUpperCase()} - {singleResult.analysis_type.replace("_", " ")}
              <Badge className={getRecommendationColor(singleResult.recommendation)}>
                {singleResult.recommendation.replace("_", " ")}
              </Badge>
            </CardTitle>
            <CardDescription>
              Confidence: {singleResult.confidence.toFixed(0)}% |
              {singleResult.from_cache ? " Cached |" : ""}
              {singleResult.processing_time_ms}ms
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-muted">
              <h4 className="font-semibold mb-2">Summary</h4>
              <p>{singleResult.summary}</p>
            </div>

            <div className="p-4 rounded-lg bg-muted">
              <h4 className="font-semibold mb-2">Detailed Analysis</h4>
              <pre className="text-xs overflow-auto max-h-96 whitespace-pre-wrap">
                {JSON.stringify(singleResult.data, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      {!result && !singleResult && (
        <Card>
          <CardHeader>
            <CardTitle>How It Works</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {ANALYSIS_TYPES.map((analysis) => {
                const Icon = analysis.icon;
                return (
                  <div key={analysis.id} className="p-4 rounded-lg border">
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="h-5 w-5 text-primary" />
                      <h4 className="font-semibold">{analysis.name}</h4>
                    </div>
                    <p className="text-sm text-muted-foreground">{analysis.description}</p>
                  </div>
                );
              })}
            </div>

            <div className="p-4 rounded-lg bg-primary/10 border border-primary/20">
              <h4 className="font-semibold mb-2">SmartFlow Integration</h4>
              <p className="text-sm text-muted-foreground">
                Enable AI Enhancement in SmartFlow settings to automatically boost signal confidence
                when AI analysis agrees with flow sentiment. This adds institutional-grade analysis
                to every SmartFlow signal.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
