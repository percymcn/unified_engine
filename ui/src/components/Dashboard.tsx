import { useState, useEffect } from 'react';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { ScrollArea } from './ui/scroll-area';
import { 
  Activity, 
  TrendingUp, 
  Users, 
  Settings, 
  Key, 
  Webhook, 
  BarChart3,
  Shield,
  CreditCard,
  Terminal,
  AlertCircle,
  Menu,
  ChevronDown
} from 'lucide-react';
import { useUser } from '../contexts/UserContext';
import { useBroker, BrokerType } from '../contexts/BrokerContext';
import { SettingsDropdown } from './SettingsDropdown';
import { TradeFlowLogo } from './TradeFlowLogo';
import { DashboardOverview } from './DashboardOverview';
import { AccountsManager } from './AccountsManager';
import { WebhookTemplates } from './WebhookTemplates';
import { OrdersManager } from './OrdersManager';
import { PositionsMonitor } from './PositionsMonitor';
import { RiskControls } from './RiskControls';
import { TradingConfiguration } from './TradingConfiguration';
import { ApiKeyManager } from './ApiKeyManager';
import { BillingPortal } from './BillingPortal';
import { AdminPanel } from './AdminPanel';
import { LogsViewer } from './LogsViewer';
import { AnalyticsPage } from './AnalyticsPage';
import { ConnectBrokerPage } from './ConnectBrokerPage';
import { TrialBanner } from './TrialBanner';
import { BillingGuard } from './BillingGuard';
import { BrokerSwitcher } from './BrokerSwitcher';
import { BrokerSyncIndicator } from './BrokerSyncIndicator';
import { BrokerNavigationBar } from './BrokerNavigationBar';
import { Chatbot } from './Chatbot';

interface DashboardProps {
  onNavigateToAccountSelection?: () => void;
  onNavigateToChangeAccount?: () => void;
  onNavigateToSyncResults?: () => void;
}

export function Dashboard({
  onNavigateToAccountSelection,
  onNavigateToChangeAccount,
  onNavigateToSyncResults
}: DashboardProps) {
  const { user, isAdmin } = useUser();
  const { activeBroker: contextBroker, isSyncing } = useBroker();
  const [activeSection, setActiveSection] = useState('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Use broker from context, fallback to tradelocker for compatibility
  const activeBroker = (contextBroker || 'tradelocker') as 'tradelocker' | 'topstep' | 'truforex';

  const brokers = [
    { id: 'tradelocker', name: 'TradeLocker', icon: TrendingUp, color: 'text-blue-500' },
    { id: 'topstep', name: 'Topstep', icon: BarChart3, color: 'text-purple-500' },
    { id: 'truforex', name: 'TruForex', icon: Activity, color: 'text-green-500' }
  ] as const;

  // Filter sections based on user role
  const allSections = [
    { id: 'dashboard', name: 'Dashboard', icon: Activity, adminOnly: false },
    { id: 'analytics', name: 'Analytics', icon: BarChart3, adminOnly: false },
    { id: 'connect', name: 'Connect Broker', icon: Users, adminOnly: false },
    { id: 'accounts', name: 'Accounts', icon: Users, adminOnly: false },
    { id: 'webhooks', name: 'Webhooks', icon: Webhook, adminOnly: false },
    { id: 'trading', name: 'Trading Config', icon: Settings, adminOnly: false },
    { id: 'orders', name: 'Orders', icon: Terminal, adminOnly: false },
    { id: 'positions', name: 'Positions', icon: TrendingUp, adminOnly: false },
    { id: 'risk', name: 'Risk', icon: Shield, adminOnly: false },
    { id: 'keys', name: 'API Keys', icon: Key, adminOnly: false },
    { id: 'billing', name: 'Billing', icon: CreditCard, adminOnly: false },
    { id: 'admin', name: 'Admin', icon: Shield, adminOnly: true },
    { id: 'logs', name: 'Logs', icon: AlertCircle, adminOnly: false }
  ];

  const sections = isAdmin 
    ? allSections 
    : allSections.filter(section => !section.adminOnly);

  const renderSection = () => {
    switch (activeSection) {
      case 'dashboard':
        return (
          <DashboardOverview 
            broker={activeBroker}
            onNavigateToAccountSelection={onNavigateToAccountSelection}
            onNavigateToChangeAccount={onNavigateToChangeAccount}
            onNavigateToSyncResults={onNavigateToSyncResults}
          />
        );
      case 'analytics':
        return <AnalyticsPage broker={activeBroker} />;
      case 'connect':
        return <ConnectBrokerPage standalone={false} />;
      case 'accounts':
        return <AccountsManager broker={activeBroker} />;
      case 'webhooks':
        return <WebhookTemplates broker={activeBroker} />;
      case 'trading':
        return <TradingConfiguration broker={activeBroker} />;
      case 'orders':
        return <OrdersManager broker={activeBroker} />;
      case 'positions':
        return <PositionsMonitor broker={activeBroker} />;
      case 'risk':
        return <RiskControls broker={activeBroker} />;
      case 'keys':
        return <ApiKeyManager broker={activeBroker} />;
      case 'billing':
        return <BillingPortal />;
      case 'admin':
        return <AdminPanel />;
      case 'logs':
        return <LogsViewer broker={activeBroker} />;
      default:
        return (
          <DashboardOverview 
            broker={activeBroker}
            onNavigateToAccountSelection={onNavigateToAccountSelection}
            onNavigateToChangeAccount={onNavigateToChangeAccount}
            onNavigateToSyncResults={onNavigateToSyncResults}
          />
        );
    }
  };

  // Sidebar navigation component (reusable for desktop and mobile)
  const NavigationMenu = ({ onItemClick }: { onItemClick?: () => void }) => (
    <nav className="space-y-1">
      {sections.map((section) => {
        const Icon = section.icon;
        return (
          <button
            key={section.id}
            onClick={() => {
              setActiveSection(section.id);
              onItemClick?.();
            }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors touch-manipulation min-h-[44px] ${
              activeSection === section.id
                ? 'bg-[#002b36] text-[#00ffc2]'
                : 'text-gray-400 hover:text-white hover:bg-[#002b36]'
            }`}
          >
            <Icon className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm md:text-base">{section.name}</span>
          </button>
        );
      })}
      
      {/* Separator */}
      <div className="py-2">
        <div className="border-t border-gray-800"></div>
      </div>
      
      {/* Support Chatbot */}
      <Chatbot inSidebar={true} />
    </nav>
  );

  return (
    <div className="min-h-screen bg-[#002b36] text-white">
      {/* Broker Sync Indicator */}
      <BrokerSyncIndicator />
      
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-gray-800 bg-[#001f29]">
        <div className="px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center justify-between gap-2">
            {/* Left: Hamburger Menu + Logo */}
            <div className="flex items-center gap-2 md:gap-3 min-w-0">
              {/* Mobile Hamburger Menu */}
              <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                <SheetTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="md:hidden p-2 min-w-[44px] min-h-[44px]"
                  >
                    <Menu className="w-6 h-6" />
                    <span className="sr-only">Open menu</span>
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="bg-[#001f29] border-gray-800 w-[280px] p-0">
                  <SheetHeader className="px-4 py-4 border-b border-gray-800">
                    <SheetTitle className="text-white text-left">Navigation</SheetTitle>
                  </SheetHeader>
                  <ScrollArea className="h-[calc(100vh-80px)] px-4 py-4">
                    <NavigationMenu onItemClick={() => setMobileMenuOpen(false)} />
                  </ScrollArea>
                </SheetContent>
              </Sheet>

              <TradeFlowLogo size="sm" showText={true} />
            </div>

            {/* Center: Broker Switcher (Desktop) - Hidden, replaced by nav bar */}
            <div className="hidden lg:flex flex-1 justify-center">
              <BrokerSwitcher onConnectBroker={() => setActiveSection('connect')} compact />
            </div>

            {/* Right: User Info + Settings */}
            <div className="flex items-center gap-2 md:gap-4">
              {/* Desktop User Info */}
              <div className="hidden lg:flex items-center gap-3">
                {isAdmin && (
                  <Badge variant="outline" className="border-purple-400 text-purple-400">
                    Admin
                  </Badge>
                )}
                <Badge variant="outline" className="border-[#00ffc2] text-[#00ffc2]">
                  {user?.plan}
                </Badge>
                <div className="text-right">
                  <p className="text-sm text-white">{user?.name}</p>
                  <p className="text-xs text-gray-400">{user?.email}</p>
                </div>
              </div>

              {/* Mobile Plan Badge Only */}
              <Badge 
                variant="outline" 
                className="lg:hidden border-[#00ffc2] text-[#00ffc2] text-xs px-2"
              >
                {user?.plan}
              </Badge>

              {/* Settings Dropdown */}
              <SettingsDropdown onNavigate={setActiveSection} />
            </div>
          </div>
        </div>
      </header>

      {/* Broker Navigation Bar - Top Level Switcher */}
      <BrokerNavigationBar />

      <div className="px-4 md:px-6 py-4 md:py-6">
        <div className="flex flex-col md:grid md:grid-cols-12 gap-4 md:gap-6">
          {/* Desktop Sidebar Navigation */}
          <div className="hidden md:block md:col-span-3 lg:col-span-2">
            <Card className="bg-[#001f29] border-gray-800 sticky top-20">
              <CardContent className="p-3">
                <NavigationMenu />
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="md:col-span-9 lg:col-span-10">
            {/* Trial Banner - shows for trialing users */}
            {activeSection === 'overview' && <TrialBanner />}
            
            {/* Billing Guard - wraps trading sections when billing is blocked */}
            {['overview', 'positions', 'orders'].includes(activeSection) ? (
              <BillingGuard blockInteraction={true} showBanner={true}>
                {renderSection()}
              </BillingGuard>
            ) : (
              renderSection()
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
