import { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { ArrowLeft, AlertCircle, Loader2, Check } from 'lucide-react';
import { Badge } from './ui/badge';
import { TradeFlowLogo } from './TradeFlowLogo';

interface SignupPageProps {
  onSignup: (email: string, password: string, name: string, plan: string) => Promise<void>;
  onNavigateToLogin: () => void;
  onNavigateToLanding: () => void;
}

export function SignupPage({ onSignup, onNavigateToLogin, onNavigateToLanding }: SignupPageProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [selectedPlan, setSelectedPlan] = useState('pro');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const plans = [
    {
      id: 'starter',
      name: 'Starter',
      price: '$20/mo',
      features: ['1 Broker', 'API Keys', 'Risk Controls']
    },
    {
      id: 'pro',
      name: 'Pro',
      price: '$40/mo',
      features: ['2 Brokers', '1 Strategy', 'Priority Support']
    },
    {
      id: 'elite',
      name: 'Elite',
      price: '$60/mo',
      features: ['3 Brokers', '3 Strategies', '24/7 Support']
    }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      await onSignup(email, password, name, selectedPlan);
    } catch (err: any) {
      setError(err.message || 'Failed to create account. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Back to Home */}
        <Button
          variant="ghost"
          onClick={onNavigateToLanding}
          className="mb-4 text-gray-400 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Home
        </Button>

        {/* Signup Card */}
        <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10">
          <CardHeader className="space-y-4">
            <div className="flex justify-center">
              <TradeFlowLogo size="md" />
            </div>
            <div className="text-center">
              <CardTitle className="text-2xl text-white">Start Your Free Trial</CardTitle>
              <CardDescription className="text-gray-400">
                3 days or 100 trades — No credit card required
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <Alert variant="destructive" className="bg-red-500/10 border-red-500/50 text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Personal Information */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-gray-300">Full Name</Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="John Doe"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="bg-[#0a0f1a] border-white/10 text-white placeholder:text-gray-500 focus:border-[#00C2A8]"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-gray-300">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-[#0a0f1a] border-white/10 text-white placeholder:text-gray-500 focus:border-[#00C2A8]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-gray-300">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="bg-[#0a0f1a] border-white/10 text-white placeholder:text-gray-500 focus:border-[#00C2A8]"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm-password" className="text-gray-300">Confirm Password</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      className="bg-[#0a0f1a] border-white/10 text-white placeholder:text-gray-500 focus:border-[#00C2A8]"
                    />
                  </div>
                </div>
              </div>

              {/* Plan Selection */}
              <div className="space-y-3">
                <Label className="text-gray-300">Select Your Plan</Label>
                <RadioGroup value={selectedPlan} onValueChange={setSelectedPlan}>
                  {plans.map((plan) => (
                    <label
                      key={plan.id}
                      htmlFor={plan.id}
                      className={`flex items-center space-x-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                        selectedPlan === plan.id
                          ? 'border-[#00C2A8] bg-[#00C2A8]/5'
                          : 'border-white/10 bg-[#0a0f1a] hover:border-white/20'
                      }`}
                    >
                      <RadioGroupItem value={plan.id} id={plan.id} />
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-white">{plan.name}</span>
                          <span className="text-[#00C2A8]">{plan.price}</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {plan.features.map((feature) => (
                            <Badge 
                              key={feature} 
                              variant="outline" 
                              className="text-xs border-gray-600 text-gray-400"
                            >
                              {feature}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      {selectedPlan === plan.id && (
                        <Check className="w-5 h-5 text-[#00C2A8]" />
                      )}
                    </label>
                  ))}
                </RadioGroup>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-[#00C2A8] text-[#0a0f1a] hover:bg-[#00C2A8]/90 font-semibold"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  'Start Free Trial'
                )}
              </Button>

              <p className="text-xs text-center text-gray-400">
                By signing up, you agree to our Terms of Service and Privacy Policy
              </p>
            </form>
          </CardContent>
          <CardFooter className="flex justify-center border-t border-white/10 pt-6">
            <p className="text-sm text-gray-400">
              Already have an account?{' '}
              <button
                onClick={onNavigateToLogin}
                className="text-[#00C2A8] hover:text-[#00C2A8]/80 font-medium"
              >
                Login
              </button>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
