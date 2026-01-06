import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  Link, 
  RefreshCw, 
  FileText, 
  ArrowRightLeft,
  CheckSquare,
  AlertCircle,
  ChevronRight
} from 'lucide-react';

interface QuickActionsPanelProps {
  onNavigateToAccountSelection?: () => void;
  onNavigateToChangeAccount?: () => void;
  onNavigateToSyncResults?: () => void;
}

export function QuickActionsPanel({ 
  onNavigateToAccountSelection,
  onNavigateToChangeAccount,
  onNavigateToSyncResults 
}: QuickActionsPanelProps) {
  const quickActions = [
    {
      id: 'select-accounts',
      title: 'Select Synced Accounts',
      description: 'Activate accounts after broker sync',
      icon: CheckSquare,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
      onClick: onNavigateToAccountSelection,
      badge: 'New'
    },
    {
      id: 'change-account',
      title: 'Switch Active Account',
      description: 'Change your current trading account',
      icon: ArrowRightLeft,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/20',
      onClick: onNavigateToChangeAccount
    },
    {
      id: 'sync-results',
      title: 'View Sync Results',
      description: 'Check account synchronization status',
      icon: RefreshCw,
      color: 'text-green-400',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/20',
      onClick: onNavigateToSyncResults
    }
  ];

  return (
    <Card className="bg-[#001f29] border-gray-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-white">Quick Actions</CardTitle>
            <CardDescription className="text-gray-400">
              Account management shortcuts
            </CardDescription>
          </div>
          <Link className="w-5 h-5 text-gray-400" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              onClick={action.onClick}
              className={`w-full p-4 rounded-lg border ${action.borderColor} ${action.bgColor} 
                hover:bg-opacity-20 transition-all group text-left relative overflow-hidden`}
            >
              {/* Background gradient on hover */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent 
                opacity-0 group-hover:opacity-100 transition-opacity" />
              
              <div className="relative flex items-start gap-4">
                <div className={`p-2 rounded-lg ${action.bgColor} ${action.borderColor} border`}>
                  <Icon className={`w-5 h-5 ${action.color}`} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-white font-medium">{action.title}</h4>
                    {action.badge && (
                      <Badge className="bg-[#00ffc2] text-[#001f29] text-xs px-2 py-0">
                        {action.badge}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-gray-400">{action.description}</p>
                </div>
                
                <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-gray-400 
                  group-hover:translate-x-1 transition-all flex-shrink-0 mt-1" />
              </div>
            </button>
          );
        })}

        {/* Additional Info */}
        <div className="mt-4 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="text-blue-400 font-medium mb-1">Account Management</p>
              <p className="text-gray-400">
                These features help you manage multiple broker accounts and track synchronization status.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
