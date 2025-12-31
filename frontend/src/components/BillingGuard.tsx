/**
 * BillingGuard Component
 * Blocks trading actions when billing status is past_due or canceled
 * Shows prominent warning banner and reactivation button
 */

import { useState, useEffect, ReactNode } from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { AlertTriangle, CreditCard, X } from 'lucide-react';
import { enhancedApiClient, BillingStatus } from '../utils/api-client-enhanced';
import { toast } from 'sonner@2.0.3';

interface BillingGuardProps {
  children: ReactNode;
  blockInteraction?: boolean;
  showBanner?: boolean;
}

export function BillingGuard({
  children,
  blockInteraction = true,
  showBanner = true,
}: BillingGuardProps) {
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    loadBillingStatus();
  }, []);

  const loadBillingStatus = async () => {
    try {
      const status = await enhancedApiClient.getBillingStatus();
      setBillingStatus(status);
    } catch (error) {
      console.error('Failed to load billing status:', error);
      // Don't block on error - assume status is OK
      setBillingStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const handleReactivate = async () => {
    try {
      const checkout = await enhancedApiClient.createCheckout({
        price_id: billingStatus?.price_id || '',
        success_url: window.location.href,
        cancel_url: window.location.href,
      });
      
      window.location.href = checkout.url;
    } catch (error) {
      console.error('Checkout error:', error);
      toast.error('Failed to start checkout process');
    }
  };

  const handleUpdatePayment = () => {
    // Open Stripe Customer Portal
    toast.info('Opening payment portal...');
    // In production, this would redirect to Stripe portal
  };

  if (loading) {
    return <>{children}</>;
  }

  const isBlocked = billingStatus && ['past_due', 'canceled', 'incomplete'].includes(billingStatus.status);

  if (!isBlocked) {
    return <>{children}</>;
  }

  return (
    <div className="relative">
      {/* Warning Banner */}
      {showBanner && !dismissed && (
        <Alert className="mb-6 border-red-700 bg-red-950/20">
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <AlertTitle className="text-red-400 flex items-center justify-between">
            <span>
              {billingStatus.status === 'past_due' && 'Payment Past Due'}
              {billingStatus.status === 'canceled' && 'Subscription Canceled'}
              {billingStatus.status === 'incomplete' && 'Payment Required'}
            </span>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 w-6 p-0 text-gray-400 hover:text-white"
              onClick={() => setDismissed(true)}
            >
              <X className="h-4 w-4" />
            </Button>
          </AlertTitle>
          <AlertDescription className="text-gray-300 mt-2">
            {billingStatus.status === 'past_due' && (
              <>
                Your payment method failed. Please update your payment information to continue trading.
              </>
            )}
            {billingStatus.status === 'canceled' && (
              <>
                Your subscription has been canceled. Reactivate to resume trading and access all features.
              </>
            )}
            {billingStatus.status === 'incomplete' && (
              <>
                Your subscription setup is incomplete. Please complete payment to activate your account.
              </>
            )}
          </AlertDescription>
          <div className="flex gap-2 mt-4">
            {billingStatus.status === 'past_due' && (
              <Button
                size="sm"
                className="bg-red-600 hover:bg-red-700 text-white"
                onClick={handleUpdatePayment}
              >
                <CreditCard className="w-4 h-4 mr-2" />
                Update Payment Method
              </Button>
            )}
            {(billingStatus.status === 'canceled' || billingStatus.status === 'incomplete') && (
              <Button
                size="sm"
                className="bg-[#0EA5E9] hover:bg-[#0EA5E9]/90 text-white"
                onClick={handleReactivate}
              >
                <CreditCard className="w-4 h-4 mr-2" />
                Reactivate Subscription
              </Button>
            )}
          </div>
        </Alert>
      )}

      {/* Content with optional interaction blocking */}
      <div className={blockInteraction ? 'pointer-events-none opacity-60' : ''}>
        {children}
      </div>

      {/* Overlay for blocked areas */}
      {blockInteraction && (
        <div className="absolute inset-0 bg-transparent z-10 cursor-not-allowed" />
      )}
    </div>
  );
}

/**
 * Hook to check billing status programmatically
 */
export function useBillingStatus() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const billingStatus = await enhancedApiClient.getBillingStatus();
      setStatus(billingStatus);
    } catch (error) {
      console.error('Failed to load billing status:', error);
    } finally {
      setLoading(false);
    }
  };

  const isBlocked = status && ['past_due', 'canceled', 'incomplete'].includes(status.status);
  const isActive = status?.status === 'active';
  const isTrialing = status?.status === 'trialing';

  return {
    status,
    loading,
    isBlocked,
    isActive,
    isTrialing,
    refresh: loadStatus,
  };
}
