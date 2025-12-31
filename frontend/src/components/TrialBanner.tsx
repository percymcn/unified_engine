/**
 * TrialBanner Component
 * Shows remaining trial trades/days with upgrade CTA
 * Displays at the top of dashboard for trialing users
 */

import { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { Clock, TrendingUp, Zap, X } from 'lucide-react';
import { enhancedApiClient, BillingStatus, BillingUsage } from '../utils/api-client-enhanced';
import { toast } from 'sonner@2.0.3';

export function TrialBanner() {
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [usage, setUsage] = useState<BillingUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [status, usageData] = await Promise.all([
        enhancedApiClient.getBillingStatus(),
        enhancedApiClient.getBillingUsage(),
      ]);
      
      setBillingStatus(status);
      setUsage(usageData);
    } catch (error) {
      console.error('Failed to load trial data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async () => {
    try {
      toast.info('Opening upgrade options...');
      // Navigate to billing page or open upgrade modal
      window.location.href = '/billing'; // Or use router navigation
    } catch (error) {
      console.error('Upgrade error:', error);
      toast.error('Failed to open upgrade options');
    }
  };

  if (loading || !billingStatus || !usage) {
    return null;
  }

  // Only show for trialing users
  if (billingStatus.status !== 'trialing') {
    return null;
  }

  if (dismissed) {
    return null;
  }

  const tradesUsed = usage.trades_count;
  const tradesLimit = usage.trades_limit;
  const tradesRemaining = Math.max(0, tradesLimit - tradesUsed);
  const tradesProgress = (tradesUsed / tradesLimit) * 100;

  const daysRemaining = usage.days_remaining || 0;
  
  // Show warning when trial is almost over
  const isLowTrades = tradesRemaining <= 20;
  const isLowDays = daysRemaining <= 1;
  const showWarning = isLowTrades || isLowDays;

  return (
    <Card 
      className={`mb-6 border-2 ${
        showWarning 
          ? 'border-orange-500 bg-gradient-to-r from-orange-950/20 to-yellow-950/20' 
          : 'border-[#0EA5E9] bg-gradient-to-r from-blue-950/20 to-cyan-950/20'
      }`}
    >
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4 flex-1">
            {/* Icon */}
            <div className={`p-3 rounded-lg ${
              showWarning ? 'bg-orange-500/20' : 'bg-[#0EA5E9]/20'
            }`}>
              {showWarning ? (
                <Clock className="w-6 h-6 text-orange-400" />
              ) : (
                <Zap className="w-6 h-6 text-[#0EA5E9]" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h3 className={`text-white ${showWarning ? 'text-orange-300' : ''}`}>
                  {showWarning ? 'Trial Ending Soon!' : 'Trial Active'}
                </h3>
                <span className="text-xs px-2 py-1 rounded-full bg-[#0EA5E9]/20 text-[#0EA5E9] border border-[#0EA5E9]/30">
                  {billingStatus.plan.toUpperCase()}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-3">
                {/* Trades Remaining */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400">Trades</span>
                    <span className={`text-sm ${isLowTrades ? 'text-orange-400' : 'text-white'}`}>
                      {tradesRemaining} / {tradesLimit}
                    </span>
                  </div>
                  <Progress 
                    value={tradesProgress} 
                    className={`h-1.5 ${isLowTrades ? 'bg-orange-900/30' : 'bg-gray-800'}`}
                  />
                </div>

                {/* Days Remaining */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400">Days Left</span>
                    <span className={`text-sm ${isLowDays ? 'text-orange-400' : 'text-white'}`}>
                      {daysRemaining} {daysRemaining === 1 ? 'day' : 'days'}
                    </span>
                  </div>
                  <Progress 
                    value={(daysRemaining / 3) * 100} 
                    className={`h-1.5 ${isLowDays ? 'bg-orange-900/30' : 'bg-gray-800'}`}
                  />
                </div>
              </div>

              <p className="text-xs text-gray-400 mb-3">
                {showWarning ? (
                  <span className="text-orange-300">
                    Your trial ends when you hit 100 trades or 3 days, whichever comes first. 
                    Upgrade now to continue trading without interruption.
                  </span>
                ) : (
                  <>
                    Your trial includes {tradesLimit} trades or {usage.days_remaining} days, whichever comes first. 
                    Upgrade anytime to unlock unlimited trading.
                  </>
                )}
              </p>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="bg-[#0EA5E9] hover:bg-[#0EA5E9]/90 text-white"
                  onClick={handleUpgrade}
                >
                  <TrendingUp className="w-4 h-4 mr-2" />
                  {showWarning ? 'Upgrade Now' : 'View Plans'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-gray-400 hover:text-white"
                  onClick={() => setDismissed(true)}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </div>

          {/* Close Button */}
          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-6 p-0 text-gray-400 hover:text-white -mt-1"
            onClick={() => setDismissed(true)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}

/**
 * Compact version for sidebar/header
 */
export function TrialBadge() {
  const [usage, setUsage] = useState<BillingUsage | null>(null);

  useEffect(() => {
    loadUsage();
  }, []);

  const loadUsage = async () => {
    try {
      const usageData = await enhancedApiClient.getBillingUsage();
      setUsage(usageData);
    } catch (error) {
      console.error('Failed to load usage:', error);
    }
  };

  if (!usage || !usage.trial_trades_remaining) {
    return null;
  }

  const tradesRemaining = usage.trial_trades_remaining;
  const isLow = tradesRemaining <= 20;

  return (
    <div className={`px-3 py-1.5 rounded-full text-xs ${
      isLow 
        ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' 
        : 'bg-[#0EA5E9]/20 text-[#0EA5E9] border border-[#0EA5E9]/30'
    }`}>
      <Clock className="w-3 h-3 inline mr-1" />
      {tradesRemaining} trades left
    </div>
  );
}
