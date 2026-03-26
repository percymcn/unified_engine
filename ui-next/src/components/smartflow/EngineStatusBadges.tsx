'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Zap,
  Brain,
  BarChart3,
  Timer,
  TrendingUp,
  AlertCircle,
} from 'lucide-react';

interface EngineStatusBadgesProps {
  flowEnabled: boolean;
  aiEnhancementEnabled: boolean;
  aiOnlyModeEnabled: boolean;
  // Note: Deterministic and Quick are always running (hardcoded in backend)
}

export function EngineStatusBadges({
  flowEnabled,
  aiEnhancementEnabled,
  aiOnlyModeEnabled,
}: EngineStatusBadgesProps) {
  return (
    <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-violet-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Active Trading Systems
        </CardTitle>
        <CardDescription>
          Multiple engines can run in parallel. Signals are tagged by source.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {/* Flow-Based Engine */}
          {flowEnabled ? (
            <Badge className="bg-green-500 text-white gap-1.5">
              <Zap className="h-3 w-3" />
              Flow Engine: ACTIVE
            </Badge>
          ) : (
            <Badge variant="outline" className="gap-1.5">
              <Zap className="h-3 w-3" />
              Flow Engine: OFF
            </Badge>
          )}

          {/* AI Enhancement (Add-on) */}
          {aiEnhancementEnabled && flowEnabled && (
            <Badge className="bg-violet-500 text-white gap-1.5">
              <Brain className="h-3 w-3" />
              + AI Enhancement
            </Badge>
          )}

          {/* AI-Only 24/7 Engine */}
          {aiOnlyModeEnabled ? (
            <Badge className="bg-purple-500 text-white gap-1.5 animate-pulse">
              <Brain className="h-3 w-3" />
              AI-Only: ACTIVE
            </Badge>
          ) : (
            <Badge variant="outline" className="gap-1.5">
              <Brain className="h-3 w-3" />
              AI-Only: STANDBY
            </Badge>
          )}

          {/* Deterministic Engine (Always Running - Hardcoded) */}
          <Badge className="bg-emerald-600 text-white gap-1.5">
            <BarChart3 className="h-3 w-3" />
            Deterministic: RUNNING
          </Badge>

          {/* Quick Mode (Always Running - Hardcoded) */}
          <Badge className="bg-amber-600 text-white gap-1.5">
            <Timer className="h-3 w-3" />
            Quick Mode: RUNNING
          </Badge>

          {/* Warning if user might not realize all engines are running */}
          {(flowEnabled || aiOnlyModeEnabled) && (
            <Badge variant="outline" className="gap-1.5 border-orange-500 text-orange-500">
              <AlertCircle className="h-3 w-3" />
              3-5 engines active
            </Badge>
          )}
        </div>

        {/* Explanation */}
        <p className="text-xs text-muted-foreground mt-3">
          <strong>Note:</strong> Deterministic and Quick Mode are always running in the background (current limitation).
          Multiple engines can generate signals simultaneously. Check the source engine in signal details.
        </p>
      </CardContent>
    </Card>
  );
}
