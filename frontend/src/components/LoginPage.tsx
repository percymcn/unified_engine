import { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { ArrowLeft, AlertCircle, Loader2 } from 'lucide-react';
import { TradeFlowLogo } from './TradeFlowLogo';

interface LoginPageProps {
  onLogin: (email: string, password: string) => Promise<void>;
  onNavigateToSignup: () => void;
  onNavigateToLanding: () => void;
  onNavigateToPasswordReset?: () => void;
}

export function LoginPage({ onLogin, onNavigateToSignup, onNavigateToLanding, onNavigateToPasswordReset }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await onLogin(email, password);
    } catch (err: any) {
      setError(err.message || 'Failed to login. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Back to Home */}
        <Button
          variant="ghost"
          onClick={onNavigateToLanding}
          className="mb-4 text-gray-400 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Home
        </Button>

        {/* Login Card */}
        <Card className="bg-gradient-to-br from-[#0f1923] to-[#0a0f1a] border-white/10">
          <CardHeader className="space-y-4">
            <div className="flex justify-center">
              <TradeFlowLogo size="md" />
            </div>
            <div className="text-center">
              <CardTitle className="text-2xl text-white">Welcome back</CardTitle>
              <CardDescription className="text-gray-400">
                Sign in to your TradeFlow account
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive" className="bg-red-500/10 border-red-500/50 text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email" className="text-gray-300">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="bg-[#0a0f1a] border-white/10 text-white placeholder:text-gray-500 focus:border-[#00C2A8]"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-gray-300">Password</Label>
                  {onNavigateToPasswordReset && (
                    <button
                      type="button"
                      onClick={onNavigateToPasswordReset}
                      className="text-xs text-[#00C2A8] hover:text-[#00C2A8]/80"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
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

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-[#00C2A8] text-[#0a0f1a] hover:bg-[#00C2A8]/90 font-semibold"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in to your account'
                )}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-center border-t border-white/10 pt-6">
            <p className="text-sm text-gray-400">
              Don't have an account?{' '}
              <button
                onClick={onNavigateToSignup}
                className="text-[#00C2A8] hover:text-[#00C2A8]/80 font-medium"
              >
                Start free trial
              </button>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
