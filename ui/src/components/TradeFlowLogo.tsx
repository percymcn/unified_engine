interface TradeFlowLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

export function TradeFlowLogo({ size = 'md', showText = true, className = '' }: TradeFlowLogoProps) {
  const sizes = {
    sm: { icon: 32, text: 20 },
    md: { icon: 40, text: 24 },
    lg: { icon: 48, text: 28 }
  };

  const { icon, text } = sizes[size];

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Custom SVG Logo Icon */}
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Gradient Definitions */}
        <defs>
          <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0C1221" />
            <stop offset="50%" stopColor="#00C2A8" />
            <stop offset="100%" stopColor="#A5FFCE" />
          </linearGradient>
          <linearGradient id="arrowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00C2A8" />
            <stop offset="100%" stopColor="#A5FFCE" />
          </linearGradient>
        </defs>

        {/* Background circle with subtle glow */}
        <circle cx="50" cy="50" r="48" fill="#0C1221" opacity="0.3" />
        
        {/* Flowing wave lines (trading chart pattern) */}
        <path
          d="M 15 60 Q 25 45, 35 50 T 55 45 T 75 55 T 85 45"
          stroke="url(#flowGradient)"
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
        />
        
        <path
          d="M 15 70 Q 30 55, 40 60 T 60 55 T 80 65"
          stroke="#00C2A8"
          strokeWidth="1.5"
          fill="none"
          opacity="0.6"
          strokeLinecap="round"
        />

        {/* Data points */}
        <circle cx="35" cy="50" r="2" fill="#A5FFCE" />
        <circle cx="55" cy="45" r="2" fill="#A5FFCE" />
        <circle cx="75" cy="55" r="2" fill="#00C2A8" />

        {/* Upward arrow (growth/execution) */}
        <path
          d="M 50 25 L 50 65 M 50 25 L 42 33 M 50 25 L 58 33"
          stroke="url(#arrowGradient)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {/* Border circle */}
        <circle
          cx="50"
          cy="50"
          r="48"
          stroke="url(#flowGradient)"
          strokeWidth="1"
          fill="none"
          opacity="0.4"
        />
      </svg>

      {/* Logo Text */}
      {showText && (
        <div className="flex flex-col leading-tight">
          <div style={{ fontSize: `${text}px` }} className="font-semibold tracking-tight">
            <span className="text-white">Trade</span>
            <span className="text-[#00C2A8]">Flow</span>
          </div>
          <span 
            style={{ fontSize: `${text * 0.4}px` }} 
            className="text-[#A5FFCE] tracking-wide -mt-1"
          >
            by Fluxeo
          </span>
        </div>
      )}
    </div>
  );
}
