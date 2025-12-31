import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Alert, AlertDescription } from './ui/alert';
import { Users, UserCog, Shield, Download, Search, AlertCircle } from 'lucide-react';
import { useUser } from '../contexts/UserContext';

export function AdminPanel() {
  const { user, isAdmin } = useUser();
  
  // Redirect non-admin users
  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <Alert className="bg-red-950 border-red-800">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <AlertDescription className="text-red-200">
            Access Denied: This section is only available to administrators.
          </AlertDescription>
        </Alert>
      </div>
    );
  }
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState('all');

  const users = [
    {
      id: 1,
      name: 'John Doe',
      email: 'john@example.com',
      role: 'owner',
      plan: 'enterprise',
      status: 'active',
      accounts: 5,
      lastLogin: '2025-10-14 14:30',
      created: '2025-01-15'
    },
    {
      id: 2,
      name: 'Jane Smith',
      email: 'jane@example.com',
      role: 'admin',
      plan: 'pro',
      status: 'active',
      accounts: 3,
      lastLogin: '2025-10-14 12:15',
      created: '2025-03-22'
    },
    {
      id: 3,
      name: 'Bob Johnson',
      email: 'bob@example.com',
      role: 'trader',
      plan: 'pro',
      status: 'active',
      accounts: 2,
      lastLogin: '2025-10-13 18:45',
      created: '2025-05-10'
    },
    {
      id: 4,
      name: 'Alice Williams',
      email: 'alice@example.com',
      role: 'viewer',
      plan: 'trial',
      status: 'trial',
      accounts: 1,
      lastLogin: '2025-10-14 09:20',
      created: '2025-10-12'
    }
  ];

  const systemStats = {
    totalUsers: 247,
    activeUsers: 189,
    trialUsers: 23,
    totalRevenue: 9263,
    monthlyRecurring: 9263
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === 'all' || user.role === filterRole;
    return matchesSearch && matchesRole;
  });

  const getRoleBadge = (role: string) => {
    const variants = {
      owner: 'bg-purple-950 border-purple-400 text-purple-300',
      admin: 'bg-blue-950 border-blue-400 text-blue-300',
      trader: 'bg-[#002b36] border-[#00ffc2] text-[#00ffc2]',
      viewer: 'bg-gray-900 border-gray-500 text-gray-400'
    };
    return variants[role as keyof typeof variants];
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'border-[#00ffc2] text-[#00ffc2]',
      trial: 'border-yellow-400 text-yellow-400',
      suspended: 'border-red-400 text-red-400',
      cancelled: 'border-gray-500 text-gray-500'
    };
    return variants[status as keyof typeof variants];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white mb-1">Admin Panel</h2>
          <p className="text-sm text-gray-400">Manage all users, permissions, and system settings</p>
        </div>
        <Badge variant="outline" className="border-purple-400 text-purple-400">
          Administrator View
        </Badge>
      </div>

      <Alert className="bg-purple-950 border-purple-800">
        <Shield className="w-4 h-4 text-purple-400" />
        <AlertDescription className="text-purple-200 text-sm">
          You are viewing the admin panel with full access to all user data, system logs, and configurations.
          Regular users can only see their own data.
        </AlertDescription>
      </Alert>

      {/* System Stats */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-[#00ffc2]" />
              <p className="text-xs text-gray-400">Total Users</p>
            </div>
            <p className="text-white text-2xl">{systemStats.totalUsers}</p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-[#00ffc2]" />
              <p className="text-xs text-gray-400">Active Users</p>
            </div>
            <p className="text-[#00ffc2] text-2xl">{systemStats.activeUsers}</p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-yellow-400" />
              <p className="text-xs text-gray-400">Trial Users</p>
            </div>
            <p className="text-yellow-400 text-2xl">{systemStats.trialUsers}</p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">Total Revenue</p>
            <p className="text-white text-2xl">${systemStats.totalRevenue.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-[#001f29] border-gray-800">
          <CardContent className="p-4">
            <p className="text-xs text-gray-400 mb-1">MRR</p>
            <p className="text-[#00ffc2] text-2xl">${systemStats.monthlyRecurring.toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search users..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-[#002b36] border-gray-700 text-white"
              />
            </div>
            <div className="w-48">
              <Select value={filterRole} onValueChange={setFilterRole}>
                <SelectTrigger className="bg-[#002b36] border-gray-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#002b36] border-gray-700">
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="owner">Owner</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="trader">Trader</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="border-gray-700 text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Users ({filteredUsers.length})</CardTitle>
          <CardDescription className="text-gray-400">
            Manage user access and permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {filteredUsers.map((user) => (
              <div
                key={user.id}
                className="p-4 bg-[#002b36] rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div>
                        <h4 className="text-white">{user.name}</h4>
                        <p className="text-sm text-gray-400">{user.email}</p>
                      </div>
                      <Badge variant="outline" className={getRoleBadge(user.role)}>
                        {user.role}
                      </Badge>
                      <Badge variant="outline" className={getStatusBadge(user.status)}>
                        {user.status}
                      </Badge>
                      <Badge variant="outline" className="border-gray-600 text-gray-300">
                        {user.plan}
                      </Badge>
                    </div>
                    
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-xs text-gray-400">Connected Accounts</p>
                        <p className="text-white">{user.accounts}</p>
                      </div>
                      
                      <div>
                        <p className="text-xs text-gray-400">Last Login</p>
                        <p className="text-white">{user.lastLogin}</p>
                      </div>
                      
                      <div>
                        <p className="text-xs text-gray-400">Member Since</p>
                        <p className="text-white">{user.created}</p>
                      </div>
                      
                      <div>
                        <p className="text-xs text-gray-400">User ID</p>
                        <p className="text-white">#{user.id}</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-gray-700 text-white"
                    >
                      <UserCog className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-gray-700 text-white"
                    >
                      <Shield className="w-4 h-4 mr-1" />
                      Logs
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Role Matrix */}
      <Card className="bg-[#001f29] border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Role & Permission Matrix</CardTitle>
          <CardDescription className="text-gray-400">
            Permission levels for different user roles
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left py-3 px-4 text-gray-400">Permission</th>
                  <th className="text-center py-3 px-4 text-gray-400">Owner</th>
                  <th className="text-center py-3 px-4 text-gray-400">Admin</th>
                  <th className="text-center py-3 px-4 text-gray-400">Trader</th>
                  <th className="text-center py-3 px-4 text-gray-400">Viewer</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['View Dashboard', true, true, true, true],
                  ['Place Orders', true, true, true, false],
                  ['Close Positions', true, true, true, false],
                  ['Modify Risk Settings', true, true, false, false],
                  ['Manage API Keys', true, true, false, false],
                  ['View Logs', true, true, false, false],
                  ['Manage Users', true, true, false, false],
                  ['Billing Access', true, true, false, false],
                  ['Admin Panel', true, true, false, false]
                ].map(([permission, owner, admin, trader, viewer], idx) => (
                  <tr key={idx} className="border-b border-gray-800">
                    <td className="py-3 px-4 text-white">{permission}</td>
                    <td className="py-3 px-4 text-center">
                      {owner ? '✓' : '✗'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {admin ? '✓' : '✗'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {trader ? '✓' : '✗'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {viewer ? '✓' : '✗'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
