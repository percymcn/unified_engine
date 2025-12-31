import { useState, useEffect } from 'react';
import { Toaster } from './components/ui/sonner';
import { UserProvider, useUser } from './contexts/UserContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { BrokerProvider } from './contexts/BrokerContext';
import { AnimatedBackground } from './components/AnimatedBackground';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { SignupPage } from './components/SignupPage';
import { Dashboard } from './components/Dashboard';
import { OnboardingPlanSelection } from './components/OnboardingPlanSelection';
import { ConnectBrokerPage } from './components/ConnectBrokerPage';
import { AdminLoginPage } from './components/AdminLoginPage';
import { AdminDashboard } from './components/AdminDashboard';
import { AccountSelectionPage } from './components/AccountSelectionPage';
import { ChangeAccountPage } from './components/ChangeAccountPage';
import { SyncResultsPage } from './components/SyncResultsPage';
import { PasswordResetPage } from './components/PasswordResetPage';
import { NotFoundPage } from './components/NotFoundPage';

type AppView = 
  | 'landing' 
  | 'login' 
  | 'signup' 
  | 'password-reset'
  | 'onboarding' 
  | 'connect-broker' 
  | 'dashboard' 
  | 'account-selection'
  | 'change-account'
  | 'sync-results'
  | 'admin-login' 
  | 'admin-dashboard'
  | '404';

function AppRouter() {
  const { user, loading, login, signup, logout, setUser, isAdmin } = useUser();
  const [view, setView] = useState<AppView>('landing');
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [adminAuthenticated, setAdminAuthenticated] = useState(false);

  // Check if user needs onboarding
  useEffect(() => {
    if (!loading && user) {
      // Check if user has completed onboarding (you can add a flag in user object)
      const needsOnboarding = !user.plan || user.plan === 'trial';
      
      if (needsOnboarding && !onboardingComplete) {
        setView('onboarding');
      } else {
        setView('dashboard');
      }
    } else if (!loading && !user && (view === 'dashboard' || view === 'onboarding' || view === 'connect-broker')) {
      setView('landing');
    }
  }, [user, loading, onboardingComplete]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#001f29] via-[#002b36] to-[#001f29] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-[#00ffc2] mx-auto mb-4"></div>
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Admin authentication handler
  const handleAdminLogin = async (username: string, password: string) => {
    // In production, validate against secure admin credentials
    if (username === 'admin' && password === 'admin123') {
      setAdminAuthenticated(true);
      setView('admin-dashboard');
    } else {
      throw new Error('Invalid admin credentials');
    }
  };

  const handleAdminLogout = () => {
    setAdminAuthenticated(false);
    setView('landing');
  };

  // Admin views
  if (adminAuthenticated && view === 'admin-dashboard') {
    return <AdminDashboard onLogout={handleAdminLogout} />;
  }

  // Regular user views
  if (user && view === 'dashboard') {
    return (
      <Dashboard 
        onNavigateToAccountSelection={() => setView('account-selection')}
        onNavigateToChangeAccount={() => setView('change-account')}
        onNavigateToSyncResults={() => setView('sync-results')}
      />
    );
  }

  switch (view) {
    case 'admin-login':
      return (
        <AdminLoginPage
          onAdminLogin={handleAdminLogin}
          onBackToPublic={() => setView('landing')}
        />
      );
    case 'admin-dashboard':
      if (!adminAuthenticated) {
        setView('admin-login');
        return null;
      }
      return <AdminDashboard onLogout={handleAdminLogout} />;

    case 'login':
      return (
        <LoginPage
          onLogin={login}
          onNavigateToSignup={() => setView('signup')}
          onNavigateToLanding={() => setView('landing')}
          onNavigateToPasswordReset={() => setView('password-reset')}
        />
      );
    case 'signup':
      return (
        <SignupPage
          onSignup={signup}
          onNavigateToLogin={() => setView('login')}
          onNavigateToLanding={() => setView('landing')}
        />
      );
    case 'password-reset':
      return (
        <PasswordResetPage
          onBack={() => setView('login')}
          onSuccess={() => setView('login')}
        />
      );
    case 'onboarding':
      return (
        <OnboardingPlanSelection
          onPlanSelected={(plan) => {
            // Update user plan
            if (user) {
              setUser({ ...user, plan });
            }
            setView('connect-broker');
          }}
          onSkip={() => setView('dashboard')}
        />
      );
    case 'connect-broker':
      return (
        <ConnectBrokerPage
          standalone={true}
          onComplete={() => {
            setOnboardingComplete(true);
            setView('dashboard');
          }}
          onSkip={() => {
            setOnboardingComplete(true);
            setView('dashboard');
          }}
        />
      );
    case 'account-selection':
      return (
        <AccountSelectionPage
          onComplete={() => setView('dashboard')}
          onBack={() => setView('dashboard')}
        />
      );
    case 'change-account':
      return (
        <ChangeAccountPage
          onComplete={() => setView('dashboard')}
          onBack={() => setView('dashboard')}
        />
      );
    case 'sync-results':
      return (
        <SyncResultsPage
          onBack={() => setView('dashboard')}
        />
      );
    case '404':
      return (
        <NotFoundPage
          onNavigateToDashboard={user ? () => setView('dashboard') : undefined}
          onNavigateToLanding={() => setView('landing')}
        />
      );
    case 'landing':
    default:
      return (
        <LandingPage
          onNavigateToLogin={() => setView('login')}
          onNavigateToSignup={() => setView('signup')}
          onNavigateToAdmin={() => setView('admin-login')}
        />
      );
  }
}

export default function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <BrokerProvider>
          <AnimatedBackground />
          <AppRouter />
          <Toaster position="top-right" />
        </BrokerProvider>
      </UserProvider>
    </ThemeProvider>
  );
}
