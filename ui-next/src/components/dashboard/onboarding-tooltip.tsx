"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { X, Sparkles, ArrowRight, Webhook, Settings, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

const ONBOARDING_KEY = "tradeflow_onboarding_completed";

interface OnboardingStep {
  title: string;
  description: string;
  icon: React.ReactNode;
  highlight?: string;
}

const steps: OnboardingStep[] = [
  {
    title: "Welcome to Tradeflow!",
    description: "Your automated trading dashboard is ready. Let's get you set up in 3 quick steps.",
    icon: <Sparkles className="h-5 w-5 text-yellow-500" />,
  },
  {
    title: "Connect Your Broker",
    description: "Head to Settings > Accounts to connect your first broker account.",
    icon: <Settings className="h-5 w-5 text-primary" />,
    highlight: "accounts",
  },
  {
    title: "Set Up Webhooks",
    description: "Configure webhooks in Settings > Webhooks to receive TradingView signals.",
    icon: <Webhook className="h-5 w-5 text-blue-500" />,
    highlight: "webhooks",
  },
  {
    title: "Monitor Your Trades",
    description: "Watch your signals execute automatically. Your dashboard shows real-time stats!",
    icon: <BarChart3 className="h-5 w-5 text-green-500" />,
  },
];

export function OnboardingTooltip() {
  const [visible, setVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Check if onboarding was already completed
    const completed = localStorage.getItem(ONBOARDING_KEY);
    if (!completed) {
      // Small delay for smoother appearance
      const timer = setTimeout(() => setVisible(true), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handleComplete = () => {
    setIsExiting(true);
    setTimeout(() => {
      localStorage.setItem(ONBOARDING_KEY, "true");
      setVisible(false);
    }, 300);
  };

  const handleSkip = () => {
    handleComplete();
  };

  if (!visible) return null;

  const step = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;

  return (
    <div
      className={cn(
        "fixed bottom-6 right-6 z-50 max-w-sm transition-all duration-300",
        isExiting ? "opacity-0 translate-y-4" : "opacity-100 translate-y-0"
      )}
    >
      <Card className="glass border-primary/30 shadow-lg shadow-primary/10">
        <CardContent className="p-4">
          {/* Close button */}
          <button
            onClick={handleSkip}
            className="absolute top-2 right-2 p-1 rounded-full hover:bg-muted transition-colors"
            aria-label="Close onboarding"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>

          {/* Step indicator */}
          <div className="flex gap-1 mb-3">
            {steps.map((_, index) => (
              <div
                key={index}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  index === currentStep
                    ? "bg-primary"
                    : index < currentStep
                    ? "bg-primary/50"
                    : "bg-muted"
                )}
              />
            ))}
          </div>

          {/* Content */}
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-primary/10">{step.icon}</div>
            <div className="flex-1 pr-4">
              <h3 className="font-semibold text-sm mb-1">{step.title}</h3>
              <p className="text-xs text-muted-foreground">{step.description}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between mt-4">
            <button
              onClick={handleSkip}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip tutorial
            </button>
            <Button size="sm" onClick={handleNext} className="gap-1">
              {isLastStep ? "Get Started" : "Next"}
              <ArrowRight className="h-3 w-3" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
