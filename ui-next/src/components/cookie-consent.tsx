"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, Cookie, Settings } from "lucide-react";
import Link from "next/link";

const COOKIE_CONSENT_KEY = "tradeflow-cookie-consent";

interface CookiePreferences {
  necessary: boolean;
  analytics: boolean;
  marketing: boolean;
  acceptedAt: string;
}

export function CookieConsent() {
  const [isVisible, setIsVisible] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [preferences, setPreferences] = useState<CookiePreferences>({
    necessary: true, // Always required
    analytics: true,
    marketing: false,
    acceptedAt: "",
  });

  useEffect(() => {
    // Check if user has already consented
    const stored = localStorage.getItem(COOKIE_CONSENT_KEY);
    if (!stored) {
      // Small delay before showing to avoid flash
      const timer = setTimeout(() => setIsVisible(true), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAcceptAll = () => {
    const newPreferences: CookiePreferences = {
      necessary: true,
      analytics: true,
      marketing: true,
      acceptedAt: new Date().toISOString(),
    };
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(newPreferences));
    setIsVisible(false);
  };

  const handleAcceptSelected = () => {
    const newPreferences: CookiePreferences = {
      ...preferences,
      necessary: true, // Always required
      acceptedAt: new Date().toISOString(),
    };
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(newPreferences));
    setIsVisible(false);
  };

  const handleDeclineOptional = () => {
    const newPreferences: CookiePreferences = {
      necessary: true,
      analytics: false,
      marketing: false,
      acceptedAt: new Date().toISOString(),
    };
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(newPreferences));
    setIsVisible(false);
  };

  useEffect(() => {
    if (!isVisible || showSettings) {
      return;
    }
    const timer = setTimeout(() => {
      handleDeclineOptional();
    }, 10000);
    return () => clearTimeout(timer);
  }, [isVisible, showSettings]);

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 md:p-6 pointer-events-none">
      <div className="mx-auto max-w-4xl pointer-events-auto">
        <div className={`rounded-lg border border-border bg-card shadow-lg ${showSettings ? "" : "max-h-[80px]"}`}>
          {!showSettings ? (
            // Main consent view
            <div className="p-3 md:p-4">
              <div className="flex items-center gap-3">
                <div className="hidden md:flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                  <Cookie className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 text-xs text-muted-foreground">
                  We use cookies to improve TradeFlow.{" "}
                  <Link href="/privacy" className="text-primary underline hover:no-underline">
                    Privacy Policy
                  </Link>
                  .
                </div>
                <div className="flex items-center gap-2">
                  <Button onClick={handleAcceptAll} size="sm">
                    Accept
                  </Button>
                  <Button onClick={handleDeclineOptional} variant="outline" size="sm">
                    Necessary
                  </Button>
                  <Button
                    onClick={() => setShowSettings(true)}
                    variant="ghost"
                    size="sm"
                    className="gap-2"
                  >
                    <Settings className="h-4 w-4" />
                    Customize
                  </Button>
                  <button
                    onClick={handleDeclineOptional}
                    className="text-muted-foreground hover:text-foreground"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            // Settings view
            <div className="p-4 md:p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Cookie Preferences</h3>
                <button
                  onClick={() => setShowSettings(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-4 mb-6">
                {/* Necessary cookies */}
                <div className="flex items-start justify-between gap-4 p-3 rounded-lg bg-muted/50">
                  <div>
                    <h4 className="font-medium">Necessary Cookies</h4>
                    <p className="text-sm text-muted-foreground">
                      Required for the website to function. Cannot be disabled.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={true}
                    disabled
                    className="h-5 w-5 rounded border-border"
                  />
                </div>

                {/* Analytics cookies */}
                <div className="flex items-start justify-between gap-4 p-3 rounded-lg border border-border">
                  <div>
                    <h4 className="font-medium">Analytics Cookies</h4>
                    <p className="text-sm text-muted-foreground">
                      Help us understand how visitors interact with our website.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.analytics}
                    onChange={(e) => setPreferences({ ...preferences, analytics: e.target.checked })}
                    className="h-5 w-5 rounded border-border accent-primary"
                  />
                </div>

                {/* Marketing cookies */}
                <div className="flex items-start justify-between gap-4 p-3 rounded-lg border border-border">
                  <div>
                    <h4 className="font-medium">Marketing Cookies</h4>
                    <p className="text-sm text-muted-foreground">
                      Used to deliver personalized advertisements.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences.marketing}
                    onChange={(e) => setPreferences({ ...preferences, marketing: e.target.checked })}
                    className="h-5 w-5 rounded border-border accent-primary"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={handleAcceptSelected} size="sm">
                  Save Preferences
                </Button>
                <Button onClick={handleAcceptAll} variant="outline" size="sm">
                  Accept All
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
