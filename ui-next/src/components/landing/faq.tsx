"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "What brokers does Tradeflow support?",
    answer: "Tradeflow supports TradeLocker, Tradovate, TopStep, ProjectX, and MetaTrader 4 & 5. We're continuously expanding our broker integrations."
  },
  {
    question: "How secure are my API credentials?",
    answer: "Your broker credentials are encrypted using AES-256 and stored securely on our servers. They are never exposed in logs or shared with third parties, and are only used to execute trades on your behalf. You can revoke access at any time."
  },
  {
    question: "What happens if TradingView goes down?",
    answer: "Tradeflow only processes signals it receives. If TradingView is unavailable, no signals are sent. We recommend setting up native alerts in your broker platform as a backup for critical positions."
  },
  {
    question: "Can I route signals to multiple accounts?",
    answer: "Yes! One signal can execute across multiple broker accounts simultaneously. You can route to all connected accounts, a specific group, or hand-pick target accounts per signal."
  },
  {
    question: "How fast are trades executed?",
    answer: "Average execution time is under 55ms from when we receive your TradingView webhook to when the order is placed with your broker."
  },
  {
    question: "Is there a free plan?",
    answer: "Yes! Our free plan includes up to 50 signals per day with basic signal routing. Upgrade to Starter ($29/mo), Trader ($59/mo), Pro ($99/mo), or Enterprise ($199/mo) for more features."
  },
  {
    question: "Can I limit when signals execute?",
    answer: "Yes! Trading Session Control lets you define exactly which hours and days signals are accepted. Signals that arrive outside your session are automatically paused. You can set custom hours with timezone support for any market session."
  },
  {
    question: "What is Signal Intelligence Guard?",
    answer: "Signal Intelligence Guard is Tradeflow's self-protecting execution layer that screens every incoming signal before execution. It includes:\n\n• Chop Detection — automatically detects sideways markets and pauses new entries\n• Stale Signal Rejection — blocks old signals that arrive late\n• Position P&L Protection — warns/blocks when trading against profitable positions\n• Profit Lock — tracks peak profit and only allows flips when profit drops significantly\n• Auto-Breakeven — moves stop loss to entry when momentum shifts\n\nWhen a guard fires, you can choose to execute, discard, or let the system handle it automatically."
  },
  {
    question: "What is Profit Lock Protection?",
    answer: "Profit Lock is a smart exit protection feature. When you're in a profitable trade, it tracks your peak unrealized profit. If a flip signal comes in (sell when you're long, or buy when you're short), Profit Lock checks whether your profit is still near the peak or has dropped significantly.\n\n• If profit is near peak → flip is BLOCKED (probably noise/consolidation)\n• If profit dropped 50%+ from peak → flip is ALLOWED (trend likely changed)\n\nThis prevents you from closing winners during brief pullbacks while still letting you exit when the trend actually reverses."
  },
  {
    question: "What risk management controls are available?",
    answer: "Each account has its own risk settings that override your global defaults:\n\n• Max daily trades — stops new entries after a set count\n• Max daily loss ($ or %) — halts trading if daily drawdown is hit\n• Daily profit target — locks in gains by halting when target is reached\n• Trade cooldown — enforces a waiting period between trades\n• Max open positions (total and per symbol)\n• Max drawdown % from peak equity\n• Min risk/reward ratio — rejects trades with insufficient R:R\n\nAll limits automatically reset at the next trading session (6 PM EST)."
  },
  {
    question: "How does position sizing work?",
    answer: "You can set a sizing mode per account: Fixed lot size, % of balance, % of equity, or Risk-Based (lot size calculated from your risk % and stop loss distance). A max position size cap ensures no single order ever exceeds your limit."
  },
  {
    question: "What AI features are available?",
    answer: "Pro tier includes the AI Strategy Suite: a Pine Script AI Fixer that corrects broken indicator code and explains changes, plus a Strategy Analyzer that reviews your strategy logic and risk-reward profile. Enterprise adds the AI Trading Coach for personalized feedback and bias detection."
  },
];

export function FAQ() {
  return (
    <section id="faq" className="py-20">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-4">
          Frequently Asked Questions
        </h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          Got questions? We&apos;ve got answers.
        </p>

        <div className="max-w-3xl mx-auto">
          <Accordion type="single" collapsible className="w-full">
            {faqs.map((faq, index) => (
              <AccordionItem key={index} value={`item-${index}`}>
                <AccordionTrigger className="text-left">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
}
