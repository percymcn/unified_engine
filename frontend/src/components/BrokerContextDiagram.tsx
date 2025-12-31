import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { ArrowDown, Database, RefreshCw, Zap } from 'lucide-react';

export function BrokerContextDiagram() {
  return (
    <div className="space-y-6">
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Broker Context Architecture</CardTitle>
          <p className="text-sm text-gray-400">
            Visual representation of dynamic broker switching data flow
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Global State */}
            <div className="text-center">
              <div className="inline-block bg-[#002b36] border-2 border-[#0EA5E9] rounded-lg p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Database className="w-5 h-5 text-[#0EA5E9]" />
                  <h3 className="text-white">BrokerContext (Global State)</h3>
                </div>
                <div className="space-y-2 text-sm text-left">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-[#0EA5E9]">activeBroker</Badge>
                    <span className="text-gray-300">"topstep"</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-600">isSyncing</Badge>
                    <span className="text-gray-300">false</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-purple-600">connectedBrokers</Badge>
                    <span className="text-gray-300">[3]</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Arrow Down */}
            <div className="flex justify-center">
              <ArrowDown className="w-6 h-6 text-gray-500" />
            </div>

            {/* Event Layer */}
            <div className="text-center">
              <div className="inline-block bg-[#002b36] border border-yellow-500 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Zap className="w-4 h-4 text-yellow-500" />
                  <span className="text-yellow-400 text-sm">Event: broker.switch</span>
                </div>
                <div className="text-xs text-gray-400 font-mono">
                  {`{ broker: "topstep", accountId: "TSX-12345" }`}
                </div>
              </div>
            </div>

            {/* Arrow Down */}
            <div className="flex justify-center">
              <ArrowDown className="w-6 h-6 text-gray-500" />
            </div>

            {/* Component Layer */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { name: 'Balance', endpoint: '/balance', color: 'blue' },
                { name: 'Positions', endpoint: '/positions', color: 'green' },
                { name: 'Orders', endpoint: '/orders', color: 'purple' },
                { name: 'Risk', endpoint: '/risk', color: 'orange' }
              ].map((component) => (
                <div
                  key={component.name}
                  className="bg-[#002b36] border border-gray-700 rounded-lg p-4 text-center"
                >
                  <div className="flex items-center justify-center gap-1 mb-2">
                    <RefreshCw className={`w-3 h-3 text-${component.color}-400`} />
                    <h4 className="text-white text-sm">{component.name}</h4>
                  </div>
                  <div className="text-xs text-gray-400 font-mono">
                    GET {component.endpoint}
                  </div>
                </div>
              ))}
            </div>

            {/* Arrow Down */}
            <div className="flex justify-center">
              <ArrowDown className="w-6 h-6 text-gray-500" />
            </div>

            {/* API Layer */}
            <div className="text-center">
              <div className="inline-block bg-[#002b36] border-2 border-[#00ffc2] rounded-lg p-6">
                <h3 className="text-[#00ffc2] mb-3">API Routing</h3>
                <div className="space-y-2 text-sm text-left font-mono">
                  <div className="text-blue-400">
                    /api/tradelocker/* → TradeLocker Backend
                  </div>
                  <div className="text-green-400">
                    /api/topstep/* → TopStep Backend
                  </div>
                  <div className="text-orange-400">
                    /api/truforex/* → TruForex Backend
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Legend */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white text-base">Update Triggers</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <h4 className="text-sm text-gray-400">On Broker Switch</h4>
              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-[#00ffc2] rounded-full"></div>
                  <span className="text-gray-300">All account data</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-[#00ffc2] rounded-full"></div>
                  <span className="text-gray-300">Positions & orders</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-[#00ffc2] rounded-full"></div>
                  <span className="text-gray-300">API keys & settings</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm text-gray-400">On Manual Refresh</h4>
              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                  <span className="text-gray-300">Live positions</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                  <span className="text-gray-300">Account balance</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                  <span className="text-gray-300">Recent trades</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm text-gray-400">Never Updates</h4>
              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-gray-600 rounded-full"></div>
                  <span className="text-gray-300">User profile</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-gray-600 rounded-full"></div>
                  <span className="text-gray-300">Subscription plan</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-gray-600 rounded-full"></div>
                  <span className="text-gray-300">UI preferences</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
