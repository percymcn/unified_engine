import { useState } from 'react';
import { 
  User, 
  Settings, 
  CreditCard, 
  Bell, 
  LogOut, 
  Palette,
  KeyRound
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from './ui/dropdown-menu';
import { Button } from './ui/button';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { useUser } from '../contexts/UserContext';
import { useTheme, THEME_CONFIG } from '../contexts/ThemeContext';
import { ThemeSelector } from './ThemeSelector';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner@2.0.3';

interface SettingsDropdownProps {
  onNavigate: (section: string) => void;
}

export function SettingsDropdown({ onNavigate }: SettingsDropdownProps) {
  const { user, logout } = useUser();
  const { theme, setTheme } = useTheme();
  const [profileDialogOpen, setProfileDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [notificationsDialogOpen, setNotificationsDialogOpen] = useState(false);

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully');
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  if (!user) return null;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="ghost" 
            className="relative h-10 w-10 rounded-full p-0 hover:bg-[#002b36]"
          >
            <Avatar className="h-10 w-10">
              <AvatarImage src={user.avatarUrl} alt={user.name} />
              <AvatarFallback className="bg-[#00ffc2] text-[#001f29]">
                {getInitials(user.name)}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-64 bg-[#001f29] border-gray-800" align="end">
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm text-white">{user.name}</p>
              <p className="text-xs text-gray-400">{user.email}</p>
              <div className="flex gap-2 mt-2">
                <span className="inline-flex items-center rounded-full bg-[#00ffc2]/10 px-2 py-1 text-xs text-[#00ffc2] border border-[#00ffc2]/20">
                  {user.plan.charAt(0).toUpperCase() + user.plan.slice(1)}
                </span>
                {user.role === 'admin' && (
                  <span className="inline-flex items-center rounded-full bg-purple-500/10 px-2 py-1 text-xs text-purple-400 border border-purple-500/20">
                    Admin
                  </span>
                )}
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator className="bg-gray-800" />
          
          <DropdownMenuItem 
            onClick={() => setProfileDialogOpen(true)}
            className="cursor-pointer text-gray-300 focus:bg-[#002b36] focus:text-white"
          >
            <User className="mr-2 h-4 w-4" />
            <span>Profile & Preferences</span>
          </DropdownMenuItem>

          <DropdownMenuItem 
            onClick={() => setPasswordDialogOpen(true)}
            className="cursor-pointer text-gray-300 focus:bg-[#002b36] focus:text-white"
          >
            <KeyRound className="mr-2 h-4 w-4" />
            <span>Reset Password</span>
          </DropdownMenuItem>

          <ThemeSelector
            trigger={
              <DropdownMenuItem 
                className="cursor-pointer text-gray-300 focus:bg-[#002b36] focus:text-white"
                onSelect={(e) => {
                  e.preventDefault();
                }}
              >
                <Palette className="mr-2 h-4 w-4" />
                <span>Theme: {THEME_CONFIG[theme].name}</span>
              </DropdownMenuItem>
            }
          />

          <DropdownMenuItem 
            onClick={() => {
              onNavigate('billing');
            }}
            className="cursor-pointer text-gray-300 focus:bg-[#002b36] focus:text-white"
          >
            <CreditCard className="mr-2 h-4 w-4" />
            <span>Billing & Subscription</span>
          </DropdownMenuItem>

          <DropdownMenuItem 
            onClick={() => setNotificationsDialogOpen(true)}
            className="cursor-pointer text-gray-300 focus:bg-[#002b36] focus:text-white"
          >
            <Bell className="mr-2 h-4 w-4" />
            <span>Notifications</span>
          </DropdownMenuItem>

          <DropdownMenuSeparator className="bg-gray-800" />
          
          <DropdownMenuItem 
            onClick={handleLogout}
            className="cursor-pointer text-red-400 focus:bg-red-500/10 focus:text-red-400"
          >
            <LogOut className="mr-2 h-4 w-4" />
            <span>Logout</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Profile Dialog */}
      <Dialog open={profileDialogOpen} onOpenChange={setProfileDialogOpen}>
        <DialogContent className="bg-[#001f29] border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle>Profile & Preferences</DialogTitle>
            <DialogDescription className="text-gray-400">
              Update your personal information
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input 
                id="name" 
                defaultValue={user.name} 
                className="bg-[#002b36] border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input 
                id="email" 
                type="email" 
                defaultValue={user.email} 
                className="bg-[#002b36] border-gray-700 text-white"
                disabled
              />
              <p className="text-xs text-gray-400">Email cannot be changed</p>
            </div>
            <Button 
              onClick={() => {
                toast.success('Profile updated successfully');
                setProfileDialogOpen(false);
              }}
              className="w-full bg-[#00ffc2] text-[#001f29] hover:bg-[#00ffc2]/90"
            >
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Password Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent className="bg-[#001f29] border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription className="text-gray-400">
              Choose a new password for your account
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="current-password">Current Password</Label>
              <Input 
                id="current-password" 
                type="password" 
                className="bg-[#002b36] border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-password">New Password</Label>
              <Input 
                id="new-password" 
                type="password" 
                className="bg-[#002b36] border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm New Password</Label>
              <Input 
                id="confirm-password" 
                type="password" 
                className="bg-[#002b36] border-gray-700 text-white"
              />
            </div>
            <Button 
              onClick={() => {
                toast.success('Password updated successfully');
                setPasswordDialogOpen(false);
              }}
              className="w-full bg-[#00ffc2] text-[#001f29] hover:bg-[#00ffc2]/90"
            >
              Update Password
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Notifications Dialog */}
      <Dialog open={notificationsDialogOpen} onOpenChange={setNotificationsDialogOpen}>
        <DialogContent className="bg-[#001f29] border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle>Notification Preferences</DialogTitle>
            <DialogDescription className="text-gray-400">
              Manage your notification settings
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm">Trade Notifications</p>
                <p className="text-xs text-gray-400">Get notified when trades are executed</p>
              </div>
              <input type="checkbox" defaultChecked className="toggle" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm">Risk Alerts</p>
                <p className="text-xs text-gray-400">Alerts when risk thresholds are exceeded</p>
              </div>
              <input type="checkbox" defaultChecked className="toggle" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm">Billing Updates</p>
                <p className="text-xs text-gray-400">Payment and subscription notifications</p>
              </div>
              <input type="checkbox" defaultChecked className="toggle" />
            </div>
            <Button 
              onClick={() => {
                toast.success('Notification preferences saved');
                setNotificationsDialogOpen(false);
              }}
              className="w-full bg-[#00ffc2] text-[#001f29] hover:bg-[#00ffc2]/90"
            >
              Save Preferences
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
