import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { useBroker, getBrokerDisplayName, getBrokerIcon, getBrokerColor } from '../contexts/BrokerContext';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Zap,
  Database,
  RefreshCw,
  Activity
} from 'lucide-react';

export function BrokerTestPanel() {
  const { 
    activeBroker, 
    activeBrokerAccount,
    connectedBrokers, 
    isLoading, 
    isSyncing,
    getApiBaseUrl,
    switchBroker,
    refreshBrokerData
  } = useBroker();

  const [events, setEvents] = useState<Array<{ type: string; time: string; detail: any }>>([]);
  const [testResults, setTestResults] = useState({
    contextLoaded: false,
    brokerSet: false,
    apiUrlResolved: false,
    eventsWorking: false
  });

  // Monitor broker events
  useEffect(() => {
    const handleBrokerSwitch = (e: any) => {
      setEvents(prev => [...prev, {
        type: 'broker.switch',
        time: new Date().toLocaleTimeString(),
        detail: e.detail
      }].slice(-10)); // Keep last 10 events
    };

    const handleBrokerRefresh = (e: any) => {
      setEvents(prev => [...prev, {
        type: 'broker.refresh',
        time: new Date().toLocaleTimeString(),
        detail: e.detail
      }].slice(-10));
    };

    window.addEventListener('broker.switch', handleBrokerSwitch);
    window.addEventListener('broker.refresh', handleBrokerRefresh);

    return () => {
      window.removeEventListener('broker.switch', handleBrokerSwitch);
      window.removeEventListener('broker.refresh', handleBrokerRefresh);
    };
  }, []);

  // Update test results
  useEffect(() => {
    setTestResults({
      contextLoaded: !isLoading,
      brokerSet: activeBroker !== null,
      apiUrlResolved: getApiBaseUrl() !== '',
      eventsWorking: events.length > 0
    });
  }, [isLoading, activeBroker, events, getApiBaseUrl]);

  const handleTestSwitch = async (broker: 'tradelocker' | 'topstep' | 'truforex') => {
    await switchBroker(broker);
  };

  const handleTestRefresh = async () => {
    await refreshBrokerData();
  };

  return (
    <div className="space-y-6">
      {/* System Status */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#0EA5E9]" />
            Broker Context System Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Test Results */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2">
              {testResults.contextLoaded ? (
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-sm text-gray-300">Context Loaded</span>
            </div>

            <div className="flex items-center gap-2">
              {testResults.brokerSet ? (
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-sm text-gray-300">Broker Selected</span>
            </div>

            <div className="flex items-center gap-2">
              {testResults.apiUrlResolved ? (
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-sm text-gray-300">API URL Resolved</span>
            </div>

            <div className="flex items-center gap-2">
              {testResults.eventsWorking ? (
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              ) : (
                <Clock className="w-4 h-4 text-yellow-400" />
              )}
              <span className="text-sm text-gray-300">Events Working</span>
            </div>
          </div>

          {/* Current State */}
          <div className="border-t border-gray-700 pt-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Active Broker:</span>
              {activeBroker ? (
                <Badge 
                  variant="outline" 
                  className="border-[#00ffc2] text-[#00ffc2]"
                >
                  {getBrokerIcon(activeBroker)} {getBrokerDisplayName(activeBroker)}
                </Badge>
              ) : (
                <Badge variant="outline" className="border-gray-600 text-gray-400">
                  None
                </Badge>
              )}
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">API Base URL:</span>
              <code className="text-xs text-blue-400 font-mono">
                {getApiBaseUrl() || 'Not set'}
              </code>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Is Syncing:</span>
              <Badge variant={isSyncing ? 'default' : 'outline'}>
                {isSyncing ? 'Yes' : 'No'}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Connected Brokers:</span>
              <Badge variant="outline" className="border-purple-400 text-purple-400">
                {connectedBrokers.length}
              </Badge>
            </div>

            {activeBrokerAccount && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Account ID:</span>
                  <span className="text-xs text-gray-300">{activeBrokerAccount.accountId}</span>
                </div>

                {activeBrokerAccount.lastSync && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Last Sync:</span>
                    <span className="text-xs text-gray-300">
                      {new Date(activeBrokerAccount.lastSync).toLocaleTimeString()}
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Test Controls */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Test Controls
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-gray-400">Test Broker Switching:</p>
            <div className="flex gap-2 flex-wrap">
              <Button
                size="sm"
                onClick={() => handleTestSwitch('tradelocker')}
                disabled={isSyncing}
                className="bg-blue-600 hover:bg-blue-700"
              >
                📈 TradeLocker
              </Button>
              <Button
                size="sm"
                onClick={() => handleTestSwitch('topstep')}
                disabled={isSyncing}
                className="bg-green-600 hover:bg-green-700"
              >
                🎯 TopStep
              </Button>
              <Button
                size="sm"
                onClick={() => handleTestSwitch('truforex')}
                disabled={isSyncing}
                className="bg-orange-600 hover:bg-orange-700"
              >
                📊 TruForex
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm text-gray-400">Test Data Refresh:</p>
            <Button
              size="sm"
              onClick={handleTestRefresh}
              disabled={!activeBroker || isSyncing}
              variant="outline"
              className="border-gray-600 text-gray-300 hover:bg-[#002b36]"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
              Refresh Current Broker
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Event Log */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-[#0EA5E9]" />
              Event Log
            </CardTitle>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setEvents([])}
              className="text-gray-400 hover:text-white"
            >
              Clear
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">
              No events yet. Try switching brokers or refreshing data.
            </p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {events.slice().reverse().map((event, index) => (
                <div
                  key={index}
                  className="bg-[#002b36] border border-gray-700 rounded p-3 text-xs"
                >
                  <div className="flex items-center justify-between mb-1">
                    <Badge 
                      variant="outline" 
                      className={
                        event.type === 'broker.switch' 
                          ? 'border-yellow-400 text-yellow-400'
                          : 'border-blue-400 text-blue-400'
                      }
                    >
                      {event.type}
                    </Badge>
                    <span className="text-gray-400">{event.time}</span>
                  </div>
                  <pre className="text-gray-300 overflow-x-auto">
                    {JSON.stringify(event.detail, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Connected Brokers List */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Connected Brokers</CardTitle>
        </CardHeader>
        <CardContent>
          {connectedBrokers.length === 0 ? (
            <Alert className="bg-[#002b36] border-gray-700">
              <AlertDescription className="text-gray-400">
                No brokers connected. Use the Connect Broker page to add brokers.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-2">
              {connectedBrokers.map((broker) => (
                <div
                  key={`${broker.broker}-${broker.accountId}`}
                  className="flex items-center justify-between p-3 bg-[#002b36] border border-gray-700 rounded"
                  style={{
                    borderLeft: broker.broker === activeBroker 
                      ? `3px solid ${getBrokerColor(broker.broker)}`
                      : '3px solid transparent'
                  }}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{getBrokerIcon(broker.broker)}</span>
                    <div>
                      <p className="text-sm text-white">{getBrokerDisplayName(broker.broker)}</p>
                      <p className="text-xs text-gray-400">{broker.accountName}</p>
                    </div>
                  </div>
                  {broker.broker === activeBroker && (
                    <Badge className="bg-[#00ffc2] text-[#002b36]">Active</Badge>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
