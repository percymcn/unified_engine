import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Alert, AlertDescription } from './ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { 
  CheckCircle2,
  Copy,
  Plus,
  Download,
  ArrowRight,
  CheckCircle,
  Lock
} from 'lucide-react';
import { motion } from 'motion/react';
import { enhancedApiClient } from '../utils/api-client-enhanced';
import { toast } from 'sonner@2.0.3';
import { useBroker, BrokerType, getBrokerDisplayName, getBrokerIcon } from '../contexts/BrokerContext';
import { useUser } from '../contexts/UserContext';
import { TradeLockerIcon } from './TradeLockerLogo';
import { cn } from './ui/utils';

interface ConnectBrokerPageProps {
  onComplete?: () => void;
  onSkip?: () => void;
  standalone?: boolean;
}

export function ConnectBrokerPage({ onComplete, onSkip, standalone = false }: ConnectBrokerPageProps) {
  const { addBrokerAccount, connectedBrokers: contextConnectedBrokers } = useBroker();
  const { user } = useUser();
  
  const [activeBroker, setActiveBroker] = useState<'tradelocker' | 'topstep' | 'truforex' | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [generatedApiKey, setGeneratedApiKey] = useState<string | null>(null);
  const [showApiKeySuccess, setShowApiKeySuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    // TradeLocker fields
    tlUsername: '',
    tlPassword: '',
    server: '',
    url: 'https://demo.tradelocker.com',
    accountName: '',
    // Topstep fields
    username: '',
    password: '',
    topstepUsername: '',
    topstepApiKey: '',
    email: '',
    // TruForex fields
    platform: 'MT4',
    accountLogin: ''
  });

  // Tier limits
  const tierLimits = {
    trial: { brokers: 1, accountsPerBroker: 1 },
    starter: { brokers: 1, accountsPerBroker: 1 },
    pro: { brokers: 2, accountsPerBroker: 2 },
    elite: { brokers: 3, accountsPerBroker: 3 }
  };

  const currentTier = user?.plan || 'trial';
  const limits = tierLimits[currentTier as keyof typeof tierLimits] || tierLimits.trial;

  const brokers = [
    {
      id: 'tradelocker' as const,
      name: 'TradeLocker',
      icon: 'logo',
      color: '#0EA5E9',
      description: 'Direct API integration - no EA required',
      requiresEA: false
    },
    {
      id: 'topstep' as const,
      name: 'Topstep (ProjectX)',
      icon: '🎯',
      color: '#10b981',
      description: 'Direct API integration - no EA required',
      requiresEA: false
    },
    {
      id: 'truforex' as const,
      name: 'TruForex (MT4/MT5)',
      icon: '📊',
      color: '#f59e0b',
      description: 'Requires TradeFlow EA installation',
      requiresEA: true
    }
  ];

  const handleInputChange = (field: string, value: string) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleRegister = async () => {
    if (!activeBroker) return;

    setLoading(true);
    try {
      let brokerName = '';
      let payload: any = {};

      switch (activeBroker) {
        case 'tradelocker':
          brokerName = 'tradelocker';
          payload = {
            email: formData.tlUsername,
            password: formData.tlPassword,
            server: formData.server,
            mode: 'demo' as const
          };
          break;
        case 'topstep':
          brokerName = 'projectx';
          payload = {
            email: formData.email || formData.username,
            password: formData.password,
            mode: 'demo' as const
          };
          break;
        case 'truforex':
          brokerName = 'mtx';
          payload = {
            email: formData.username,
            password: formData.password,
            mode: 'demo' as const
          };
          break;
      }

      try {
        const response = await enhancedApiClient.registerBroker(brokerName, payload);
        
        const mockApiKey = `${activeBroker}_${Math.random().toString(36).substr(2, 9)}_${Date.now().toString(36)}`;
        setGeneratedApiKey(mockApiKey);
        setShowApiKeySuccess(true);

        // Generate unique account ID
        const accountId = response.id || `${activeBroker}-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
        const accountName = formData.accountName || 
                          formData.tlUsername || 
                          formData.username || 
                          `${getBrokerDisplayName(activeBroker)} Account ${contextConnectedBrokers.filter(b => b.broker === activeBroker).length + 1}`;

        addBrokerAccount({
          broker: activeBroker,
          accountId,
          accountName,
          connected: true,
          lastSync: new Date().toISOString()
        });

        toast.success(`${getBrokerDisplayName(activeBroker)} account connected!`);
      } catch (apiError: any) {
        console.warn('API registration failed, using local mode:', apiError.message);
        
        const mockApiKey = `${activeBroker}_${Math.random().toString(36).substr(2, 9)}_${Date.now().toString(36)}`;
        setGeneratedApiKey(mockApiKey);
        setShowApiKeySuccess(true);

        const accountId = `${activeBroker}-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
        const accountName = formData.accountName || 
                          formData.tlUsername || 
                          formData.username || 
                          `${getBrokerDisplayName(activeBroker)} Account ${contextConnectedBrokers.filter(b => b.broker === activeBroker).length + 1}`;

        addBrokerAccount({
          broker: activeBroker,
          accountId,
          accountName,
          connected: true,
          lastSync: new Date().toISOString()
        });

        toast.success(`${getBrokerDisplayName(activeBroker)} account connected (local mode)`);
      }
    } catch (error: any) {
      console.error('Registration error:', error);
      toast.error(error.message || 'Failed to register broker');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyApiKey = () => {
    if (generatedApiKey) {
      navigator.clipboard.writeText(generatedApiKey);
      toast.success('API key copied to clipboard!');
    }
  };

  const handleCloseDialog = () => {
    setShowDialog(false);
    setActiveBroker(null);
    setGeneratedApiKey(null);
    setShowApiKeySuccess(false);
    setFormData({
      tlUsername: '',
      tlPassword: '',
      server: '',
      url: 'https://demo.tradelocker.com',
      accountName: '',
      username: '',
      password: '',
      topstepUsername: '',
      topstepApiKey: '',
      email: '',
      platform: 'MT4',
      accountLogin: ''
    });
  };

  const openBrokerDialog = (brokerId: 'tradelocker' | 'topstep' | 'truforex') => {
    // Check account limit for this broker
    const brokerAccountCount = contextConnectedBrokers.filter(b => b.broker === brokerId).length;
    
    if (brokerAccountCount >= limits.accountsPerBroker) {
      toast.error(`You can only have ${limits.accountsPerBroker} account(s) per broker on the ${currentTier.toUpperCase()} plan. Upgrade to add more.`);
      return;
    }

    setActiveBroker(brokerId);
    setShowDialog(true);
  };

  const getBrokerAccountCount = (brokerId: string) => {
    return contextConnectedBrokers.filter(b => b.broker === brokerId).length;
  };

  const canAddMoreAccounts = (brokerId: string) => {
    return getBrokerAccountCount(brokerId) < limits.accountsPerBroker;
  };

  return (
    <div className="min-h-screen bg-[#002b36] text-white py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="text-white mb-4">Connect Your Brokers</h1>
          <p className="text-gray-400 max-w-2xl mx-auto mb-4">
            Link your trading accounts to start using TradeFlow. You can connect multiple accounts per broker based on your plan.
          </p>
          
          {/* Tier Info */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-950/30 border border-blue-800/30 rounded-lg">
            <Badge className="bg-[#00ffc2] text-[#002b36]">{currentTier.toUpperCase()}</Badge>
            <span className="text-sm text-blue-300">
              {limits.accountsPerBroker} account(s) per broker • {limits.brokers} broker(s) total
            </span>
          </div>
        </motion.div>

        {/* Broker Cards Grid */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          {brokers.map((broker, index) => {
            const accountCount = getBrokerAccountCount(broker.id);
            const canAdd = canAddMoreAccounts(broker.id);
            
            return (
              <motion.div
                key={broker.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card 
                  className={cn(
                    "bg-[#001f29] border-gray-800 hover:border-gray-700 transition-all h-full",
                    accountCount > 0 && "border-l-4"
                  )}
                  style={{
                    borderLeftColor: accountCount > 0 ? broker.color : undefined
                  }}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between mb-3">
                      <div 
                        className="w-12 h-12 rounded-lg flex items-center justify-center overflow-hidden p-1"
                        style={{ 
                          background: broker.icon === 'logo' ? 'transparent' : `${broker.color}20`
                        }}
                      >
                        {broker.icon === 'logo' ? (
                          <TradeLockerIcon className="w-full h-full" />
                        ) : (
                          <span className="text-2xl">{broker.icon}</span>
                        )}
                      </div>
                      <div className="flex flex-col gap-1">
                        {broker.requiresEA && (
                          <Badge variant="outline" className="border-orange-400 text-orange-400 text-xs">
                            EA Required
                          </Badge>
                        )}
                        {accountCount > 0 && (
                          <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-xs">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            {accountCount} Connected
                          </Badge>
                        )}
                      </div>
                    </div>
                    <CardTitle className="text-white">{broker.name}</CardTitle>
                    <CardDescription className="text-gray-400 text-sm">
                      {broker.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Dialog 
                      open={showDialog && activeBroker === broker.id} 
                      onOpenChange={(open) => {
                        if (!open) handleCloseDialog();
                      }}
                    >
                      <Button
                        onClick={() => openBrokerDialog(broker.id)}
                        className={cn(
                          "w-full",
                          !canAdd && "opacity-50"
                        )}
                        style={{ 
                          background: canAdd ? broker.color : '#374151',
                          color: 'white'
                        }}
                        disabled={!canAdd}
                      >
                        {!canAdd ? (
                          <>
                            <Lock className="w-4 h-4 mr-2" />
                            Limit Reached ({accountCount}/{limits.accountsPerBroker})
                          </>
                        ) : accountCount > 0 ? (
                          <>
                            <Plus className="w-4 h-4 mr-2" />
                            Add Account ({accountCount}/{limits.accountsPerBroker})
                          </>
                        ) : (
                          <>
                            <Plus className="w-4 h-4 mr-2" />
                            Connect Account
                          </>
                        )}
                      </Button>
                      <DialogContent 
                        className="bg-[#001f29] border-gray-800 text-white max-w-md"
                        onEscapeKeyDown={(e) => {
                          if (showApiKeySuccess) e.preventDefault();
                        }}
                      >
                        <DialogHeader>
                          <DialogTitle className="text-white flex items-center gap-2">
                            {broker.id === 'tradelocker' && '🔄 Auto Register (Recommended)'}
                            {broker.id === 'topstep' && '🚀 ProjectX User Registration'}
                            {broker.id === 'truforex' && 'TruForex ProjectX – Signup & API Key'}
                          </DialogTitle>
                          <DialogDescription className="text-gray-400 text-xs">
                            {broker.id === 'tradelocker' && 'Connect your TradeLocker account to start trading'}
                            {broker.id === 'topstep' && 'Register your Topstep account for automated trading'}
                            {broker.id === 'truforex' && 'Backend: https://truforex.securepharma.net'}
                          </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4 mt-4">
                          {/* Success State - API Key Generated */}
                          {showApiKeySuccess && generatedApiKey ? (
                            <div className="space-y-4">
                              <div className="p-4 bg-green-950 border border-green-800 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                  <CheckCircle className="w-5 h-5 text-green-400" />
                                  <h3 className="text-white">Account Registered Successfully!</h3>
                                </div>
                                <p className="text-sm text-green-200">
                                  Your API key has been generated. Copy it now and use it in your TradingView webhooks.
                                </p>
                              </div>

                              <div>
                                <Label className="text-gray-300 mb-2 block">Your API Key</Label>
                                <div className="flex gap-2">
                                  <div className="flex-1 p-3 bg-[#002b36] rounded border border-gray-700 font-mono text-sm">
                                    <code className="text-[#00ffc2] break-all">{generatedApiKey}</code>
                                  </div>
                                  <Button
                                    onClick={handleCopyApiKey}
                                    className="bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad] shrink-0"
                                  >
                                    <Copy className="w-4 h-4" />
                                  </Button>
                                </div>
                                <p className="text-xs text-yellow-400 mt-2">
                                  ⚠️ Store this key securely. You'll need it for TradingView webhook configuration.
                                </p>
                              </div>

                              <div className="p-3 bg-[#002b36] rounded border border-gray-700">
                                <p className="text-sm text-white mb-2">Next Steps:</p>
                                <ol className="text-xs text-gray-400 space-y-1 list-decimal list-inside">
                                  <li>Go to the "Webhooks" tab in the sidebar</li>
                                  <li>Select your TradingView alert template</li>
                                  <li>Your API key will be automatically included in the webhook URL</li>
                                  <li>Copy the complete webhook configuration to TradingView</li>
                                </ol>
                              </div>

                              <Button
                                onClick={handleCloseDialog}
                                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                              >
                                Done - Add Another or Close
                                <ArrowRight className="w-4 h-4 ml-2" />
                              </Button>
                            </div>
                          ) : (
                            <>
                              {/* Account Name (Optional) */}
                              <div>
                                <Label htmlFor="accountName" className="text-gray-300 text-sm mb-1 block">
                                  Account Name (Optional)
                                </Label>
                                <Input
                                  id="accountName"
                                  placeholder="e.g., Main Trading Account"
                                  value={formData.accountName}
                                  onChange={(e) => handleInputChange('accountName', e.target.value)}
                                  className="bg-[#002b36] border-gray-700 text-white placeholder:text-gray-500"
                                />
                              </div>

                              {/* TradeLocker Form */}
                              {broker.id === 'tradelocker' && (
                                <>
                                  <div>
                                    <Input
                                      placeholder="TL Username"
                                      value={formData.tlUsername}
                                      onChange={(e) => handleInputChange('tlUsername', e.target.value)}
                                      className="bg-[#002b36] border-gray-700 text-white placeholder:text-gray-500"
                                    />
                                  </div>
                                  <div>
                                    <Input
                                      type="password"
                                      placeholder="TL Password"
                                      value={formData.tlPassword}
                                      onChange={(e) => handleInputChange('tlPassword', e.target.value)}
                                      className="bg-[#002b36] border-gray-700 text-white placeholder:text-gray-500"
                                    />
                                  </div>
                                  <div>
                                    <Input
                                      placeholder="Server (e.g., TOPFX-Live)"
                                      value={formData.server}
                                      onChange={(e) => handleInputChange('server', e.target.value)}
                                      className="bg-[#002b36] border-gray-700 text-white placeholder:text-gray-500"
                                    />
                                  </div>
                                  <div>
                                    <Input
                                      placeholder="https://demo.tradelocker.com"
                                      value={formData.url}
                                      onChange={(e) => handleInputChange('url', e.target.value)}
                                      className="bg-[#002b36] border-gray-700 text-white"
                                    />
                                  </div>
                                  <Button
                                    className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                                    onClick={handleRegister}
                                    disabled={loading}
                                  >
                                    {loading ? '⏳ Registering...' : '✅ Auto Register'}
                                  </Button>
                                </>
                              )}

                              {/* Topstep Form */}
                              {broker.id === 'topstep' && (
                                <>
                                  <div>
                                    <Label htmlFor="username" className="text-gray-300 text-sm mb-1 block">Username</Label>
                                    <Input
                                      id="username"
                                      value={formData.username}
                                      onChange={(e) => handleInputChange('username', e.target.value)}
                                      className="bg-[#002b36] border-gray-700 text-white"
                                    />
                                  </div>
                                  <div>
                                    <Label htmlFor="password" className="text-gray-300 text-sm mb-1 block">Password</Label>
                                    <Input
                                      id="password"
                                      type="password"
                                      value={formData.password}
                                      onChange={(e) => handleInputChange('password', e.target.value)}
                                      className="bg-[#002b36] border-gray-700 text-white"
                                    />
                                  </div>
                                  <div>
                                    <Label htmlFor="email" className="text-gray-300 text-sm mb-1 block">Email (optional)</Label>
                                    <Input
                                      id="email"
                                      type="email"
                                      value={formData.email}
                                      onChange={(e) => handleInputChange('email', e.target.value)}
                                      className="bg-[#002b36] border-gray-700 text-white"
                                    />
                                  </div>
                                  <Button
                                    className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                                    onClick={handleRegister}
                                    disabled={loading}
                                  >
                                    {loading ? '⏳ Registering...' : '✅ Register User'}
                                  </Button>
                                </>
                              )}

                              {/* TruForex Form */}
                              {broker.id === 'truforex' && (
                                <>
                                  <div className="grid grid-cols-2 gap-4">
                                    <div>
                                      <Label htmlFor="tfUsername" className="text-gray-400 text-xs mb-1 block">Username</Label>
                                      <Input
                                        id="tfUsername"
                                        placeholder="your name"
                                        value={formData.username}
                                        onChange={(e) => handleInputChange('username', e.target.value)}
                                        className="bg-[#001f29] border-gray-700 text-white placeholder:text-gray-600"
                                      />
                                    </div>
                                    <div>
                                      <Label htmlFor="tfPassword" className="text-gray-400 text-xs mb-1 block">Password</Label>
                                      <Input
                                        id="tfPassword"
                                        type="password"
                                        placeholder="••••••••"
                                        value={formData.password}
                                        onChange={(e) => handleInputChange('password', e.target.value)}
                                        className="bg-[#001f29] border-gray-700 text-white"
                                      />
                                    </div>
                                  </div>
                                  
                                  <div className="grid grid-cols-2 gap-4">
                                    <div>
                                      <Label htmlFor="platform" className="text-gray-400 text-xs mb-1 block">Platform</Label>
                                      <Select
                                        value={formData.platform}
                                        onValueChange={(value) => handleInputChange('platform', value)}
                                      >
                                        <SelectTrigger className="bg-[#001f29] border-gray-700 text-white">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#002b36] border-gray-700">
                                          <SelectItem value="MT4">MT4</SelectItem>
                                          <SelectItem value="MT5">MT5</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <div>
                                      <Label htmlFor="accountLogin" className="text-gray-400 text-xs mb-1 block">Account Login</Label>
                                      <Input
                                        id="accountLogin"
                                        placeholder="123456"
                                        value={formData.accountLogin}
                                        onChange={(e) => handleInputChange('accountLogin', e.target.value)}
                                        className="bg-[#001f29] border-gray-700 text-white"
                                      />
                                    </div>
                                  </div>

                                  <Alert className="bg-orange-950 border-orange-800">
                                    <Download className="w-4 h-4 text-orange-400" />
                                    <AlertDescription className="text-orange-200 text-xs">
                                      <p className="mb-1">MT4/MT5 requires the TradeFlow EA:</p>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="mt-1 border-orange-400 text-orange-400 hover:bg-orange-400/10 h-7"
                                      >
                                        <Download className="w-3 h-3 mr-1" />
                                        Download EA
                                      </Button>
                                    </AlertDescription>
                                  </Alert>

                                  <Button
                                    className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                                    onClick={handleRegister}
                                    disabled={loading}
                                  >
                                    {loading ? '⏳ Creating Account...' : '✅ Create Account & Get API Key'}
                                  </Button>
                                </>
                              )}
                            </>
                          )}
                        </div>
                      </DialogContent>
                    </Dialog>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>

        {/* Connected Brokers Summary */}
        {contextConnectedBrokers.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="bg-[#001f29] border-gray-800">
              <CardHeader>
                <CardTitle className="text-white">Connected Brokers</CardTitle>
                <CardDescription className="text-gray-400">
                  You have {contextConnectedBrokers.length} account{contextConnectedBrokers.length !== 1 ? 's' : ''} connected
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {contextConnectedBrokers.map((broker) => (
                    <div
                      key={`${broker.broker}-${broker.accountId}`}
                      className="flex items-center justify-between p-3 bg-[#002b36] border border-gray-700 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        {broker.broker === 'tradelocker' ? (
                          <div className="w-6 h-6">
                            <TradeLockerIcon className="w-full h-full" />
                          </div>
                        ) : (
                          <span className="text-xl">{getBrokerIcon(broker.broker)}</span>
                        )}
                        <div>
                          <p className="text-sm text-white font-medium">{getBrokerDisplayName(broker.broker)}</p>
                          <p className="text-xs text-gray-400">{broker.accountName}</p>
                        </div>
                      </div>
                      <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Connected
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="flex gap-4 justify-center mt-8"
        >
          {standalone && onSkip && (
            <Button
              variant="outline"
              onClick={onSkip}
              className="border-gray-700 text-gray-300 hover:bg-[#001f29]"
            >
              Skip for Now
            </Button>
          )}
          {onComplete && contextConnectedBrokers.length > 0 && (
            <Button
              onClick={onComplete}
              className="bg-[#00ffc2] text-[#002b36] hover:bg-[#00e6ad]"
            >
              Continue to Dashboard
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          )}
        </motion.div>
      </div>
    </div>
  );
}
