export function TradeLockerLogo({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Background Circle */}
      <circle cx="50" cy="50" r="45" fill="#0EA5E9" />
      
      {/* T Letter */}
      <path
        d="M 30 30 L 50 30 L 70 30 M 50 30 L 50 70"
        stroke="white"
        strokeWidth="8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      
      {/* L Letter - Overlapping */}
      <path
        d="M 42 40 L 42 70 L 62 70"
        stroke="white"
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.9"
      />
      
      {/* Lock Icon Detail - Small padlock at bottom right */}
      <g transform="translate(60, 60)">
        <rect
          x="0"
          y="4"
          width="10"
          height="8"
          rx="1"
          fill="white"
          opacity="0.8"
        />
        <path
          d="M 2 4 L 2 2 C 2 0.5 3 0 5 0 C 7 0 8 0.5 8 2 L 8 4"
          stroke="white"
          strokeWidth="1.5"
          fill="none"
          opacity="0.8"
        />
      </g>
    </svg>
  );
}

// Alternative compact version
export function TradeLockerLogoCompact({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Background */}
      <rect width="120" height="120" rx="24" fill="#0EA5E9" />
      
      {/* TL Monogram */}
      <g transform="translate(25, 30)">
        {/* T */}
        <path
          d="M 5 5 L 35 5 M 20 5 L 20 60"
          stroke="white"
          strokeWidth="10"
          strokeLinecap="round"
        />
        
        {/* L */}
        <path
          d="M 30 20 L 30 60 L 65 60"
          stroke="white"
          strokeWidth="9"
          strokeLinecap="round"
          opacity="0.95"
        />
      </g>
      
      {/* Subtle lock accent */}
      <circle
        cx="85"
        cy="85"
        r="8"
        fill="white"
        opacity="0.3"
      />
    </svg>
  );
}

// Text-based version
export function TradeLockerLogoText({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* TL in modern sans-serif style */}
      <text
        x="10"
        y="60"
        fontSize="60"
        fontWeight="700"
        fill="white"
        fontFamily="system-ui, -apple-system, sans-serif"
      >
        TL
      </text>
      
      {/* Underline accent */}
      <rect
        x="10"
        y="68"
        width="80"
        height="6"
        rx="3"
        fill="#00ffc2"
      />
    </svg>
  );
}

// Icon only version for small spaces
export function TradeLockerIcon({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Minimalist TL */}
      <rect width="48" height="48" rx="12" fill="#0EA5E9" />
      
      {/* T */}
      <line x1="12" y1="14" x2="24" y2="14" stroke="white" strokeWidth="3" strokeLinecap="round" />
      <line x1="18" y1="14" x2="18" y2="34" stroke="white" strokeWidth="3" strokeLinecap="round" />
      
      {/* L */}
      <line x1="26" y1="18" x2="26" y2="34" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="26" y1="34" x2="36" y2="34" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
