"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { UserCircle, Lock, Mail, User, ImageIcon, Calendar, Loader2, Trophy, Zap, Target, TrendingUp, Shield, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface UserProfile {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
}

export default function ProfileSettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const { toast } = useToast();

  // Profile form state
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");

  // Password form state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");

  useEffect(() => {
    fetchProfile();
  }, []);

  async function fetchProfile() {
    try {
      const res = await fetch("/api/users/me/profile");
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
        setFullName(data.full_name || "");
        setEmail(data.email || "");
        setAvatarUrl(data.avatar_url || "");
      } else {
        toast({ title: "Error", description: "Failed to load profile", variant: "destructive" });
      }
    } catch {
      toast({ title: "Error", description: "Failed to load profile", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  async function saveProfile() {
    setSavingProfile(true);
    try {
      const res = await fetch("/api/users/me/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName || null,
          email: email || null,
          avatar_url: avatarUrl || null,
        }),
      });

      if (res.ok) {
        const updatedProfile = await res.json();
        setProfile(updatedProfile);
        toast({ title: "Profile updated", description: "Your profile has been saved successfully" });
      } else {
        const error = await res.json();
        toast({
          title: "Error",
          description: error.detail || "Failed to update profile",
          variant: "destructive"
        });
      }
    } catch {
      toast({ title: "Error", description: "Failed to update profile", variant: "destructive" });
    } finally {
      setSavingProfile(false);
    }
  }

  async function changePassword() {
    // Client-side validation
    setPasswordError("");

    if (!currentPassword) {
      setPasswordError("Current password is required");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match");
      return;
    }

    if (currentPassword === newPassword) {
      setPasswordError("New password must be different from current password");
      return;
    }

    setSavingPassword(true);
    try {
      const res = await fetch("/api/users/me/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      if (res.ok) {
        toast({ title: "Password changed", description: "Your password has been updated successfully" });
        // Clear password fields
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      } else {
        const error = await res.json();
        setPasswordError(error.detail || "Failed to change password");
      }
    } catch {
      setPasswordError("Failed to change password");
    } finally {
      setSavingPassword(false);
    }
  }

  // Password strength indicator
  function getPasswordStrength(password: string): { strength: number; label: string; color: string } {
    if (!password) return { strength: 0, label: "", color: "bg-muted" };

    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    if (score <= 2) return { strength: 33, label: "Weak", color: "bg-red-500" };
    if (score <= 3) return { strength: 66, label: "Medium", color: "bg-yellow-500" };
    return { strength: 100, label: "Strong", color: "bg-green-500" };
  }

  const passwordStrength = getPasswordStrength(newPassword);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Profile Settings</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Profile Settings</h1>
        <p className="text-muted-foreground">
          Manage your account profile and security settings
        </p>
      </div>

      {/* Profile Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserCircle className="h-5 w-5" />
            Profile Information
          </CardTitle>
          <CardDescription>Update your profile details and avatar</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Username (read-only) */}
          <div className="space-y-2">
            <Label htmlFor="username" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Username
            </Label>
            <Input
              id="username"
              value={profile?.username || ""}
              disabled
              className="bg-muted"
            />
            <p className="text-sm text-muted-foreground">
              Username cannot be changed
            </p>
          </div>

          {/* Full Name */}
          <div className="space-y-2">
            <Label htmlFor="fullName" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Full Name
            </Label>
            <Input
              id="fullName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Enter your full name"
              maxLength={100}
            />
          </div>

          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor="email" className="flex items-center gap-2">
              <Mail className="h-4 w-4" />
              Email Address
            </Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </div>

          {/* Avatar URL */}
          <div className="space-y-2">
            <Label htmlFor="avatarUrl" className="flex items-center gap-2">
              <ImageIcon className="h-4 w-4" />
              Avatar URL
            </Label>
            <Input
              id="avatarUrl"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://example.com/avatar.jpg"
              maxLength={500}
            />
            <p className="text-sm text-muted-foreground">
              Enter a URL to an image for your avatar
            </p>
            {avatarUrl && (
              <div className="mt-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={avatarUrl}
                  alt="Avatar preview"
                  className="h-16 w-16 rounded-full object-cover border"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
            )}
          </div>

          {/* Member Since */}
          {profile?.created_at && (
            <div className="pt-2 border-t">
              <p className="text-sm text-muted-foreground flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Member since {new Date(profile.created_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            </div>
          )}

          <Button
            onClick={saveProfile}
            disabled={savingProfile}
            className="mt-4"
          >
            {savingProfile ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Profile"
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Achievement Badges */}
      <Card className="border-primary/20 bg-gradient-to-br from-background to-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-yellow-500" />
            Achievements
          </CardTitle>
          <CardDescription>Your trading milestones and accomplishments</CardDescription>
        </CardHeader>
        <CardContent>
          <TooltipProvider>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {/* First Trade Badge */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center p-4 rounded-xl bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/20 hover:scale-105 transition-transform cursor-default">
                    <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mb-2">
                      <Zap className="h-6 w-6 text-green-500" />
                    </div>
                    <span className="text-xs font-medium text-center">First Trade</span>
                    <Badge variant="outline" className="mt-1 text-[10px] border-green-500/50 text-green-600">Unlocked</Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-semibold">First Trade</p>
                  <p className="text-xs text-muted-foreground">Execute your first trade signal</p>
                </TooltipContent>
              </Tooltip>

              {/* 10 Signals Badge */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-indigo-500/10 border border-blue-500/20 hover:scale-105 transition-transform cursor-default">
                    <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center mb-2">
                      <Target className="h-6 w-6 text-blue-500" />
                    </div>
                    <span className="text-xs font-medium text-center">10 Signals</span>
                    <Badge variant="outline" className="mt-1 text-[10px] border-blue-500/50 text-blue-600">Unlocked</Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-semibold">Signal Starter</p>
                  <p className="text-xs text-muted-foreground">Process 10 trading signals</p>
                </TooltipContent>
              </Tooltip>

              {/* Multi-Broker Badge */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 hover:scale-105 transition-transform cursor-default">
                    <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center mb-2">
                      <TrendingUp className="h-6 w-6 text-purple-500" />
                    </div>
                    <span className="text-xs font-medium text-center">Multi-Broker</span>
                    <Badge variant="outline" className="mt-1 text-[10px] border-purple-500/50 text-purple-600">Unlocked</Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-semibold">Diversified Trader</p>
                  <p className="text-xs text-muted-foreground">Connect 2+ broker accounts</p>
                </TooltipContent>
              </Tooltip>

              {/* Risk Manager Badge */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center p-4 rounded-xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/20 hover:scale-105 transition-transform cursor-default">
                    <div className="w-12 h-12 rounded-full bg-amber-500/20 flex items-center justify-center mb-2">
                      <Shield className="h-6 w-6 text-amber-500" />
                    </div>
                    <span className="text-xs font-medium text-center">Risk Manager</span>
                    <Badge variant="outline" className="mt-1 text-[10px] border-amber-500/50 text-amber-600">Unlocked</Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-semibold">Protected Trader</p>
                  <p className="text-xs text-muted-foreground">Configure risk management settings</p>
                </TooltipContent>
              </Tooltip>

              {/* 100 Signals - Locked */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center p-4 rounded-xl bg-muted/30 border border-muted hover:scale-105 transition-transform cursor-default opacity-50">
                    <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-2">
                      <Star className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <span className="text-xs font-medium text-center text-muted-foreground">100 Signals</span>
                    <Badge variant="outline" className="mt-1 text-[10px]">Locked</Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-semibold">Signal Pro</p>
                  <p className="text-xs text-muted-foreground">Process 100 trading signals</p>
                  <p className="text-xs text-primary mt-1">Progress: 12/100</p>
                </TooltipContent>
              </Tooltip>

              {/* Profitable Month - Locked */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center p-4 rounded-xl bg-muted/30 border border-muted hover:scale-105 transition-transform cursor-default opacity-50">
                    <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-2">
                      <Trophy className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <span className="text-xs font-medium text-center text-muted-foreground">Profit Month</span>
                    <Badge variant="outline" className="mt-1 text-[10px]">Locked</Badge>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-semibold">Monthly Winner</p>
                  <p className="text-xs text-muted-foreground">End a month with positive P&L</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Change Password
          </CardTitle>
          <CardDescription>Update your password to keep your account secure</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current Password */}
          <div className="space-y-2">
            <Label htmlFor="currentPassword">Current Password</Label>
            <Input
              id="currentPassword"
              type="password"
              value={currentPassword}
              onChange={(e) => {
                setCurrentPassword(e.target.value);
                setPasswordError("");
              }}
              placeholder="Enter your current password"
            />
          </div>

          {/* New Password */}
          <div className="space-y-2">
            <Label htmlFor="newPassword">New Password</Label>
            <Input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => {
                setNewPassword(e.target.value);
                setPasswordError("");
              }}
              placeholder="Enter new password (min. 8 characters)"
            />
            {/* Password strength indicator */}
            {newPassword && (
              <div className="space-y-1">
                <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${passwordStrength.color}`}
                    style={{ width: `${passwordStrength.strength}%` }}
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  Password strength: <span className={passwordStrength.strength === 100 ? "text-green-500" : passwordStrength.strength > 33 ? "text-yellow-500" : "text-red-500"}>{passwordStrength.label}</span>
                </p>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm New Password</Label>
            <Input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setPasswordError("");
              }}
              placeholder="Confirm your new password"
            />
            {confirmPassword && newPassword !== confirmPassword && (
              <p className="text-sm text-red-500">Passwords do not match</p>
            )}
          </div>

          {/* Error message */}
          {passwordError && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
              <p className="text-sm text-destructive">{passwordError}</p>
            </div>
          )}

          <Button
            onClick={changePassword}
            disabled={savingPassword || !currentPassword || !newPassword || !confirmPassword}
            variant="secondary"
            className="mt-4"
          >
            {savingPassword ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Changing Password...
              </>
            ) : (
              "Change Password"
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
