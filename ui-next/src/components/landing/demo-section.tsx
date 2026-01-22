"use client";

import { TradeExecutionAnimation } from "./trade-execution-animation";

export function DemoSection() {
  return (
    <section id="demo" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-4">
          See Tradeflow in Action
        </h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          Watch how a TradingView alert becomes an executed trade in milliseconds.
        </p>

        {/* Animated demonstration */}
        <div className="max-w-4xl mx-auto">
          <TradeExecutionAnimation />
        </div>

        {/* Caption */}
        <p className="text-center text-sm text-muted-foreground mt-6 max-w-2xl mx-auto">
          Animated demonstration showing signal flow from TradingView through TradeFlow to broker execution. 
          Actual execution time: &lt;50ms average.
        </p>
      </div>
    </section>
  );
}
