import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Check, Zap, Link2, Settings, TrendingUp, Gauge, Users, LayoutDashboard, RefreshCw, ChevronDown, ArrowDown } from 'lucide-react';
import { TradeFlowLogo } from './TradeFlowLogo';
import { Chatbot } from './Chatbot';
import { motion } from 'motion/react';
import { useState, useEffect } from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from './ui/accordion';

interface LandingPageProps {
  onNavigateToLogin: () => void;
  onNavigateToSignup: () => void;
  onNavigateToAdmin?: () => void;
}

export function LandingPage({ onNavigateToLogin, onNavigateToSignup, onNavigateToAdmin }: LandingPageProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((oldProgress) => {
        if (oldProgress === 100) {
          return 0;
        }
        const diff = Math.random() * 10;
        return Math.min(oldProgress + diff, 100);
      });
    }, 500);

    return () => {
      clearInterval(timer);
    };
  }, []);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const howItWorksSteps = [
    {
      number: '1',
      icon: Link2,
      title: 'Connect your TradingView strategy',
      description: 'Link your TradingView alerts to TradeFlow in seconds. No coding, no EA setup required.'
    },
    {
      number: '2',
      icon: Settings,
      title: 'Set risk rules & position size',
      description: 'TradeFlow auto-calculates lot size based on your account balance and stop loss. Stay in control.'
    },
    {
      number: '3',
      icon: TrendingUp,
      title: 'Watch trades execute in real time',
      description: 'Your trades go live on demo instantly. Monitor everything from one unified dashboard.'
    }
  ];

  const capabilities = [
    {
      icon: Zap,
      title: 'Ultra-Fast Execution',
      description: 'Millisecond-fast signal to fill. Lightning-speed order execution.'
    },
    {
      icon: Gauge,
      title: 'Smart Position Sizing',
      description: 'Auto lot size calculation based on risk-to-reward ratio.'
    },
    {
      icon: Users,
      title: 'Full Account Support',
      description: 'Live + Demo + Prop Firms. Compatible with any broker offering API execution.'
    },
    {
      icon: LayoutDashboard,
      title: 'Unified Dashboard',
      description: 'Manage all accounts and strategies from one beautiful interface.'
    },
    {
      icon: RefreshCw,
      title: 'Instant Sync',
      description: 'View open positions, equity, and profit in real time across all accounts.'
    }
  ];

  const plans = [
    {
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
      cta: 'Start Trial'
    },
    {
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
      cta: 'Start Trial'
    },
    {
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
      cta: 'Start Trial'
    }
  ];

  const integrations = [
    { name: 'TradeLocker', requiresEA: false },
    { name: 'Topstep (ProjectX)', requiresEA: false },
    { name: 'TruForex', requiresEA: false },
    { name: 'MetaTrader 4', requiresEA: true },
    { name: 'MetaTrader 5', requiresEA: true }
  ];

  const faqs = [
    {
      question: 'How does the trial work?',
      answer: 'Your trial lasts 3 days OR 100 trades, whichever comes first. No credit card required to start. You get full access to all features of your selected plan during the trial period.'
    },
    {
      question: 'Do I need the TradeFlow EA for MT4/MT5?',
      answer: 'Yes, MT4 and MT5 require the TradeFlow EA (Expert Advisor) installation. After signup, download it from your dashboard, install it in your MetaTrader platform, and configure your API credentials. TradeLocker, Topstep, and TruForex work via direct API integration without requiring an EA.'
    },
    {
      question: 'Can I use my own TradingView strategy?',
      answer: 'Absolutely! TradeFlow works with your own TradingView scripts. Just set up the webhook in TradingView and connect it to your TradeFlow API key. All plans support BYO (Bring Your Own) strategies.'
    },
    {
      question: 'What are Fluxeo strategies and indicators?',
      answer: 'Fluxeo strategies are AI-built, ready-made TradingView strategies and indicators created by our team. Pro plans get access to 1 strategy, and Elite plans get up to 3, plus custom build services.'
    },
    {
      question: 'Which brokers are supported?',
      answer: 'We support TradeLocker, Topstep (ProjectX), TruForex, MetaTrader 4, and MetaTrader 5. Note that MT4/MT5 require our EA installation, while others connect via API.'
    },
    {
      question: 'How do I get support?',
      answer: 'Email us at support@fluxeo.net. Starter plans get email support with 24-hour response time. Pro plans get priority support, and Elite plans get 24/7 priority support with dedicated assistance.'
    }
  ];

  return (
    <div className="min-h-screen bg-[#0a0f1a]">
      {/* Header */}
      <header className="border-b border-white/5 bg-[#0a0f1a]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 md:px-6 py-4">
          <div className="flex items-center justify-between">
            <TradeFlowLogo size="md" />
            
            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-8">
              <button 
                onClick={() => scrollToSection('features')}
                className="text-gray-400 hover:text-white transition-colors text-sm"
              >
                Features
              </button>
              <button 
                onClick={() => scrollToSection('pricing')}
                className="text-gray-400 hover:text-white transition-colors text-sm"
              >
                Pricing
              </button>
              <button 
                onClick={() => scrollToSection('integrations')}
                className="text-gray-400 hover:text-white transition-colors text-sm"
              >
                Integrations
              </button>
            </nav>

            <div className="flex items-center gap-3">
              <Button 
                variant="ghost" 
                onClick={onNavigateToLogin}
                className="text-gray-300 hover:text-white hover:bg-white/5"
              >
                Login
              </Button>
              <Button 
                onClick={onNavigateToSignup}
                className="bg-[#00C2A8] text-[#0a0f1a] hover:bg-[#00C2A8]/90 font-semibold"
              >
                Start Free Trial
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 md:px-6 py-16 md:py-24">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left Side - Content */}
          <div>
            <Badge className="mb-6 bg-[#00C2A8]/10 text-[#00C2A8] border-[#00C2A8]/30 inline-flex items-center gap-2">
              <Zap className="w-3 h-3" />
              Lightning-Fast Execution
            </Badge>
            
            <h1 className="text-4xl md:text-5xl lg:text-6xl mb-6 leading-tight">
              <span className="text-white">Your </span>
              <span className="text-[#00C2A8]">TradingView</span>
              <br />
              <span className="text-white">strategy — </span>
              <br />
              <span className="text-white">executed</span>
              <br />
              <span className="text-white">instantly.</span>
            </h1>

            <p className="text-lg text-gray-400 mb-8 max-w-xl">
              Automate entries, stops, and targets across your brokers and prop-firm accounts in seconds.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 mb-6">
              <Button 
                size="lg"
                onClick={onNavigateToSignup}
                className="bg-[#00C2A8] text-[#0a0f1a] hover:bg-[#00C2A8]/90 text-base px-8 font-semibold"
              >
                Start Free Trial
              </Button>
              <Button 
                size="lg"
                variant="outline"
                className="border-white/10 text-white hover:bg-white/5 text-base px-8"
              >
                Watch How It Works
              </Button>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-2">
                <Check className="w-4 h-4 text-[#00C2A8]" />
                No coding required
              </span>
              <span className="flex items-center gap-2">
                <Check className="w-4 h-4 text-[#00C2A8]" />
                3 days or 100 trades free
              </span>
            </div>
          </div>

          {/* Right Side - Animated Flow */}
          <div className="hidden lg:block">
            <div className="space-y-6">
              {/* TradingView Alert Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <Badge className="bg-[#00C2A8]/20 text-[#00C2A8] border-[#00C2A8]/30">
                        TradingView Alert
                      </Badge>
                      <span className="text-xs text-gray-500">Just now</span>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Entry:</span>
                        <span className="text-white font-semibold">$25,500</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Stop Loss:</span>
                        <span className="text-red-400">$25,450</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Take Profit:</span>
                        <span className="text-green-400">$48,020</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Arrow Down */}
              <motion.div 
                className="flex justify-center"
                animate={{ y: [0, 10, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <ArrowDown className="w-6 h-6 text-[#00C2A8]" />
              </motion.div>

              {/* TradeFlow Processing Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
              >
                <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-[#00C2A8]/30">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-3">
                      <Badge className="bg-[#00C2A8]/20 text-[#00C2A8] border-[#00C2A8]/30">
                        TradeFlow Processing
                      </Badge>
                    </div>
                    <div className="relative h-2 bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        className="absolute top-0 left-0 h-full bg-gradient-to-r from-[#00C2A8] to-[#A5FFCE]"
                        style={{ width: `${progress}%` }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-2">~203ms</p>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Arrow Down */}
              <motion.div 
                className="flex justify-center"
                animate={{ y: [0, 10, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: 0.75 }}
              >
                <ArrowDown className="w-6 h-6 text-[#00C2A8]" />
              </motion.div>

              {/* Trade Executed Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 }}
              >
                <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10">
                  <CardContent className="p-6">
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30 mb-3">
                      Trade Executed
                    </Badge>
                    <p className="text-sm text-gray-400">
                      Position opened on <span className="text-white">MT5 Live Account</span>
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="features" className="container mx-auto px-4 md:px-6 py-16 md:py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl mb-4 text-white">
            How It Works
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Three simple steps to automate your trading strategy
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {howItWorksSteps.map((step, index) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10 h-full relative overflow-hidden group hover:border-[#00C2A8]/30 transition-all">
                  <div className="absolute top-4 right-4">
                    <div className="w-12 h-12 rounded-full bg-[#00C2A8]/10 flex items-center justify-center">
                      <span className="text-2xl font-bold text-[#00C2A8]">{step.number}</span>
                    </div>
                  </div>
                  <CardContent className="p-8 pt-20">
                    <Icon className="w-12 h-12 text-[#00C2A8] mb-6" />
                    <h3 className="text-xl text-white mb-3 font-semibold">
                      {step.title}
                    </h3>
                    <p className="text-gray-400 leading-relaxed">
                      {step.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Platform Capabilities Section */}
      <section className="container mx-auto px-4 md:px-6 py-16 md:py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl mb-4 text-white">
            Platform Capabilities
          </h2>
          <p className="text-gray-400 text-lg max-w-3xl mx-auto">
            Everything you need for automated trading, built for speed and reliability
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {capabilities.map((capability, index) => {
            const Icon = capability.icon;
            return (
              <motion.div
                key={capability.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10 h-full hover:border-[#00C2A8]/30 transition-all group">
                  <CardContent className="p-6">
                    <div className="w-12 h-12 rounded-lg bg-[#00C2A8]/10 flex items-center justify-center mb-4 group-hover:bg-[#00C2A8]/20 transition-colors">
                      <Icon className="w-6 h-6 text-[#00C2A8]" />
                    </div>
                    <h3 className="text-lg text-white mb-2 font-semibold">
                      {capability.title}
                    </h3>
                    <p className="text-gray-400 text-sm leading-relaxed">
                      {capability.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="container mx-auto px-4 md:px-6 py-16 md:py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl mb-4 text-white">
            Simple, Transparent Pricing
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto mb-2">
            Choose the plan that fits your trading needs. All plans include a risk-free trial.
          </p>
          <p className="text-sm text-gray-500 max-w-2xl mx-auto">
            TradeFlow works with your own TradingView scripts or our ready-made AI-built strategies and indicators.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card 
                className={`bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10 relative h-full flex flex-col ${
                  plan.popular ? 'border-[#00C2A8] shadow-xl shadow-[#00C2A8]/20 scale-105' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-[#00C2A8] text-[#0a0f1a] font-semibold">Most Popular</Badge>
                  </div>
                )}
                <CardHeader>
                  <CardTitle className="text-white text-2xl">{plan.name}</CardTitle>
                  <CardDescription className="text-gray-400">
                    {plan.description}
                  </CardDescription>
                  <div className="mt-4">
                    <span className="text-4xl lg:text-5xl text-white font-bold">{plan.price}</span>
                    <span className="text-gray-400 text-lg">{plan.period}</span>
                  </div>
                  <p className="text-xs text-[#00C2A8] mt-2 font-medium">
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
                  <Button 
                    className={`w-full ${
                      plan.popular 
                        ? 'bg-[#00C2A8] text-[#0a0f1a] hover:bg-[#00C2A8]/90 font-semibold' 
                        : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                    }`}
                    onClick={onNavigateToSignup}
                  >
                    {plan.cta}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Integrations Section */}
      <section id="integrations" className="container mx-auto px-4 md:px-6 py-16 md:py-24">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl lg:text-5xl mb-4 text-white">
            Supported Brokers & Platforms
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Connect to your favorite brokers seamlessly
          </p>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 max-w-5xl mx-auto mb-6">
          {integrations.map((integration, index) => (
            <motion.div
              key={integration.name}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10 hover:border-[#00C2A8]/30 transition-all">
                <CardContent className="p-6 text-center">
                  <h3 className="text-white font-semibold mb-1 text-sm">{integration.name}</h3>
                  {integration.requiresEA && (
                    <Badge className="mt-2 bg-orange-500/20 text-orange-400 border-orange-500/30 text-xs">
                      EA Required
                    </Badge>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        <div className="bg-[#0f1923] border border-white/10 rounded-lg p-6 max-w-3xl mx-auto">
          <p className="text-white text-sm font-medium mb-2">
            MT4 and MT5 require the TradeFlow EA (Expert Advisor) installation
          </p>
          <p className="text-gray-400 text-xs leading-relaxed">
            Download the EA from your dashboard after signup, install it in your MetaTrader platform, and configure your API credentials. 
            TradeLocker, Topstep, and TruForex connect via direct API.
          </p>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="container mx-auto px-4 md:px-6 py-16 md:py-24">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl lg:text-5xl mb-4 text-white">
            Frequently Asked Questions
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Got questions? We've got answers. Can't find what you're looking for? Email us at{' '}
            <a href="mailto:support@fluxeo.net" className="text-[#00C2A8] hover:underline">
              support@fluxeo.net
            </a>
          </p>
        </div>
        
        <div className="max-w-3xl mx-auto">
          <Accordion type="single" collapsible className="space-y-4">
            {faqs.map((faq, index) => (
              <AccordionItem 
                key={index} 
                value={`item-${index}`}
                className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border border-white/10 rounded-lg px-6 hover:border-[#00C2A8]/30 transition-colors"
              >
                <AccordionTrigger className="text-white hover:text-[#00C2A8] text-left">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-gray-400">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-[#0a0f1a]/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 md:px-6 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-4">
            <TradeFlowLogo size="sm" />
            <div className="flex flex-wrap justify-center gap-6 text-sm text-gray-400">
              <a href="mailto:support@fluxeo.net" className="hover:text-[#00C2A8] transition-colors">
                support@fluxeo.net
              </a>
              <span className="text-gray-600">|</span>
              <button onClick={onNavigateToLogin} className="hover:text-[#00C2A8] transition-colors">
                Login
              </button>
              <span className="text-gray-600">|</span>
              <button onClick={onNavigateToSignup} className="hover:text-[#00C2A8] transition-colors">
                Sign Up
              </button>
              {onNavigateToAdmin && (
                <>
                  <span className="text-gray-600">|</span>
                  <button onClick={onNavigateToAdmin} className="hover:text-purple-400 transition-colors flex items-center gap-1">
                    <span>Admin</span>
                  </button>
                </>
              )}
            </div>
          </div>
          <div className="text-center text-gray-500 text-sm">
            <p>© 2025 TradeFlow by Fluxeo Technologies. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Chatbot */}
      <Chatbot />
    </div>
  );
}
