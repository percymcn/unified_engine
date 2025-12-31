import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Home, ArrowLeft, Search } from 'lucide-react';
import { TradeFlowLogo } from './TradeFlowLogo';

interface NotFoundPageProps {
  onNavigateToDashboard?: () => void;
  onNavigateToLanding?: () => void;
}

export function NotFoundPage({ onNavigateToDashboard, onNavigateToLanding }: NotFoundPageProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Logo */}
        <div className="text-center mb-8">
          <TradeFlowLogo size="md" />
        </div>

        <Card className="border-slate-200 dark:border-slate-700 shadow-xl overflow-hidden">
          <CardContent className="p-12 text-center">
            {/* 404 Illustration */}
            <div className="mb-8">
              <div className="relative inline-block">
                {/* Large 404 */}
                <h1 className="text-[150px] md:text-[200px] font-bold text-transparent bg-clip-text bg-gradient-to-br from-blue-400 to-purple-600 leading-none">
                  404
                </h1>
                
                {/* Floating icon */}
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                  <div className="bg-white dark:bg-slate-800 rounded-full p-4 shadow-lg">
                    <Search className="w-12 h-12 text-slate-400" />
                  </div>
                </div>
              </div>
            </div>

            {/* Error Message */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold mb-3 text-slate-900 dark:text-slate-100">
                Page Not Found
              </h2>
              <p className="text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                The page you're looking for doesn't exist or has been moved. 
                It might have been deleted, or you may have mistyped the URL.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              {onNavigateToDashboard && (
                <Button
                  onClick={onNavigateToDashboard}
                  className="bg-blue-500 hover:bg-blue-600 text-white min-w-48"
                  size="lg"
                >
                  <Home className="w-4 h-4 mr-2" />
                  Go to Dashboard
                </Button>
              )}
              
              {onNavigateToLanding && (
                <Button
                  onClick={onNavigateToLanding}
                  variant="outline"
                  className="border-slate-300 dark:border-slate-600 min-w-48"
                  size="lg"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Home
                </Button>
              )}
            </div>

            {/* Help Text */}
            <div className="mt-8 pt-8 border-t border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                If you believe this is an error, please{' '}
                <a
                  href="mailto:support@fluxeo.net"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  contact our support team
                </a>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Additional Help Links */}
        <div className="mt-6 text-center">
          <div className="inline-flex gap-6 text-sm text-slate-500 dark:text-slate-400">
            <a href="/" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              Home
            </a>
            <a href="/dashboard" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              Dashboard
            </a>
            <a href="mailto:support@fluxeo.net" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              Support
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
