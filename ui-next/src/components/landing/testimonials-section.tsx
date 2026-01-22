"use client";

import { useEffect, useRef, useState } from "react";
import { Star } from "lucide-react";

/**
 * Testimonial data from real trader personas
 * Each testimonial addresses a specific pain point Tradeflow solves
 */
const testimonials = [
  {
    quote:
      "Tradeflow cut my execution time from minutes to milliseconds. I never miss a signal now.",
    name: "Mike T.",
    title: "Day Trader",
    initials: "MT",
    rating: 5,
  },
  {
    quote:
      "Managing 3 prop firm accounts used to be chaos. Now it's one webhook and done.",
    name: "Sarah K.",
    title: "Prop Firm Trader",
    initials: "SK",
    rating: 5,
  },
  {
    quote:
      "The risk management rules saved me from myself. No more overtrading.",
    name: "James L.",
    title: "Forex Trader",
    initials: "JL",
    rating: 5,
  },
  {
    quote:
      "Finally a tool that speaks every broker's language. Symbol mapping is genius.",
    name: "Alex R.",
    title: "Futures Trader",
    initials: "AR",
    rating: 5,
  },
];

/**
 * TestimonialsSection component displays customer reviews
 * Uses scroll-triggered fade-in animation for visual appeal
 */
export function TestimonialsSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        {/* Section header */}
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
          Trusted by Traders Worldwide
        </h2>
        <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
          Join thousands of traders who have automated their signal execution
        </p>

        {/* Testimonial cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {testimonials.map((testimonial, index) => (
            <div
              key={testimonial.name}
              className={`bg-card border rounded-xl p-6 shadow-sm hover:shadow-md transition-all duration-500 ${
                isVisible
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-4"
              }`}
              style={{ transitionDelay: `${index * 100}ms` }}
            >
              {/* Star rating */}
              <div className="flex gap-1 mb-4">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <Star
                    key={i}
                    className="w-4 h-4 fill-yellow-400 text-yellow-400"
                  />
                ))}
              </div>

              {/* Quote text */}
              <p className="text-foreground/90 italic mb-6 leading-relaxed">
                &ldquo;{testimonial.quote}&rdquo;
              </p>

              {/* Author info */}
              <div className="flex items-center gap-3">
                {/* Avatar with initials */}
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-sm font-semibold text-primary">
                    {testimonial.initials}
                  </span>
                </div>
                <div>
                  <p className="font-medium text-sm">{testimonial.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {testimonial.title}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
