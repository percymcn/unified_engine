'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Power, AlertTriangle, Shield, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface KillSwitchProps {
  className?: string;
  variant?: 'compact' | 'full';
}

export function KillSwitch({ className, variant = 'full' }: KillSwitchProps) {
  const [isKilling, setIsKilling] = useState(false);
  const [isPausing, setIsPausing] = useState(false);
  const [isArmed, setIsArmed] = useState(false);
  const { toast } = useToast();

  const handleKillSwitch = async () => {
    console.log('[KillSwitch] Executing flatten all...');
    setIsKilling(true);
    try {
      const response = await fetch('/api/emergency/kill-switch', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'flatten_all' }),
      });

      const result = await response.json();
      console.log('[KillSwitch] Response:', response.status, result);

      if (response.ok) {
        toast({
          title: 'Emergency Kill Switch Activated',
          description: `Flattened ${result.positionsClosed || 0} positions across ${result.accountsAffected || 0} accounts${result.errors?.length ? `. Errors: ${result.errors.length}` : ''}`,
          variant: 'destructive',
        });
        setIsArmed(false);
      } else {
        toast({
          title: 'Kill Switch Failed',
          description: result.error || result.message || 'Unknown error occurred',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('[KillSwitch] Error:', error);
      toast({
        title: 'Kill Switch Failed',
        description: error instanceof Error ? error.message : 'Unable to flatten positions. Check your connections.',
        variant: 'destructive',
      });
    } finally {
      setIsKilling(false);
    }
  };

  const handlePauseAll = async () => {
    console.log('[KillSwitch] Pausing all trading...');
    setIsPausing(true);
    try {
      const response = await fetch('/api/emergency/pause-all', {
        method: 'POST',
        credentials: 'include',
      });

      const result = await response.json();
      console.log('[KillSwitch] Pause response:', response.status, result);

      if (response.ok) {
        toast({
          title: 'All Trading Paused',
          description: result.message || `Signal execution paused for ${result.accountsPaused || 0} accounts.`,
        });
      } else {
        toast({
          title: 'Pause Failed',
          description: result.error || result.message || 'Unable to pause trading.',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('[KillSwitch] Pause error:', error);
      toast({
        title: 'Pause Failed',
        description: error instanceof Error ? error.message : 'Unable to pause trading.',
        variant: 'destructive',
      });
    } finally {
      setIsPausing(false);
    }
  };

  if (variant === 'compact') {
    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="destructive"
            size="sm"
            className={cn('gap-2', className)}
          >
            <Power className="h-4 w-4" />
            Kill Switch
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent className="border-red-500/50">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-500">
              <AlertTriangle className="h-5 w-5" />
              Emergency Kill Switch
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will immediately close ALL open positions across ALL connected accounts.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleKillSwitch}
              className="bg-red-600 hover:bg-red-700"
              disabled={isKilling}
            >
              {isKilling ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Flattening...
                </>
              ) : (
                'FLATTEN ALL POSITIONS'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  }

  return (
    <Card className={cn('cyber-card border-red-500/30', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-red-500" />
          Emergency Controls
          <Badge variant="outline" className="ml-auto text-xs">Enterprise</Badge>
        </CardTitle>
        <CardDescription>
          Account-wide emergency controls for risk management
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Arm/Disarm toggle */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
          <div>
            <p className="text-sm font-medium">Kill Switch Status</p>
            <p className="text-xs text-muted-foreground">
              {isArmed ? 'Armed and ready' : 'Safety engaged'}
            </p>
          </div>
          <Button
            variant={isArmed ? 'destructive' : 'outline'}
            size="sm"
            onClick={() => setIsArmed(!isArmed)}
          >
            {isArmed ? 'ARMED' : 'Arm Kill Switch'}
          </Button>
        </div>

        {/* Kill switch button - no longer requires arming */}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="destructive"
              className="w-full h-14 text-lg gap-3 transition-all"
              disabled={isKilling}
            >
              <Power className="h-6 w-6" />
              {isKilling ? 'FLATTENING...' : 'EMERGENCY FLATTEN ALL'}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="border-red-500/50">
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2 text-red-500">
                <AlertTriangle className="h-5 w-5" />
                Confirm Emergency Flatten
              </AlertDialogTitle>
              <AlertDialogDescription className="space-y-2">
                <p>This will immediately:</p>
                <ul className="list-disc list-inside text-sm">
                  <li>Close ALL open positions on ALL accounts</li>
                  <li>Cancel ALL pending orders</li>
                  <li>Pause signal execution</li>
                </ul>
                <p className="font-medium text-red-400 mt-2">
                  This action cannot be undone!
                </p>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleKillSwitch}
                className="bg-red-600 hover:bg-red-700"
              >
                {isKilling ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Executing...
                  </>
                ) : (
                  'CONFIRM FLATTEN ALL'
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Pause trading button */}
        <Button
          variant="outline"
          className="w-full"
          onClick={handlePauseAll}
          disabled={isPausing}
        >
          {isPausing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Pausing...
            </>
          ) : (
            <>
              <Power className="h-4 w-4 mr-2" />
              Pause All Trading
            </>
          )}
        </Button>

        <p className="text-xs text-muted-foreground text-center">
          Emergency controls bypass all guards and execute immediately
        </p>
      </CardContent>
    </Card>
  );
}
