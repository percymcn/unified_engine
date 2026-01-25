"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Flame, Trophy, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface StreakData {
  currentStreak: number;
  lastActiveDate: string;
  longestStreak: number;
  totalTradingDays: number;
}

const STREAK_STORAGE_KEY = "tradeflow_streak_data";

function getStreakData(): StreakData {
  if (typeof window === "undefined") {
    return { currentStreak: 0, lastActiveDate: "", longestStreak: 0, totalTradingDays: 0 };
  }

  const stored = localStorage.getItem(STREAK_STORAGE_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      // Invalid data, reset
    }
  }

  return { currentStreak: 0, lastActiveDate: "", longestStreak: 0, totalTradingDays: 0 };
}

function saveStreakData(data: StreakData) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STREAK_STORAGE_KEY, JSON.stringify(data));
}

function getTodayStr() {
  return new Date().toISOString().split("T")[0];
}

function getYesterdayStr() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split("T")[0];
}

export function StreakBadge() {
  const [streak, setStreak] = useState<StreakData | null>(null);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    const data = getStreakData();
    const today = getTodayStr();
    const yesterday = getYesterdayStr();

    // Check if we need to update streak
    if (data.lastActiveDate === today) {
      // Already recorded today
      setStreak(data);
    } else if (data.lastActiveDate === yesterday) {
      // Continuing streak from yesterday
      const newStreak = data.currentStreak + 1;
      const updated: StreakData = {
        currentStreak: newStreak,
        lastActiveDate: today,
        longestStreak: Math.max(newStreak, data.longestStreak),
        totalTradingDays: data.totalTradingDays + 1,
      };
      saveStreakData(updated);
      setStreak(updated);
      setIsNew(true);
      setTimeout(() => setIsNew(false), 3000);
    } else {
      // Streak broken or first day
      const updated: StreakData = {
        currentStreak: 1,
        lastActiveDate: today,
        longestStreak: Math.max(1, data.longestStreak),
        totalTradingDays: data.totalTradingDays + 1,
      };
      saveStreakData(updated);
      setStreak(updated);
      setIsNew(true);
      setTimeout(() => setIsNew(false), 3000);
    }
  }, []);

  if (!streak || streak.currentStreak === 0) return null;

  const getStreakColor = () => {
    if (streak.currentStreak >= 30) return "text-purple-500";
    if (streak.currentStreak >= 14) return "text-orange-500";
    if (streak.currentStreak >= 7) return "text-yellow-500";
    return "text-blue-500";
  };

  const getStreakIcon = () => {
    if (streak.currentStreak >= 30) return Trophy;
    if (streak.currentStreak >= 7) return Flame;
    return Zap;
  };

  const Icon = getStreakIcon();

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="inline-flex">
            <Badge
              variant="outline"
              className={cn(
                "gap-1.5 px-3 py-1 cursor-default transition-all duration-300",
                isNew && "animate-bounce ring-2 ring-yellow-500/50",
                streak.currentStreak >= 7 && "border-orange-500/50 bg-orange-500/10"
              )}
            >
              <Icon className={cn("h-4 w-4", getStreakColor(), isNew && "animate-pulse")} />
              <span className={cn("font-semibold", getStreakColor())}>
                {streak.currentStreak}
              </span>
              <span className="text-muted-foreground text-xs">day streak</span>
            </Badge>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-center">
          <div className="space-y-1">
            <p className="font-semibold">Trading Streak</p>
            <p className="text-xs text-muted-foreground">
              Current: {streak.currentStreak} days
            </p>
            <p className="text-xs text-muted-foreground">
              Longest: {streak.longestStreak} days
            </p>
            <p className="text-xs text-muted-foreground">
              Total: {streak.totalTradingDays} trading days
            </p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
