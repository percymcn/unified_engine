import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Check, ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';

interface OnboardingPlanSelectionProps {
  onPlanSelected: (plan: 'starter' | 'pro' | 'elite') => void;
  onSkip?: () => void;
}

export function OnboardingPlanSelection({ onPlanSelected, onSkip }: OnboardingPlanSelectionProps) {
  const [selectedPlan, setSelectedPlan] = useState<'starter' | 'pro' | 'elite'>('pro');

  const plans = [
    {
      id: 'starter' as const,
      name: 'Starter',
      price: '$20',
      period: '/month',
      description: 'Perfect for individual traders',
      features: [
        'Connect 1 broker (TradeLocker/ProjectX/MT4/MT5)',
        'BYO (Bring Your Own) strategy',
        'TradingView webhook integration',
        'Basic risk controls',
        'Email support'
      ],
      trial: '3 days or 100 trades',
      cta: 'Start Free Trial'
    },
    {
      id: 'pro' as const,
      name: 'Pro',
      price: '$40',
      period: '/month',
      description: 'For serious traders',
      features: [
        'Connect 2 brokers',
        '1 Fluxeo strategy/indicator access',
        'Priority execution',
        'Advanced analytics',
        'Priority support'
      ],
      trial: '3 days or 100 trades',
      popular: true,
      cta: 'Start Free Trial'
    },
    {
      id: 'elite' as const,
      name: 'Elite',
      price: '$60',
      period: '/month',
      description: 'Maximum trading power',
      features: [
        'Connect 3 brokers',
        'Up to 3 Fluxeo strategies/indicators',
        'Custom strategy build service',
        'Advanced risk tools + API access',
        '24/7 priority support'
      ],
      trial: '3 days or 100 trades',
      cta: 'Start Free Trial'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#001f29] via-[#002b36] to-[#001f29] flex items-center justify-center p-4">
      <div className="w-full max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-white mb-4">
              Choose Your Plan
            </h1>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              All plans include a risk-free trial. Start with 3 days or 100 trades, whichever comes first.
            </p>
          </div>

          {/* Plans Grid */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {plans.map((plan, index) => (
              <motion.div
                key={plan.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card 
                  className={`cursor-pointer transition-all h-full flex flex-col ${
                    selectedPlan === plan.id
                      ? 'bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-[#00C2A8] border-2 shadow-xl shadow-[#00C2A8]/20'
                      : 'bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10 hover:border-[#00C2A8]/50'
                  } ${plan.popular ? 'scale-105' : ''}`}
                  onClick={() => setSelectedPlan(plan.id)}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className="bg-[#00C2A8] text-[#0a0f1a]">Most Popular</Badge>
                    </div>
                  )}
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-white">{plan.name}</CardTitle>
                      {selectedPlan === plan.id && (
                        <div className="w-6 h-6 rounded-full bg-[#00C2A8] flex items-center justify-center">
                          <Check className="w-4 h-4 text-[#0a0f1a]" />
                        </div>
                      )}
                    </div>
                    <CardDescription className="text-gray-400">
                      {plan.description}
                    </CardDescription>
                    <div className="mt-4">
                      <span className="text-white text-4xl">{plan.price}</span>
                      <span className="text-gray-400 text-lg">{plan.period}</span>
                    </div>
                    <p className="text-xs text-[#00C2A8] mt-2">
                      {plan.trial}
                    </p>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    <ul className="space-y-3 mb-6 flex-1">
                      {plan.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-2">
                          <Check className="w-5 h-5 text-[#00C2A8] flex-shrink-0 mt-0.5" />
                          <span className="text-gray-300 text-sm">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              size="lg"
              onClick={() => onPlanSelected(selectedPlan)}
              className="bg-[#00C2A8] text-[#0a0f1a] hover:bg-[#00C2A8]/90 px-8 min-w-[200px]"
            >
              Continue to Setup
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
            {onSkip && (
              <Button
                size="lg"
                variant="ghost"
                onClick={onSkip}
                className="text-gray-400 hover:text-white"
              >
                Skip for now
              </Button>
            )}
          </div>

          {/* Footer Note */}
          <div className="text-center mt-8">
            <p className="text-sm text-gray-500">
              You can upgrade or downgrade your plan at any time from your billing settings.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
