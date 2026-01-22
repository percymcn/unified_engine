"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, Server, ArrowRight, CheckCircle2, TrendingUp } from "lucide-react";

/**
 * SignalFlowAnimation Component
 *
 * Animated visualization showing the signal flow:
 * TradingView Alert -> Tradeflow Processing -> Broker Execution
 *
 * Animation sequence:
 * 1. Signal pulse from TradingView (left)
 * 2. Arrow animation flowing right
 * 3. Processing pulse in center (Tradeflow)
 * 4. Arrow animation flowing right
 * 5. Execution confirmation at broker (right)
 * 6. "<50ms" flash to show speed
 *
 * Uses framer-motion for smooth, GPU-accelerated animations.
 * The sequence loops continuously to demonstrate the automation.
 */

interface SignalStep {
  id: string;
  label: string;
  sublabel: string;
  icon: React.ElementType;
  color: string;
}

const steps: SignalStep[] = [
  {
    id: "tradingview",
    label: "TradingView",
    sublabel: "Alert Triggers",
    icon: TrendingUp,
    color: "text-blue-400",
  },
  {
    id: "tradeflow",
    label: "Tradeflow",
    sublabel: "Processing",
    icon: Server,
    color: "text-purple-400",
  },
  {
    id: "broker",
    label: "Broker",
    sublabel: "Order Executed",
    icon: CheckCircle2,
    color: "text-green-400",
  },
];

export function SignalFlowAnimation() {
  const [activeStep, setActiveStep] = useState(0);
  const [showSpeed, setShowSpeed] = useState(false);

  // Animation loop: cycle through steps
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => {
        const next = (prev + 1) % 4; // 0, 1, 2, 3 (3 = reset/flash)
        if (next === 3) {
          setShowSpeed(true);
          setTimeout(() => setShowSpeed(false), 800);
          return 0; // Reset to start
        }
        return next;
      });
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Watch How Signals Become Trades
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            From TradingView alert to broker execution in milliseconds
          </p>
        </motion.div>

        {/* Main animation container */}
        <div className="max-w-4xl mx-auto">
          <div className="relative bg-card rounded-xl border p-8 overflow-hidden">
            {/* Background grid effect */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#8882_1px,transparent_1px),linear-gradient(to_bottom,#8882_1px,transparent_1px)] bg-[size:2rem_2rem] opacity-30" />

            {/* Speed flash overlay */}
            <AnimatePresence>
              {showSpeed && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.1 }}
                  className="absolute inset-0 flex items-center justify-center bg-green-500/10 z-20"
                >
                  <div className="text-center">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="inline-flex items-center gap-2 px-6 py-3 bg-green-500/20 border border-green-500/40 rounded-full"
                    >
                      <Zap className="h-6 w-6 text-green-400" />
                      <span className="text-2xl font-bold text-green-400">&lt;50ms</span>
                    </motion.div>
                    <motion.p
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className="mt-2 text-green-400 font-medium"
                    >
                      Trade Executed!
                    </motion.p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Steps */}
            <div className="relative z-10 flex items-center justify-between gap-4">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center flex-1">
                  {/* Step node */}
                  <motion.div
                    animate={{
                      scale: activeStep === index ? 1.1 : 1,
                      opacity: activeStep >= index ? 1 : 0.5,
                    }}
                    transition={{ duration: 0.3 }}
                    className="flex-shrink-0"
                  >
                    <div
                      className={`relative w-20 h-20 md:w-24 md:h-24 rounded-xl border-2 flex flex-col items-center justify-center transition-all duration-300 ${
                        activeStep >= index
                          ? "border-primary/50 bg-primary/10"
                          : "border-border bg-card"
                      }`}
                    >
                      {/* Pulse animation when active */}
                      {activeStep === index && (
                        <motion.div
                          initial={{ scale: 1, opacity: 0.5 }}
                          animate={{ scale: 1.5, opacity: 0 }}
                          transition={{ duration: 1, repeat: Infinity }}
                          className="absolute inset-0 rounded-xl border-2 border-primary"
                        />
                      )}
                      <step.icon className={`h-6 w-6 md:h-8 md:w-8 ${step.color}`} />
                      <span className="text-xs md:text-sm font-medium mt-1">{step.label}</span>
                      <span className="text-[10px] md:text-xs text-muted-foreground">
                        {step.sublabel}
                      </span>
                    </div>
                  </motion.div>

                  {/* Arrow connector (except after last step) */}
                  {index < steps.length - 1 && (
                    <div className="flex-1 flex items-center justify-center px-2 md:px-4">
                      <div className="relative w-full h-1 bg-border rounded-full overflow-hidden">
                        {/* Animated signal pulse */}
                        <motion.div
                          initial={{ x: "-100%" }}
                          animate={{
                            x: activeStep > index ? "100%" : "-100%",
                          }}
                          transition={{
                            duration: 0.5,
                            ease: "easeInOut",
                          }}
                          className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-primary to-transparent"
                        />
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0 -ml-1" />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Live indicator */}
            <div className="mt-8 flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <div className="relative">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <div className="absolute inset-0 w-2 h-2 rounded-full bg-green-500 animate-ping" />
              </div>
              <span>Live Demo - Signals process in real-time, 24/7</span>
            </div>
          </div>

          {/* Caption */}
          <p className="text-center text-sm text-muted-foreground mt-4">
            Animated demonstration of signal flow. Actual execution speed: &lt;50ms average.
          </p>
        </div>
      </div>
    </section>
  );
}
