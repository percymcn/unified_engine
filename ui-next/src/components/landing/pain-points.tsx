"use client";

import { motion } from "framer-motion";
import { XCircle, CheckCircle2, Clock, Eye, Zap, Moon } from "lucide-react";

/**
 * Pain Points Section
 *
 * Before/after cards showing trader pain points and how Tradeflow solves them.
 * Uses emotional language that resonates with traders who've experienced these frustrations.
 */

interface PainPoint {
  before: {
    icon: React.ElementType;
    title: string;
    description: string;
  };
  after: {
    icon: React.ElementType;
    title: string;
    description: string;
  };
}

const painPoints: PainPoint[] = [
  {
    before: {
      icon: Eye,
      title: "Staring at Charts 24/7",
      description: "Glued to screens, waiting for setups. Miss one bathroom break and miss the trade.",
    },
    after: {
      icon: Moon,
      title: "Trade While You Sleep",
      description: "Set your TradingView alerts once. Tradeflow executes while you rest.",
    },
  },
  {
    before: {
      icon: Clock,
      title: "Slow Manual Execution",
      description: "By the time you switch apps and place the order, price has moved against you.",
    },
    after: {
      icon: Zap,
      title: "<50ms Lightning Execution",
      description: "From signal to order in milliseconds. Your edge stays intact.",
    },
  },
  {
    before: {
      icon: XCircle,
      title: "One Broker, One Account",
      description: "Manually copying trades between accounts. Triple the work, triple the mistakes.",
    },
    after: {
      icon: CheckCircle2,
      title: "Multi-Account, Multi-Broker",
      description: "One signal routes to all your accounts automatically. Scale without effort.",
    },
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5 },
  },
};

export function PainPoints() {
  return (
    <section className="py-20 bg-background">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Sound Familiar?
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Every trader knows these frustrations. Here&apos;s how Tradeflow changes the game.
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-6xl mx-auto"
        >
          {painPoints.map((point, index) => (
            <motion.div
              key={index}
              variants={itemVariants}
              className="relative"
            >
              <div className="space-y-4">
                {/* Before card */}
                <div className="p-6 rounded-lg border border-red-500/20 bg-red-500/5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded-lg bg-red-500/10">
                      <point.before.icon className="h-5 w-5 text-red-400" />
                    </div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-red-400">
                      Before
                    </span>
                  </div>
                  <h3 className="font-semibold text-lg mb-2">{point.before.title}</h3>
                  <p className="text-sm text-muted-foreground">{point.before.description}</p>
                </div>

                {/* Arrow/transition indicator */}
                <div className="flex justify-center">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <svg
                      className="w-4 h-4 text-primary"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 14l-7 7m0 0l-7-7m7 7V3"
                      />
                    </svg>
                  </div>
                </div>

                {/* After card */}
                <div className="p-6 rounded-lg border border-green-500/20 bg-green-500/5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded-lg bg-green-500/10">
                      <point.after.icon className="h-5 w-5 text-green-400" />
                    </div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-green-400">
                      With Tradeflow
                    </span>
                  </div>
                  <h3 className="font-semibold text-lg mb-2">{point.after.title}</h3>
                  <p className="text-sm text-muted-foreground">{point.after.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
