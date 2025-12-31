import { motion } from 'motion/react';
import { useTheme } from '../contexts/ThemeContext';

export function AnimatedBackground() {
  const { theme } = useTheme();

  if (theme === 'ocean') {
    return <OceanBackground />;
  } else if (theme === 'cyberpunk') {
    return <CyberpunkBackground />;
  } else {
    return <MinimalBackground />;
  }
}

// Ocean Theme Background - Flowing waves and gradients
function OceanBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Base gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#001f29] via-[#002b36] to-[#001f29]" />
      
      {/* Animated gradient orbs */}
      <motion.div
        className="absolute top-0 left-0 w-[800px] h-[800px] rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, rgba(14,165,233,0.3) 0%, transparent 70%)',
        }}
        animate={{
          x: [0, 100, 0],
          y: [0, 50, 0],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      
      <motion.div
        className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full opacity-15"
        style={{
          background: 'radial-gradient(circle, rgba(0,255,194,0.2) 0%, transparent 70%)',
        }}
        animate={{
          x: [0, -50, 0],
          y: [0, -100, 0],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Floating particles */}
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-[#0EA5E9] rounded-full opacity-30"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, -30, 0],
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 3 + Math.random() * 2,
            repeat: Infinity,
            delay: Math.random() * 2,
          }}
        />
      ))}

      {/* Grid overlay */}
      <div 
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(14, 165, 233, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(14, 165, 233, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px',
        }}
      />
    </div>
  );
}

// Cyberpunk Theme Background - Neon grid and glitch effects
function CyberpunkBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Base dark gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0a0118] via-[#1a0933] to-[#0a0118]" />
      
      {/* Animated grid */}
      <motion.div 
        className="absolute inset-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255, 0, 255, 0.15) 2px, transparent 2px),
            linear-gradient(90deg, rgba(255, 0, 255, 0.15) 2px, transparent 2px),
            linear-gradient(rgba(0, 255, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 255, 0.05) 1px, transparent 1px)
          `,
          backgroundSize: '100px 100px, 100px 100px, 20px 20px, 20px 20px',
          backgroundPosition: '0 0, 0 0, 0 0, 0 0',
        }}
        animate={{
          backgroundPosition: ['0 0, 0 0, 0 0, 0 0', '100px 100px, 100px 100px, 20px 20px, 20px 20px'],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "linear"
        }}
      />

      {/* Neon glow orbs */}
      <motion.div
        className="absolute top-1/4 left-1/4 w-[500px] h-[500px] rounded-full"
        style={{
          background: 'radial-gradient(circle, rgba(255,0,255,0.4) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      <motion.div
        className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full"
        style={{
          background: 'radial-gradient(circle, rgba(0,255,255,0.3) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
        animate={{
          scale: [1, 1.3, 1],
          opacity: [0.2, 0.4, 0.2],
        }}
        transition={{
          duration: 5,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Scanlines effect */}
      <div 
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, #ff00ff 0px, transparent 2px, transparent 4px, #ff00ff 4px)',
          backgroundSize: '100% 4px',
        }}
      />

      {/* Random glitch lines */}
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute h-px bg-gradient-to-r from-transparent via-cyan-500 to-transparent"
          style={{
            left: 0,
            right: 0,
            top: `${20 + i * 20}%`,
          }}
          animate={{
            opacity: [0, 0.8, 0],
            x: [-1000, 1000],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            delay: i * 1.5,
            ease: "easeInOut"
          }}
        />
      ))}
    </div>
  );
}

// Minimal Theme Background - Clean gradients and subtle motion
function MinimalBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Base clean gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-white via-gray-50 to-blue-50" />
      
      {/* Subtle animated shapes */}
      <motion.div
        className="absolute -top-40 -right-40 w-80 h-80 rounded-full opacity-30"
        style={{
          background: 'radial-gradient(circle, rgba(14,165,233,0.15) 0%, transparent 70%)',
        }}
        animate={{
          scale: [1, 1.1, 1],
          rotate: [0, 90, 0],
        }}
        transition={{
          duration: 25,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      <motion.div
        className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, rgba(59,130,246,0.1) 0%, transparent 70%)',
        }}
        animate={{
          scale: [1, 1.2, 1],
          rotate: [0, -90, 0],
        }}
        transition={{
          duration: 30,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Floating chart-like lines */}
      <svg className="absolute inset-0 w-full h-full opacity-5">
        <motion.path
          d="M0,300 Q250,200 500,280 T1000,300 L1000,600 L0,600 Z"
          fill="url(#gradient1)"
          initial={{ d: "M0,300 Q250,200 500,280 T1000,300 L1000,600 L0,600 Z" }}
          animate={{ d: "M0,320 Q250,220 500,300 T1000,320 L1000,600 L0,600 Z" }}
          transition={{
            duration: 8,
            repeat: Infinity,
            repeatType: "reverse",
            ease: "easeInOut"
          }}
        />
        <defs>
          <linearGradient id="gradient1" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#0EA5E9" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#0EA5E9" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>

      {/* Minimal dots pattern */}
      <div 
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'radial-gradient(circle, #0EA5E9 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />
    </div>
  );
}
