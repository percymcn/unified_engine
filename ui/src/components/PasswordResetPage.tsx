import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { CheckCircle, AlertCircle, Key, Loader2, ArrowLeft, Mail } from 'lucide-react';
import { TradeFlowLogo } from './TradeFlowLogo';

interface PasswordResetPageProps {
  onBack: () => void;
  onSuccess?: () => void;
}

export function PasswordResetPage({ onBack, onSuccess }: PasswordResetPageProps) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email) {
      setError('Please enter your email address');
      return;
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);

    try {
      // Replace with real API call
      // await apiClient.post('/api/auth/reset-password', { email });
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      setSuccess(true);
      
      // Optionally navigate away after a delay
      if (onSuccess) {
        setTimeout(() => {
          onSuccess();
        }, 3000);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={onBack}
          className="mb-6 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Login
        </Button>

        {/* Logo */}
        <div className="text-center mb-8">
          <TradeFlowLogo size="lg" />
        </div>

        {/* Main Card */}
        <Card className="border-slate-200 dark:border-slate-700 shadow-xl">
          {!success ? (
            <>
              <CardHeader className="space-y-4 text-center pb-6">
                <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center">
                  <Key className="w-8 h-8 text-white" />
                </div>
                <div>
                  <CardTitle className="text-2xl">Reset Your Password</CardTitle>
                  <CardDescription className="mt-2">
                    Enter your email and we'll send you a link to reset your password
                  </CardDescription>
                </div>
              </CardHeader>

              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
                    <Alert variant="destructive" className="border-red-200 bg-red-50 dark:bg-red-950/30">
                      <AlertCircle className="w-4 h-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-slate-700 dark:text-slate-300">
                      Email Address
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your.email@example.com"
                        className="pl-10 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700"
                        autoComplete="email"
                        required
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-blue-500 hover:bg-blue-600 text-white h-11"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Mail className="w-4 h-4 mr-2" />
                        Send Reset Link
                      </>
                    )}
                  </Button>
                </form>

                {/* Help Text */}
                <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex gap-3">
                    <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-blue-800 dark:text-blue-200">
                      <p className="font-medium mb-1">What happens next?</p>
                      <ul className="list-disc list-inside space-y-1 text-blue-700 dark:text-blue-300">
                        <li>Check your email inbox</li>
                        <li>Click the reset link we sent you</li>
                        <li>Create a new password</li>
                        <li>Sign in with your new password</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </CardContent>
            </>
          ) : (
            <>
              <CardHeader className="space-y-4 text-center pb-6">
                <div className="mx-auto w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center">
                  <CheckCircle className="w-8 h-8 text-white" />
                </div>
                <div>
                  <CardTitle className="text-2xl text-green-700 dark:text-green-400">
                    Check Your Email
                  </CardTitle>
                  <CardDescription className="mt-2">
                    Password reset instructions sent
                  </CardDescription>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <Alert className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800">
                  <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                  <AlertDescription className="text-green-800 dark:text-green-200">
                    We've sent a password reset link to <strong>{email}</strong>
                  </AlertDescription>
                </Alert>

                <div className="p-4 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg">
                  <p className="text-sm text-slate-700 dark:text-slate-300 mb-3">
                    <strong>Didn't receive the email?</strong>
                  </p>
                  <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-2 list-disc list-inside">
                    <li>Check your spam or junk folder</li>
                    <li>Make sure {email} is correct</li>
                    <li>Wait a few minutes and check again</li>
                  </ul>
                </div>

                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={onBack}
                    className="flex-1"
                  >
                    Back to Login
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setSuccess(false);
                      setEmail('');
                    }}
                    className="flex-1"
                  >
                    Send Again
                  </Button>
                </div>
              </CardContent>
            </>
          )}
        </Card>

        {/* Support Link */}
        <div className="text-center mt-6">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Need help?{' '}
            <a
              href="mailto:support@fluxeo.net"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
