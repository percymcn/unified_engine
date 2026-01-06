import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ChevronDown, ChevronUp, Key } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { ApiKeyDisplay } from './ApiKeyDisplay';
import { getBrokerDisplayName } from '../contexts/BrokerContext';

interface UserAccount {
  userId: string;
  userName: string;
  userEmail: string;
  plan: string;
  brokerAccounts: {
    accountId: string;
    accountName: string;
    broker: string;
    apiKey: string;
    status: 'active' | 'inactive';
    connected: boolean;
    lastSync?: string;
  }[];
}

// Mock data - in production, fetch from backend
const mockUserAccounts: UserAccount[] = [
  {
    userId: '1',
    userName: 'John Doe',
    userEmail: 'john@example.com',
    plan: 'elite',
    brokerAccounts: [
      {
        accountId: 'TL123456',
        accountName: 'TradeLocker Main',
        broker: 'tradelocker',
        apiKey: 'tradelocker_TL123456_a7f3k9m2x5p8q1z',
        status: 'active',
        connected: true,
        lastSync: '2 mins ago'
      },
      {
        accountId: 'TS789012',
        accountName: 'TopStep Futures',
        broker: 'topstep',
        apiKey: 'topstep_TS789012_b4g7j2n6y9r3w',
        status: 'active',
        connected: true,
        lastSync: '5 mins ago'
      },
      {
        accountId: 'TF345678',
        accountName: 'TruForex MT5',
        broker: 'truforex',
        apiKey: 'truforex_TF345678_c8h5k3m7x2v6z',
        status: 'active',
        connected: true,
        lastSync: '1 hour ago'
      }
    ]
  },
  {
    userId: '2',
    userName: 'Jane Smith',
    userEmail: 'jane@example.com',
    plan: 'pro',
    brokerAccounts: [
      {
        accountId: 'TL654321',
        accountName: 'Jane Trading Account',
        broker: 'tradelocker',
        apiKey: 'tradelocker_TL654321_d9f4h8k1m5p7q',
        status: 'active',
        connected: true,
        lastSync: '10 mins ago'
      },
      {
        accountId: 'TS111222',
        accountName: 'Topstep Gold',
        broker: 'topstep',
        apiKey: 'topstep_TS111222_e2j6n9r4w7y3x',
        status: 'active',
        connected: false,
        lastSync: 'Never'
      }
    ]
  },
  {
    userId: '3',
    userName: 'Bob Johnson',
    userEmail: 'bob@example.com',
    plan: 'starter',
    brokerAccounts: [
      {
        accountId: 'TF999888',
        accountName: 'Bob MT4 Live',
        broker: 'truforex',
        apiKey: 'truforex_TF999888_f3k7m2p8q5v9z',
        status: 'active',
        connected: true,
        lastSync: '30 mins ago'
      }
    ]
  }
];

export function AdminAccountsViewer() {
  const [expandedUsers, setExpandedUsers] = useState<Set<string>>(new Set());

  const toggleUser = (userId: string) => {
    setExpandedUsers(prev => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  };

  const getBrokerBadgeColor = (broker: string) => {
    const colors = {
      tradelocker: 'border-blue-400 text-blue-400 bg-blue-950',
      topstep: 'border-purple-400 text-purple-400 bg-purple-950',
      truforex: 'border-green-400 text-green-400 bg-green-950'
    };
    return colors[broker as keyof typeof colors] || 'border-gray-500 text-gray-400';
  };

  const totalAccounts = mockUserAccounts.reduce((sum, user) => sum + user.brokerAccounts.length, 0);
  const activeAccounts = mockUserAccounts.reduce((sum, user) => 
    sum + user.brokerAccounts.filter(acc => acc.connected).length, 0
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-white mb-1">All User Accounts & API Keys</h2>
        <p className="text-sm text-gray-400">
          Admin view of all connected broker accounts and their API keys
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Total Users</p>
            <p className="text-white text-2xl">{mockUserAccounts.length}</p>
          </CardContent>
        </Card>
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Total Accounts</p>
            <p className="text-white text-2xl">{totalAccounts}</p>
          </CardContent>
        </Card>
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Active Accounts</p>
            <p className="text-[#00ffc2] text-2xl">{activeAccounts}</p>
          </CardContent>
        </Card>
      </div>

      {/* Users List */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Key className="h-5 w-5" />
            User Accounts & API Keys
          </CardTitle>
          <CardDescription className="text-gray-400">
            View and manage all user broker accounts and their authentication keys
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {mockUserAccounts.map((userAccount) => (
            <Collapsible
              key={userAccount.userId}
              open={expandedUsers.has(userAccount.userId)}
              onOpenChange={() => toggleUser(userAccount.userId)}
            >
              <Card className="bg-[#002b36] border-gray-700">
                <CollapsibleTrigger asChild>
                  <CardHeader className="cursor-pointer hover:bg-[#003545] transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div>
                          <CardTitle className="text-white">{userAccount.userName}</CardTitle>
                          <CardDescription className="text-gray-400">
                            {userAccount.userEmail}
                          </CardDescription>
                        </div>
                        <Badge variant="outline" className="border-[#00ffc2] text-[#00ffc2]">
                          {userAccount.plan.toUpperCase()}
                        </Badge>
                        <Badge variant="outline" className="border-gray-600 text-gray-300">
                          {userAccount.brokerAccounts.length} account{userAccount.brokerAccounts.length !== 1 ? 's' : ''}
                        </Badge>
                      </div>
                      <Button variant="ghost" size="sm" className="p-2">
                        {expandedUsers.has(userAccount.userId) ? (
                          <ChevronUp className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        )}
                      </Button>
                    </div>
                  </CardHeader>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <CardContent className="pt-0 space-y-4">
                    {userAccount.brokerAccounts.map((account) => (
                      <Card key={account.accountId} className="bg-[#001f29] border-gray-800">
                        <CardContent className="p-4 space-y-3">
                          {/* Account Header */}
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="text-white">{account.accountName}</h4>
                                <Badge 
                                  variant="outline" 
                                  className={getBrokerBadgeColor(account.broker)}
                                >
                                  {getBrokerDisplayName(account.broker as any)}
                                </Badge>
                                <Badge
                                  variant="outline"
                                  className={
                                    account.connected
                                      ? 'border-green-500 text-green-400 bg-green-950'
                                      : 'border-red-500 text-red-400 bg-red-950'
                                  }
                                >
                                  {account.connected ? 'Connected' : 'Disconnected'}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-gray-400">
                                <span>Account ID: {account.accountId}</span>
                                <span>Last Sync: {account.lastSync}</span>
                              </div>
                            </div>
                          </div>

                          {/* API Key */}
                          <div className="pt-3 border-t border-gray-700">
                            <ApiKeyDisplay
                              apiKey={account.apiKey}
                              accountId={account.accountId}
                              accountName={account.accountName}
                              broker={getBrokerDisplayName(account.broker as any)}
                              showLabel={true}
                              compact={false}
                            />
                          </div>
                        </CardContent>
                      </Card>
                    ))}

                    {userAccount.brokerAccounts.length === 0 && (
                      <div className="text-center py-8 text-gray-400">
                        <p className="text-sm">No broker accounts connected</p>
                      </div>
                    )}
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
