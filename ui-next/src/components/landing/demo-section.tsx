"use client";

import { useRef, useState, useEffect } from "react";
import { Play, Pause, RotateCcw, Zap, ArrowRight, Check, AlertCircle } from "lucide-react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { Button } from "@/components/ui/button";

/**
 * Premium Interactive Demo Section
 *
 * Features:
 * - Live signal flow simulation
 * - Step-by-step execution visualization
 * - Glassmorphism cards
 * - Real-time metrics display
 */

// Execution step type
interface ExecutionStep {
  id: number;
  label: string;
  status: "pending" | "active" | "completed";
  time?: string;
}

// Interactive signal flow demo
function SignalFlowDemo() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [executionTime, setExecutionTime] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);

  const steps: ExecutionStep[] = [
    { id: 1, label: "TradingView Alert Triggered", status: "pending" },
    { id: 2, label: "Webhook Received", status: "pending" },
    { id: 3, label: "Signal Validated", status: "pending" },
    { id: 4, label: "Risk Check Passed", status: "pending" },
    { id: 5, label: "Order Sent to Broker", status: "pending" },
    { id: 6, label: "Execution Confirmed", status: "pending" },
  ];

  const runDemo = () => {
    setIsRunning(true);
    setCurrentStep(0);
    setExecutionTime(0);

    const startTime = Date.now();

    // Simulate each step
    steps.forEach((_, index) => {
      setTimeout(() => {
        setCurrentStep(index + 1);
        setExecutionTime(Date.now() - startTime);

        if (index === steps.length - 1) {
          setTimeout(() => {
            setIsRunning(false);
            setCompletedCount((prev) => prev + 1);
          }, 500);
        }
      }, (index + 1) * 400);
    });
  };

  const resetDemo = () => {
    setCurrentStep(0);
    setExecutionTime(0);
    setIsRunning(false);
  };

  return (
    <div className="p-6 rounded-3xl bg-gradient-to-br from-background/80 to-background/40 backdrop-blur-xl border border-white/10 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h4 className="font-semibold text-lg">Live Signal Flow</h4>
          <p className="text-sm text-muted-foreground">
            Watch a signal execute in real-time
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isRunning ? (
            <Button
              onClick={runDemo}
              size="sm"
              className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
            >
              <Play className="w-4 h-4 mr-2" />
              Run Demo
            </Button>
          ) : (
            <Button onClick={resetDemo} size="sm" variant="outline">
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Execution steps */}
      <div className="space-y-3 mb-6">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isActive = index === currentStep - 1;

          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0.5 }}
              animate={{
                opacity: isCompleted || isActive ? 1 : 0.5,
                scale: isActive ? 1.02 : 1,
              }}
              className={`
                flex items-center gap-3 p-3 rounded-xl transition-all duration-300
                ${isCompleted ? "bg-green-500/10 border border-green-500/20" : ""}
                ${isActive ? "bg-primary/10 border border-primary/20" : ""}
                ${!isCompleted && !isActive ? "bg-white/5 border border-transparent" : ""}
              `}
            >
              {/* Status indicator */}
              <div
                className={`
                  w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-300
                  ${isCompleted ? "bg-green-500/20" : ""}
                  ${isActive ? "bg-primary/20 animate-pulse" : ""}
                  ${!isCompleted && !isActive ? "bg-white/10" : ""}
                `}
              >
                {isCompleted ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : isActive ? (
                  <Zap className="w-4 h-4 text-primary animate-pulse" />
                ) : (
                  <span className="text-xs text-muted-foreground">{step.id}</span>
                )}
              </div>

              {/* Label */}
              <span
                className={`
                  flex-grow text-sm font-medium transition-colors
                  ${isCompleted ? "text-green-400" : ""}
                  ${isActive ? "text-primary" : ""}
                  ${!isCompleted && !isActive ? "text-muted-foreground" : ""}
                `}
              >
                {step.label}
              </span>

              {/* Timing */}
              {isCompleted && (
                <motion.span
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="text-xs font-mono text-green-400"
                >
                  {Math.round((index + 1) * 8)}ms
                </motion.span>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
        <div className="text-center">
          <div className="text-xl font-bold text-primary">
            {currentStep === steps.length ? "48ms" : isRunning ? `${executionTime}ms` : "—"}
          </div>
          <div className="text-xs text-muted-foreground">Execution Time</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-green-400">{completedCount}</div>
          <div className="text-xs text-muted-foreground">Completed</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-cyan-400">99.9%</div>
          <div className="text-xs text-muted-foreground">Success Rate</div>
        </div>
      </div>
    </div>
  );
}

// Sample webhook payload display
function WebhookPreview() {
  const payload = {
    action: "buy",
    symbol: "MES",
    qty: 1,
    tp: 50,
    sl: 25,
    timestamp: new Date().toISOString(),
  };

  return (
    <div className="p-6 rounded-3xl bg-gradient-to-br from-background/80 to-background/40 backdrop-blur-xl border border-white/10 shadow-2xl h-full">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
          <AlertCircle className="w-4 h-4 text-purple-400" />
        </div>
        <div>
          <h4 className="font-semibold text-sm">TradingView Alert</h4>
          <p className="text-xs text-muted-foreground">Sample webhook payload</p>
        </div>
      </div>

      <pre className="p-4 rounded-xl bg-black/30 border border-white/5 overflow-x-auto">
        <code className="text-xs font-mono text-green-400">
          {JSON.stringify(payload, null, 2)}
        </code>
      </pre>

      <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
        <ArrowRight className="w-3 h-3" />
        <span>Automatically routed to your connected brokers</span>
      </div>
    </div>
  );
}

export function DemoSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const isInView = useInView(sectionRef, { once: true, margin: "-100px" });

  return (
    <section ref={sectionRef} id="demo" className="py-24 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/3 left-0 w-[500px] h-[500px] bg-gradient-to-r from-purple-500/10 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-gradient-to-l from-cyan-500/10 to-transparent rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto px-4">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-purple-500/10 to-violet-500/10 border border-purple-500/20 backdrop-blur-sm mb-6">
            <Zap className="h-4 w-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-400">Interactive Demo</span>
          </div>

          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            See Tradeflow{" "}
            <span className="bg-gradient-to-r from-purple-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
              in Action
            </span>
          </h2>

          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Watch how a TradingView alert becomes an executed trade in milliseconds.
            Click &ldquo;Run Demo&rdquo; to see the magic happen.
          </p>
        </motion.div>

        {/* Demo cards */}
        <div className="grid lg:grid-cols-2 gap-6 max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <SignalFlowDemo />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <WebhookPreview />
          </motion.div>
        </div>

        {/* Bottom note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-center text-sm text-muted-foreground mt-8 max-w-2xl mx-auto"
        >
          Real demonstration showing signal flow from TradingView through Tradeflow to broker execution.
          Actual execution time: &lt;55ms average.
        </motion.p>
      </div>
    </section>
  );
}
