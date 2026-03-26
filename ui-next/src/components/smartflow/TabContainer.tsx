'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Activity,
  LineChart,
  TestTube,
  Settings,
  Brain,
  BarChart3,
} from 'lucide-react';

interface TabContainerProps {
  liveSignalsContent: React.ReactNode;
  analyticsContent: React.ReactNode;
  forwardTestContent: React.ReactNode;
  configContent: React.ReactNode;
  defaultTab?: string;
}

export function TabContainer({
  liveSignalsContent,
  analyticsContent,
  forwardTestContent,
  configContent,
  defaultTab = 'live-signals',
}: TabContainerProps) {
  return (
    <Tabs defaultValue={defaultTab} className="w-full">
      <TabsList className="grid w-full grid-cols-4 mb-6 h-auto p-1">
        <TabsTrigger value="live-signals" className="flex items-center gap-2 py-3">
          <Activity className="h-4 w-4" />
          <span className="hidden sm:inline">Live Signals</span>
          <span className="sm:hidden">Signals</span>
        </TabsTrigger>
        <TabsTrigger value="analytics" className="flex items-center gap-2 py-3">
          <LineChart className="h-4 w-4" />
          <span className="hidden sm:inline">Analytics</span>
          <span className="sm:hidden">Stats</span>
        </TabsTrigger>
        <TabsTrigger value="forward-test" className="flex items-center gap-2 py-3">
          <TestTube className="h-4 w-4" />
          <span className="hidden sm:inline">Forward Test</span>
          <span className="sm:hidden">Test</span>
        </TabsTrigger>
        <TabsTrigger value="config" className="flex items-center gap-2 py-3">
          <Settings className="h-4 w-4" />
          <span className="hidden sm:inline">Configuration</span>
          <span className="sm:hidden">Config</span>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="live-signals" className="space-y-4">
        {liveSignalsContent}
      </TabsContent>

      <TabsContent value="analytics" className="space-y-4">
        {analyticsContent}
      </TabsContent>

      <TabsContent value="forward-test" className="space-y-4">
        {forwardTestContent}
      </TabsContent>

      <TabsContent value="config" className="space-y-4">
        {configContent}
      </TabsContent>
    </Tabs>
  );
}
