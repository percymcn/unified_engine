"use client";

import { useEffect, useRef, useState } from "react";

interface AnimatedChartProps {
  width?: number;
  height?: number;
  className?: string;
}

/**
 * AnimatedChart component displays a decorative trading chart animation
 * Uses SVG with CSS animations for smooth, GPU-accelerated performance
 * The chart line animates continuously to create a "live trading" atmosphere
 */
export function AnimatedChart({
  width = 400,
  height = 200,
  className = "",
}: AnimatedChartProps) {
  const [points, setPoints] = useState<number[]>([]);
  const animationRef = useRef<number | null>(null);
  const lastUpdateRef = useRef<number>(0);

  // Generate initial random points for the chart line
  useEffect(() => {
    const generatePoints = () => {
      const newPoints: number[] = [];
      let currentValue = height * 0.5; // Start in the middle

      for (let i = 0; i < 50; i++) {
        // Random walk with slight upward bias
        const change = (Math.random() - 0.45) * (height * 0.08);
        currentValue = Math.max(
          height * 0.15,
          Math.min(height * 0.85, currentValue + change)
        );
        newPoints.push(currentValue);
      }
      return newPoints;
    };

    setPoints(generatePoints());
  }, [height]);

  // Animate the chart by shifting points and adding new ones
  useEffect(() => {
    const animate = (timestamp: number) => {
      // Update every 100ms for smooth animation
      if (timestamp - lastUpdateRef.current > 100) {
        lastUpdateRef.current = timestamp;

        setPoints((prevPoints) => {
          if (prevPoints.length === 0) return prevPoints;

          const newPoints = [...prevPoints.slice(1)];
          const lastValue = prevPoints[prevPoints.length - 1];

          // Random walk with momentum
          const change = (Math.random() - 0.45) * (height * 0.06);
          const newValue = Math.max(
            height * 0.15,
            Math.min(height * 0.85, lastValue + change)
          );

          newPoints.push(newValue);
          return newPoints;
        });
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [height]);

  // Convert points array to SVG path
  const createPath = () => {
    if (points.length < 2) return "";

    const stepX = width / (points.length - 1);
    let path = `M 0 ${points[0]}`;

    for (let i = 1; i < points.length; i++) {
      const x = i * stepX;
      const y = points[i];
      // Use quadratic bezier for smooth curves
      const prevX = (i - 1) * stepX;
      const cpX = (prevX + x) / 2;
      path += ` Q ${cpX} ${points[i - 1]} ${x} ${y}`;
    }

    return path;
  };

  // Create gradient fill path (line to bottom corners)
  const createFillPath = () => {
    const linePath = createPath();
    if (!linePath) return "";

    return `${linePath} L ${width} ${height} L 0 ${height} Z`;
  };

  return (
    <div className={`relative overflow-hidden rounded-lg ${className}`}>
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="w-full h-full"
      >
        {/* Gradient definition */}
        <defs>
          <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgb(34, 197, 94)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="rgb(34, 197, 94)" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgb(34, 197, 94)" stopOpacity="0.5" />
            <stop offset="50%" stopColor="rgb(34, 197, 94)" stopOpacity="1" />
            <stop offset="100%" stopColor="rgb(34, 197, 94)" stopOpacity="1" />
          </linearGradient>
        </defs>

        {/* Gradient fill area */}
        <path
          d={createFillPath()}
          fill="url(#chartGradient)"
          className="transition-all duration-100 ease-out"
        />

        {/* Main chart line */}
        <path
          d={createPath()}
          fill="none"
          stroke="url(#lineGradient)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="transition-all duration-100 ease-out"
        />

        {/* Current value dot */}
        {points.length > 0 && (
          <circle
            cx={width}
            cy={points[points.length - 1]}
            r="4"
            fill="rgb(34, 197, 94)"
            className="animate-pulse"
          />
        )}
      </svg>

      {/* Grid overlay for trading chart look */}
      <div
        className="absolute inset-0 pointer-events-none opacity-10"
        style={{
          backgroundImage: `
            linear-gradient(to right, currentColor 1px, transparent 1px),
            linear-gradient(to bottom, currentColor 1px, transparent 1px)
          `,
          backgroundSize: `${width / 10}px ${height / 5}px`,
        }}
      />
    </div>
  );
}
