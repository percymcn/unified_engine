"use client";

import { useRef, useState } from "react";
import { Play, Pause, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function DemoSection() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
        setHasStarted(true);
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleReplay = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play();
      setIsPlaying(true);
      setHasStarted(true);
    }
  };

  const handleVideoEnd = () => {
    setIsPlaying(false);
  };

  return (
    <section id="demo" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-4">
          See Tradeflow in Action
        </h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          Watch how a TradingView alert becomes an executed trade in milliseconds.
        </p>

        {/* Video demonstration */}
        <div className="max-w-4xl mx-auto">
          <div className="relative rounded-2xl overflow-hidden bg-black shadow-2xl border border-border/50">
            <video
              ref={videoRef}
              className="w-full aspect-video"
              onEnded={handleVideoEnd}
              playsInline
              preload="metadata"
            >
              <source src="/demo-video.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>

            {/* Play overlay (shown when not started or paused) */}
            {!isPlaying && (
              <div
                className="absolute inset-0 flex items-center justify-center bg-black/40 cursor-pointer transition-opacity hover:bg-black/30"
                onClick={handlePlayPause}
              >
                <div className="flex flex-col items-center gap-4">
                  <div className="w-20 h-20 rounded-full bg-primary/90 flex items-center justify-center shadow-lg hover:bg-primary transition-colors">
                    <Play className="w-8 h-8 text-primary-foreground ml-1" />
                  </div>
                  {!hasStarted && (
                    <span className="text-white font-medium text-lg">Click to play</span>
                  )}
                </div>
              </div>
            )}

            {/* Video controls */}
            <div className="absolute bottom-4 right-4 flex gap-2">
              {hasStarted && (
                <>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="bg-white/90 hover:bg-white text-black"
                    onClick={handlePlayPause}
                  >
                    {isPlaying ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="bg-white/90 hover:bg-white text-black"
                    onClick={handleReplay}
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Caption */}
        <p className="text-center text-sm text-muted-foreground mt-6 max-w-2xl mx-auto">
          Real demonstration showing signal flow from TradingView through TradeFlow to broker execution.
          Actual execution time: &lt;50ms average.
        </p>
      </div>
    </section>
  );
}
