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
    answer: "Tradeflow supports TradeLocker, Tradovate, TopStep (ProjectX), and MetaTrader 4/5. We're continuously expanding our broker integrations."
  },
  {
    question: "How secure are my API credentials?",
    answer: "Your API keys are encrypted using AES-256 encryption and stored securely. We never expose your credentials in logs or to third parties. You can revoke access at any time."
  },
  {
    question: "What happens if TradingView goes down?",
    answer: "Tradeflow only processes signals it receives. If TradingView is unavailable, no signals are sent. We recommend setting up alerts in your broker as a backup."
  },
  {
    question: "Can I route signals to multiple accounts?",
    answer: "Yes! Starter plans support 1 account, Trader plans support 2 accounts, Pro supports 4 accounts, and Enterprise supports 8+ accounts. All plans allow routing signals to multiple accounts simultaneously."
  },
  {
    question: "How fast are trades executed?",
    answer: "Average execution time is under 100ms from when we receive your TradingView webhook to when the order is sent to your broker."
  },
  {
    question: "Is there a free plan?",
    answer: "Yes! Our free plan includes up to 50 signals per day with basic signal routing. Upgrade to Starter ($29/mo) or higher for more signals, multiple accounts, and advanced features."
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
