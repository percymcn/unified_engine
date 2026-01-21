import { Play } from "lucide-react";

export function DemoSection() {
  return (
    <section id="demo" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-4">
          See Tradeflow in Action
        </h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          Watch how a TradingView alert becomes an executed trade in seconds.
        </p>

        {/* Video/Demo placeholder */}
        <div className="max-w-4xl mx-auto">
          <div className="relative aspect-video rounded-xl overflow-hidden bg-gradient-to-br from-primary/20 to-primary/5 border">
            {/* Centered play button and placeholder text */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/90 text-primary-foreground mb-4 cursor-pointer hover:scale-105 transition-transform">
                  <Play className="w-6 h-6 ml-1" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Demo video coming soon
                </p>
              </div>
            </div>

            {/* CSS animated signal flow (simple version) */}
            <div className="absolute bottom-4 left-4 right-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="px-2 py-1 rounded bg-background/80 backdrop-blur-sm">
                  TradingView Alert
                </span>
                <span className="flex-1 h-0.5 bg-primary/30 mx-2 relative overflow-hidden">
                  <span className="absolute inset-y-0 left-0 w-4 bg-primary animate-[pulse_2s_ease-in-out_infinite]" />
                </span>
                <span className="px-2 py-1 rounded bg-background/80 backdrop-blur-sm">
                  Tradeflow
                </span>
                <span className="flex-1 h-0.5 bg-primary/30 mx-2 relative overflow-hidden">
                  <span
                    className="absolute inset-y-0 left-0 w-4 bg-primary animate-[pulse_2s_ease-in-out_infinite]"
                    style={{ animationDelay: "0.5s" }}
                  />
                </span>
                <span className="px-2 py-1 rounded bg-background/80 backdrop-blur-sm">
                  Broker
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
