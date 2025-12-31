import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Check, ExternalLink } from 'lucide-react';
import { useUser } from '../contexts/UserContext';
import { getStripeCheckoutUrl, getStripePortalUrl, updateSubscription, cancelSubscription } from '../utils/stripe-helpers';
import { toast } from 'sonner@2.0.3';

export function BillingPortal() {
  const { user, setUser } = useUser();
  const currentPlan = user?.plan || 'pro'; // Default to 'pro' if not set
  const [loading, setLoading] = useState(false);

  const plans = [
    {
      id: 'starter',
      name: 'Starter',
      price: 20,
      period: 'month',
      trial: true,
      features: [
        'Connect 1 broker',
        'TradeLocker/ProjectX/MT4/MT5',
        'BYO strategy',
        'TradingView webhooks',
        'Email support'
      ],
      current: currentPlan === 'starter'
    },
    {
      id: 'pro',
      name: 'Pro',
      price: 40,
      period: 'month',
      trial: true,
      features: [
        'Connect 2 brokers',
        '1 Fluxeo strategy/indicator',
        'Priority execution',
        'Advanced risk controls',
        'Unlimited webhooks',
        'Priority support',
        'Real-time notifications'
      ],
      current: currentPlan === 'pro',
      popular: true
    },
    {
      id: 'elite',
      name: 'Elite',
      price: 60,
      period: 'month',
      trial: true,
      features: [
        'Connect 3 brokers',
        'Up to 3 Fluxeo strategies',
        'Custom build service',
        'Advanced risk tools',
        'Full API access',
        'Dedicated support',
        'Advanced analytics',
        'White-label options'
      ],
      current: currentPlan === 'elite'
    }
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-white mb-2">Billing & Subscription</h2>
        <p className="text-gray-400 text-sm">
          All plans include the same trial: <span className="text-[#00ffc2]">3 days or 100 trades</span> (whichever comes first)
        </p>
      </div>

      {/* Available Plans */}
      <div>
        <h3 className="text-white mb-4">Available Plans</h3>
        <div className="grid grid-cols-3 gap-6">
          {plans.map((plan) => (
            <Card 
              key={plan.id}
              className={`bg-[#001f29] ${
                plan.current 
                  ? 'border-[#00ffc2] border-2' 
                  : 'border-gray-800'
              } transition-all hover:border-[#00ffc2]/50`}
            >
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between mb-3">
                  <CardTitle className="text-white text-lg">
                    {plan.name}
                  </CardTitle>
                  {plan.popular && (
                    <Badge className="bg-[#00ffc2] text-[#002b36] text-xs px-2 py-0.5">
                      Popular
                    </Badge>
                  )}
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-white text-3xl font-semibold">
                    ${plan.price}
                  </span>
                  <span className="text-gray-400 text-sm">
                    / {plan.period}
                  </span>
                </div>
                {plan.trial && (
                  <div className="mt-2">
                    <Badge variant="outline" className="border-blue-400 text-blue-400 text-xs">
                      Trial
                    </Badge>
                  </div>
                )}
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* Features List */}
                <ul className="space-y-2.5">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-2.5">
                      <Check className="w-4 h-4 text-[#00ffc2] mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-gray-300 leading-tight">
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                <div className="pt-2">
                  {plan.current ? (
                    <Button 
                      className="w-full bg-gray-700 text-gray-400 cursor-not-allowed"
                      disabled
                    >
                      Current Plan
                    </Button>
                  ) : (
                    <Button 
                      className="w-full bg-[#00ffc2] text-[#002b36] hover:bg-[#00ffc2]/90"
                      onClick={async () => {
                        setLoading(true);
                        try {
                          const success = await updateSubscription(plan.id as 'starter' | 'pro' | 'elite');
                          if (success) {
                            // Redirect to Stripe Checkout
                            const checkoutUrl = getStripeCheckoutUrl(plan.id as 'starter' | 'pro' | 'elite', user?.email);
                            window.location.href = checkoutUrl;
                          } else {
                            toast.error('Failed to initiate checkout. Please try again.');
                          }
                        } catch (error) {
                          console.error('Checkout error:', error);
                          toast.error('An error occurred. Please try again.');
                        } finally {
                          setLoading(false);
                        }
                      }}
                      disabled={loading}
                    >
                      {plan.id === 'starter' ? 'Start Trial' : 'Upgrade'}
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Current Subscription Details */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Current Subscription</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-gray-400 mb-1">Plan</p>
              <p className="text-white capitalize">{currentPlan}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400 mb-1">Billing Cycle</p>
              <p className="text-white">Monthly</p>
            </div>
            <div>
              <p className="text-sm text-gray-400 mb-1">Next Billing Date</p>
              <p className="text-white">November 14, 2025</p>
            </div>
            <div>
              <p className="text-sm text-gray-400 mb-1">Amount</p>
              <p className="text-white">
                ${plans.find(p => p.id === currentPlan)?.price || 40}.00
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 mb-1">Payment Method</p>
                <p className="text-white">Visa ending in 4242</p>
              </div>
              <Button 
                variant="outline" 
                className="border-gray-700 text-gray-300"
                onClick={async () => {
                  setLoading(true);
                  try {
                    toast.info('Opening payment update portal...');
                    const portalUrl = await getStripePortalUrl();
                    window.location.href = portalUrl;
                  } catch (error) {
                    console.error('Failed to open payment portal:', error);
                    toast.error('Failed to open payment update portal');
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
              >
                Update Payment
              </Button>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-800 flex gap-3">
            <Button 
              variant="outline" 
              className="border-gray-700 text-gray-300"
              onClick={async () => {
                if (window.confirm('Are you sure you want to cancel your subscription?')) {
                  setLoading(true);
                  try {
                    const success = await cancelSubscription();
                    if (success) {
                      toast.success('Subscription canceled successfully');
                    } else {
                      toast.error('Failed to cancel subscription');
                    }
                  } catch (error) {
                    toast.error('An error occurred');
                  } finally {
                    setLoading(false);
                  }
                }
              }}
              disabled={loading}
            >
              Cancel Subscription
            </Button>
            <Button 
              variant="outline" 
              className="border-gray-700 text-gray-300"
              onClick={async () => {
                setLoading(true);
                try {
                  const portalUrl = await getStripePortalUrl();
                  window.location.href = portalUrl;
                } catch (error) {
                  toast.error('Failed to open billing portal');
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading}
            >
              Manage Billing
              <ExternalLink className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Trial Information */}
      <Card className="bg-[#001f29] border-blue-800">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-950 flex items-center justify-center flex-shrink-0">
              <Check className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h4 className="text-white mb-1">Trial Period Information</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                All plans include the same trial period: <span className="text-[#00ffc2] font-medium">3 days or 100 trades</span> (whichever comes first). 
                Your trial counter starts when you register an account and connects your first broker. 
                You'll receive a notification when you reach 80% of either limit.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
