'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AccountSelector } from './account-selector';
import { BrokerType, BROKER_DISPLAY_NAMES } from '@/types/account';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, Info } from 'lucide-react';

interface BrokerWithAccounts {
  brokerType: BrokerType;
  accountCount: number;
  selectedCount: number;
}

/**
 * Component that displays account selection per broker type.
 * Allows users to manage which accounts receive signals for each connected broker.
 */
export function BrokerAccountSelection() {
  const [brokers, setBrokers] = useState<BrokerWithAccounts[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedBroker, setExpandedBroker] = useState<BrokerType | null>(null);

  // Fetch connected brokers with account counts
  useEffect(() => {
    fetchBrokerData();
  }, []);

  const fetchBrokerData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/accounts');

      if (!response.ok) {
        throw new Error('Failed to fetch accounts');
      }

      const data = await response.json();
      const accounts = Array.isArray(data) ? data : data.accounts || [];

      // Group accounts by broker and count
      const brokerMap = new Map<BrokerType, { total: number; selected: number }>();

      for (const account of accounts) {
        const broker = account.broker as BrokerType;
        const current = brokerMap.get(broker) || { total: 0, selected: 0 };
        current.total++;
        // is_signal_enabled indicates if account receives signals
        if (account.is_signal_enabled !== false) {
          current.selected++;
        }
        brokerMap.set(broker, current);
      }

      // Convert to array
      const brokerList: BrokerWithAccounts[] = Array.from(brokerMap.entries()).map(
        ([brokerType, counts]) => ({
          brokerType,
          accountCount: counts.total,
          selectedCount: counts.selected,
        })
      );

      setBrokers(brokerList);
    } catch (error) {
      console.error('Error fetching broker data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Handle selection change to update counts
  const handleSelectionChange = (brokerType: BrokerType, accountId: number, selected: boolean) => {
    setBrokers(prev =>
      prev.map(b =>
        b.brokerType === brokerType
          ? {
              ...b,
              selectedCount: selected ? b.selectedCount + 1 : b.selectedCount - 1,
            }
          : b
      )
    );
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64 mt-2" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2].map(i => (
              <Skeleton key={i} className="h-16 w-full rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (brokers.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5" />
            Signal Recipients
          </CardTitle>
          <CardDescription>
            Select which accounts should receive trading signals.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-muted-foreground">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No broker accounts connected yet.</p>
            <p className="text-sm mt-1">Add a broker account to manage signal routing.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5" />
            Signal Recipients
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-4 w-4 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-xs">
                <p>
                  Select which accounts should receive trading signals. Deselected accounts
                  will not execute trades from incoming signals.
                </p>
              </TooltipContent>
            </Tooltip>
          </CardTitle>
          <CardDescription>
            Manage signal routing for each connected broker.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {brokers.map(broker => (
            <Collapsible
              key={broker.brokerType}
              open={expandedBroker === broker.brokerType}
              onOpenChange={(open) =>
                setExpandedBroker(open ? broker.brokerType : null)
              }
            >
              <CollapsibleTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-between h-auto py-3 px-4"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-medium">
                      {BROKER_DISPLAY_NAMES[broker.brokerType]}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {broker.selectedCount} of {broker.accountCount} accounts selected
                    </span>
                  </div>
                  {expandedBroker === broker.brokerType ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="pt-3">
                <AccountSelector
                  brokerType={broker.brokerType}
                  onSelectionChange={(accountId, selected) =>
                    handleSelectionChange(broker.brokerType, accountId, selected)
                  }
                  showHeader={false}
                  compact={true}
                />
              </CollapsibleContent>
            </Collapsible>
          ))}
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
