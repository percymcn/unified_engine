"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { Menu, Sparkles, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

/**
 * Premium 2026 Landing Header
 *
 * Features:
 * - Glassmorphism navbar with animated backdrop
 * - Smooth scroll behavior
 * - Animated hover states
 * - Mobile-responsive drawer
 * - SmartFlow feature highlight
 */

const navItems = [
  { label: "Features", href: "#features" },
  { label: "SmartFlow", href: "#smartflow", isNew: true },
  { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
];

export function LandingHeader() {
  const [isScrolled, setIsScrolled] = React.useState(false);
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeSection, setActiveSection] = React.useState("");

  React.useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);

      // Detect active section
      const sections = navItems.map((item) => item.href.replace("#", ""));
      for (const section of sections.reverse()) {
        const element = document.getElementById(section);
        if (element) {
          const rect = element.getBoundingClientRect();
          if (rect.top <= 200) {
            setActiveSection(section);
            break;
          }
        }
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-500",
        isScrolled
          ? "bg-background/70 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/5"
          : "bg-transparent"
      )}
    >
      <nav className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <motion.div
            whileHover={{ rotate: 5, scale: 1.05 }}
            transition={{ duration: 0.2 }}
            className="relative"
          >
            <Image
              src="/logo.png"
              alt="Tradeflow"
              width={36}
              height={36}
              className="rounded-lg"
            />
            {/* Glow effect */}
            <div className="absolute inset-0 rounded-lg bg-primary/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
          </motion.div>
          <span className="text-xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text group-hover:from-primary group-hover:to-emerald-400 transition-all duration-300">
            Tradeflow
          </span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative px-4 py-2 text-sm font-medium transition-all duration-300 rounded-xl",
                "hover:bg-white/5",
                activeSection === item.href.replace("#", "")
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <span className="flex items-center gap-1.5">
                {item.label}
                {item.isNew && (
                  <span className="px-1.5 py-0.5 rounded-full bg-green-500/20 border border-green-500/30 text-[10px] font-bold text-green-400">
                    NEW
                  </span>
                )}
              </span>
              {/* Active indicator */}
              {activeSection === item.href.replace("#", "") && (
                <motion.div
                  layoutId="activeSection"
                  className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary"
                  transition={{ duration: 0.3 }}
                />
              )}
            </Link>
          ))}
        </div>

        {/* Desktop CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <Button
            variant="ghost"
            asChild
            className="text-muted-foreground hover:text-foreground hover:bg-white/5"
          >
            <Link href="/login">Log in</Link>
          </Button>
          <Button
            asChild
            className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 shadow-lg shadow-green-500/20 hover:shadow-green-500/30 transition-all duration-300"
          >
            <Link href="/register">
              Get Started
              <Sparkles className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>

        {/* Mobile Menu */}
        <Sheet open={isOpen} onOpenChange={setIsOpen}>
          <SheetTrigger asChild className="md:hidden">
            <Button variant="ghost" size="icon" className="hover:bg-white/5">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Toggle menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent
            side="right"
            className="w-[300px] bg-background/95 backdrop-blur-xl border-l border-white/10"
          >
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <Image
                  src="/logo.png"
                  alt="Tradeflow"
                  width={32}
                  height={32}
                  className="rounded-lg"
                />
                <span className="bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
                  Tradeflow
                </span>
              </SheetTitle>
            </SheetHeader>
            <div className="flex flex-col gap-2 mt-8">
              {navItems.map((item, index) => (
                <motion.div
                  key={item.href}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <a
                    href={item.href}
                    onClick={() => setIsOpen(false)}
                    className="flex items-center justify-between px-4 py-3 rounded-xl text-lg font-medium text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all"
                  >
                    <span>{item.label}</span>
                    {item.isNew && (
                      <span className="px-2 py-0.5 rounded-full bg-green-500/20 border border-green-500/30 text-xs font-bold text-green-400">
                        NEW
                      </span>
                    )}
                  </a>
                </motion.div>
              ))}
              <div className="flex flex-col gap-2 mt-6 pt-6 border-t border-white/10">
                <Button
                  variant="outline"
                  asChild
                  className="bg-white/5 border-white/10 hover:bg-white/10"
                >
                  <Link href="/login" onClick={() => setIsOpen(false)}>
                    Log in
                  </Link>
                </Button>
                <Button
                  asChild
                  className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
                >
                  <Link href="/register" onClick={() => setIsOpen(false)}>
                    Get Started
                    <Sparkles className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </nav>
    </motion.header>
  );
}
