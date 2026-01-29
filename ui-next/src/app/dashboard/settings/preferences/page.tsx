"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Clock, Bell, Mail, AlertCircle, BarChart3, Loader2, Palette, Send, MessageSquare, Hash, Phone, ExternalLink } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/providers/theme-provider";

interface NotificationPreferences {
  trade_alerts: boolean;
  error_notifications: boolean;
  daily_summary: boolean;
  email_notifications: boolean;
}

interface PreferencesData {
  timezone: string;
  theme?: string;  // Patch 1.2.1
  notification_preferences: NotificationPreferences;
}

interface MessagingHandles {
  telegram: { enabled: boolean; chat_id: string | null };
  discord: { enabled: boolean; webhook_url: string | null };
  slack: { enabled: boolean; webhook_url: string | null };
  whatsapp: { enabled: boolean; number: string | null };
  user_tier: string;
}

// Common timezones for the dropdown
const COMMON_TIMEZONES = [
  // Americas
  { value: "America/New_York", label: "Eastern Time (New York)" },
  { value: "America/Chicago", label: "Central Time (Chicago)" },
  { value: "America/Denver", label: "Mountain Time (Denver)" },
  { value: "America/Los_Angeles", label: "Pacific Time (Los Angeles)" },
  { value: "America/Phoenix", label: "Arizona (Phoenix)" },
  { value: "America/Toronto", label: "Eastern Time (Toronto)" },
  { value: "America/Vancouver", label: "Pacific Time (Vancouver)" },
  { value: "America/Mexico_City", label: "Central Time (Mexico City)" },
  { value: "America/Sao_Paulo", label: "Brasilia Time (Sao Paulo)" },
  { value: "America/Buenos_Aires", label: "Argentina (Buenos Aires)" },
  // Europe
  { value: "Europe/London", label: "GMT/BST (London)" },
  { value: "Europe/Paris", label: "Central European (Paris)" },
  { value: "Europe/Berlin", label: "Central European (Berlin)" },
  { value: "Europe/Amsterdam", label: "Central European (Amsterdam)" },
  { value: "Europe/Madrid", label: "Central European (Madrid)" },
  { value: "Europe/Rome", label: "Central European (Rome)" },
  { value: "Europe/Zurich", label: "Central European (Zurich)" },
  { value: "Europe/Stockholm", label: "Central European (Stockholm)" },
  { value: "Europe/Moscow", label: "Moscow Time" },
  // Asia
  { value: "Asia/Tokyo", label: "Japan (Tokyo)" },
  { value: "Asia/Shanghai", label: "China (Shanghai)" },
  { value: "Asia/Hong_Kong", label: "Hong Kong" },
  { value: "Asia/Singapore", label: "Singapore" },
  { value: "Asia/Seoul", label: "Korea (Seoul)" },
  { value: "Asia/Dubai", label: "Gulf (Dubai)" },
  { value: "Asia/Kolkata", label: "India (Kolkata)" },
  { value: "Asia/Bangkok", label: "Indochina (Bangkok)" },
  // Pacific
  { value: "Pacific/Sydney", label: "Australia (Sydney)" },
  { value: "Pacific/Auckland", label: "New Zealand (Auckland)" },
  { value: "Pacific/Honolulu", label: "Hawaii (Honolulu)" },
  // UTC
  { value: "UTC", label: "UTC (Coordinated Universal Time)" },
];

function getCurrentTimeInTimezone(timezone: string): string {
  try {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: timezone,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }).format(new Date());
  } catch {
    return "--:--:--";
  }
}

export default function PreferencesPage() {
  const [preferences, setPreferences] = useState<PreferencesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentTime, setCurrentTime] = useState<string>("");
  const { toast } = useToast();
  const { theme, setTheme } = useTheme();  // Patch 1.2.1

  // Messaging handles state
  const [messagingHandles, setMessagingHandles] = useState<MessagingHandles | null>(null);
  const [savingHandles, setSavingHandles] = useState(false);
  const [testingTelegram, setTestingTelegram] = useState(false);

  useEffect(() => {
    fetchPreferences();
    fetchMessagingHandles();
  }, []);

  async function fetchMessagingHandles() {
    try {
      const res = await fetch("/api/notifications/messaging-handles");
      if (res.ok) {
        const data = await res.json();
        setMessagingHandles(data);
      }
    } catch (error) {
      console.error("Failed to fetch messaging handles:", error);
    }
  }

  async function saveMessagingHandles() {
    if (!messagingHandles) return;
    setSavingHandles(true);
    try {
      const res = await fetch("/api/notifications/messaging-handles", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegram_enabled: messagingHandles.telegram.enabled,
          telegram_chat_id: messagingHandles.telegram.chat_id,
          discord_enabled: messagingHandles.discord.enabled,
          discord_webhook_url: messagingHandles.discord.webhook_url,
          slack_enabled: messagingHandles.slack.enabled,
          slack_webhook_url: messagingHandles.slack.webhook_url,
          whatsapp_enabled: messagingHandles.whatsapp.enabled,
          whatsapp_number: messagingHandles.whatsapp.number,
        }),
      });
      if (res.ok) {
        toast({ title: "Saved", description: "Messaging handles updated successfully" });
      } else {
        toast({ title: "Error", description: "Failed to save messaging handles", variant: "destructive" });
      }
    } catch {
      toast({ title: "Error", description: "Failed to save messaging handles", variant: "destructive" });
    } finally {
      setSavingHandles(false);
    }
  }

  async function testTelegramNotification() {
    setTestingTelegram(true);
    try {
      const res = await fetch("/api/notifications/test-telegram", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        toast({ title: "Success", description: "Test notification sent to Telegram" });
      } else {
        toast({ title: "Error", description: data.detail || "Failed to send test", variant: "destructive" });
      }
    } catch {
      toast({ title: "Error", description: "Failed to send test notification", variant: "destructive" });
    } finally {
      setTestingTelegram(false);
    }
  }

  // Update current time display every second
  useEffect(() => {
    if (!preferences?.timezone) return;

    const updateTime = () => {
      setCurrentTime(getCurrentTimeInTimezone(preferences.timezone));
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [preferences?.timezone]);

  async function fetchPreferences() {
    try {
      const res = await fetch("/api/users/me/preferences");
      if (res.ok) {
        const data = await res.json();
        setPreferences(data);
        // Sync theme from backend (Patch 1.2.1)
        if (data.theme && data.theme !== theme) {
          setTheme(data.theme);
        }
      } else {
        // Set defaults on error
        setPreferences({
          timezone: "UTC",
          theme: theme || "system",  // Patch 1.2.1
          notification_preferences: {
            trade_alerts: true,
            error_notifications: true,
            daily_summary: false,
            email_notifications: true,
          },
        });
      }
    } catch (error) {
      console.error("Failed to fetch preferences:", error);
      // Set defaults on error
      setPreferences({
        timezone: "UTC",
        theme: theme || "system",  // Patch 1.2.1
        notification_preferences: {
          trade_alerts: true,
          error_notifications: true,
          daily_summary: false,
          email_notifications: true,
        },
      });
    } finally {
      setLoading(false);
    }
  }

  async function savePreferences() {
    if (!preferences) return;

    setSaving(true);
    try {
      const res = await fetch("/api/users/me/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(preferences),
      });

      if (res.ok) {
        // Update theme cookie immediately (Patch 1.2.1)
        if (preferences.theme) {
          setTheme(preferences.theme);
          // Set cookie for theme preference
          document.cookie = `theme_preference=${preferences.theme}; path=/; max-age=31536000`; // 1 year
        }
        // Refetch preferences to ensure UI is in sync
        await fetchPreferences();
        toast({
          title: "Preferences saved",
          description: "Your preferences have been updated successfully.",
        });
      } else {
        const error = await res.json().catch(() => ({ detail: "Unknown error" }));
        toast({
          title: "Error",
          description: error.detail || "Failed to save preferences",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to save preferences:", error);
      toast({
        title: "Error",
        description: "Failed to save preferences. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  }

  function updateNotificationPref(key: keyof NotificationPreferences, value: boolean) {
    if (!preferences) return;
    setPreferences({
      ...preferences,
      notification_preferences: {
        ...preferences.notification_preferences,
        [key]: value,
      },
    });
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Preferences</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!preferences) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Preferences</h1>
          <p className="text-muted-foreground">Failed to load preferences</p>
        </div>
        <Button onClick={fetchPreferences}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Preferences</h1>
        <p className="text-muted-foreground">
          Customize your timezone and notification settings
        </p>
      </div>

      {/* Theme Settings (Patch 1.2.1) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Appearance
          </CardTitle>
          <CardDescription>
            Choose your theme preference. Applies to dashboard only.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Theme</Label>
            <Select
              value={preferences.theme || theme || "system"}
              onValueChange={(value) => {
                setPreferences({ ...preferences, theme: value });
                setTheme(value);
                // Save immediately
                fetch("/api/users/me/preferences", {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ ...preferences, theme: value }),
                }).then(() => {
                  document.cookie = `theme_preference=${value}; path=/; max-age=31536000`;
                });
              }}
            >
              <SelectTrigger className="w-full md:w-[400px]">
                <SelectValue placeholder="Select theme" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Landing page always remains dark. This setting only affects the dashboard.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Timezone Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Timezone
          </CardTitle>
          <CardDescription>
            Select your timezone for displaying dates and times
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Your Timezone</Label>
            <Select
              value={preferences.timezone}
              onValueChange={(value) =>
                setPreferences({ ...preferences, timezone: value })
              }
            >
              <SelectTrigger className="w-full md:w-[400px]">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                {COMMON_TIMEZONES.map((tz) => (
                  <SelectItem key={tz.value} value={tz.value}>
                    {tz.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Current time preview */}
          <div className="rounded-lg border bg-muted/50 p-4">
            <p className="text-sm text-muted-foreground">Current time in selected timezone:</p>
            <p className="text-2xl font-mono font-semibold">{currentTime}</p>
          </div>
        </CardContent>
      </Card>

      {/* Notification Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notification Preferences
          </CardTitle>
          <CardDescription>
            Configure how and when you receive notifications
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Master Email Toggle */}
          <div className="flex items-center justify-between rounded-lg border p-4 bg-muted/30">
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-blue-500" />
              <div>
                <Label className="text-base">Email Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Master toggle for all email notifications
                </p>
              </div>
            </div>
            <Switch
              checked={preferences.notification_preferences.email_notifications}
              onCheckedChange={(checked) =>
                updateNotificationPref("email_notifications", checked)
              }
            />
          </div>

          {/* Individual notification toggles */}
          <div className="space-y-4">
            {/* Trade Alerts */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <BarChart3 className="h-5 w-5 text-green-500" />
                <div>
                  <Label>Trade Alerts</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive notifications when trades execute
                  </p>
                </div>
              </div>
              <Switch
                checked={preferences.notification_preferences.trade_alerts}
                onCheckedChange={(checked) =>
                  updateNotificationPref("trade_alerts", checked)
                }
                disabled={!preferences.notification_preferences.email_notifications}
              />
            </div>

            {/* Error Notifications */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-red-500" />
                <div>
                  <Label>Error Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Alert me about connection or execution errors
                  </p>
                </div>
              </div>
              <Switch
                checked={preferences.notification_preferences.error_notifications}
                onCheckedChange={(checked) =>
                  updateNotificationPref("error_notifications", checked)
                }
                disabled={!preferences.notification_preferences.email_notifications}
              />
            </div>

            {/* Daily Summary */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5 text-purple-500" />
                <div>
                  <Label>Daily Summary</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive daily trading summary email
                  </p>
                </div>
              </div>
              <Switch
                checked={preferences.notification_preferences.daily_summary}
                onCheckedChange={(checked) =>
                  updateNotificationPref("daily_summary", checked)
                }
                disabled={!preferences.notification_preferences.email_notifications}
              />
            </div>
          </div>

          {!preferences.notification_preferences.email_notifications && (
            <p className="text-sm text-amber-600 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Email notifications are disabled. Enable them to configure individual settings.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Push Notifications (Telegram, Discord, Slack, WhatsApp) */}
      {messagingHandles && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="h-5 w-5" />
              Push Notifications
            </CardTitle>
            <CardDescription>
              Connect messaging apps to receive real-time trade notifications.
              {messagingHandles.user_tier && (
                <Badge variant="outline" className="ml-2">
                  {messagingHandles.user_tier} tier
                </Badge>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Telegram */}
            <div className="space-y-3 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Send className="h-5 w-5 text-blue-400" />
                  <div>
                    <Label className="text-base">Telegram</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive trade alerts via Telegram bot
                    </p>
                  </div>
                </div>
                <Switch
                  checked={messagingHandles.telegram.enabled}
                  onCheckedChange={(checked) =>
                    setMessagingHandles({
                      ...messagingHandles,
                      telegram: { ...messagingHandles.telegram, enabled: checked },
                    })
                  }
                />
              </div>
              {messagingHandles.telegram.enabled && (
                <div className="space-y-2 pl-8">
                  <Label>Telegram Chat ID</Label>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Your Telegram chat ID"
                      value={messagingHandles.telegram.chat_id || ""}
                      onChange={(e) =>
                        setMessagingHandles({
                          ...messagingHandles,
                          telegram: { ...messagingHandles.telegram, chat_id: e.target.value },
                        })
                      }
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={testTelegramNotification}
                      disabled={testingTelegram || !messagingHandles.telegram.chat_id}
                    >
                      {testingTelegram ? <Loader2 className="h-4 w-4 animate-spin" /> : "Test"}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Start a chat with @MyTradeFlowBot, then send /start to get your chat ID.
                  </p>
                </div>
              )}
            </div>

            {/* Discord */}
            <div className="space-y-3 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Hash className="h-5 w-5 text-indigo-400" />
                  <div>
                    <Label className="text-base">Discord</Label>
                    <p className="text-sm text-muted-foreground">
                      Send notifications to a Discord channel
                    </p>
                  </div>
                </div>
                <Switch
                  checked={messagingHandles.discord.enabled}
                  onCheckedChange={(checked) =>
                    setMessagingHandles({
                      ...messagingHandles,
                      discord: { ...messagingHandles.discord, enabled: checked },
                    })
                  }
                />
              </div>
              {messagingHandles.discord.enabled && (
                <div className="space-y-2 pl-8">
                  <Label>Discord Webhook URL</Label>
                  <Input
                    placeholder="https://discord.com/api/webhooks/..."
                    value={messagingHandles.discord.webhook_url || ""}
                    onChange={(e) =>
                      setMessagingHandles({
                        ...messagingHandles,
                        discord: { ...messagingHandles.discord, webhook_url: e.target.value },
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <ExternalLink className="h-3 w-3" />
                    <a href="https://support.discord.com/hc/en-us/articles/228383668" target="_blank" rel="noopener" className="underline">
                      How to create a Discord webhook
                    </a>
                  </p>
                </div>
              )}
            </div>

            {/* Slack */}
            <div className="space-y-3 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <MessageSquare className="h-5 w-5 text-green-500" />
                  <div>
                    <Label className="text-base">Slack</Label>
                    <p className="text-sm text-muted-foreground">
                      Send notifications to a Slack channel
                    </p>
                  </div>
                </div>
                <Switch
                  checked={messagingHandles.slack.enabled}
                  onCheckedChange={(checked) =>
                    setMessagingHandles({
                      ...messagingHandles,
                      slack: { ...messagingHandles.slack, enabled: checked },
                    })
                  }
                />
              </div>
              {messagingHandles.slack.enabled && (
                <div className="space-y-2 pl-8">
                  <Label>Slack Webhook URL</Label>
                  <Input
                    placeholder="https://hooks.slack.com/services/..."
                    value={messagingHandles.slack.webhook_url || ""}
                    onChange={(e) =>
                      setMessagingHandles({
                        ...messagingHandles,
                        slack: { ...messagingHandles.slack, webhook_url: e.target.value },
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <ExternalLink className="h-3 w-3" />
                    <a href="https://api.slack.com/messaging/webhooks" target="_blank" rel="noopener" className="underline">
                      How to create a Slack webhook
                    </a>
                  </p>
                </div>
              )}
            </div>

            {/* WhatsApp */}
            <div className="space-y-3 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Phone className="h-5 w-5 text-emerald-500" />
                  <div>
                    <Label className="text-base">WhatsApp</Label>
                    <Badge variant="secondary" className="ml-2 text-xs">Coming Soon</Badge>
                    <p className="text-sm text-muted-foreground">
                      Receive notifications via WhatsApp
                    </p>
                  </div>
                </div>
                <Switch
                  checked={messagingHandles.whatsapp.enabled}
                  onCheckedChange={(checked) =>
                    setMessagingHandles({
                      ...messagingHandles,
                      whatsapp: { ...messagingHandles.whatsapp, enabled: checked },
                    })
                  }
                  disabled
                />
              </div>
            </div>

            {/* Save Button for Messaging Handles */}
            <div className="flex justify-end">
              <Button onClick={saveMessagingHandles} disabled={savingHandles}>
                {savingHandles ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Messaging Settings"
                )}
              </Button>
            </div>

            {/* Tier Info */}
            <div className="rounded-lg bg-muted/50 p-4 text-sm">
              <p className="font-medium mb-2">Notification Tiers:</p>
              <ul className="space-y-1 text-muted-foreground">
                <li><Badge variant="outline" className="mr-2">Starter</Badge> Price alerts</li>
                <li><Badge variant="outline" className="mr-2">Trader</Badge> + Daily summaries</li>
                <li><Badge variant="outline" className="mr-2">Pro</Badge> + All trade & signal notifications</li>
                <li><Badge variant="outline" className="mr-2">Enterprise</Badge> + Real-time updates & custom alerts</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={savePreferences} disabled={saving} size="lg">
          {saving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            "Save Preferences"
          )}
        </Button>
      </div>
    </div>
  );
}
