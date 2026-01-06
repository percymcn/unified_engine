import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Theme = 'ocean' | 'cyberpunk' | 'minimal';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('tradeflow-theme');
    return (saved as Theme) || 'ocean';
  });

  useEffect(() => {
    localStorage.setItem('tradeflow-theme', theme);
    
    // Remove all theme classes
    document.documentElement.classList.remove('theme-ocean', 'theme-cyberpunk', 'theme-minimal');
    
    // Add current theme class
    document.documentElement.classList.add(`theme-${theme}`);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export const THEME_CONFIG = {
  ocean: {
    name: 'Ocean',
    description: 'Deep blue professional theme',
    icon: '🌊',
    preview: {
      bg: '#001f29',
      accent: '#0EA5E9',
      text: '#ffffff'
    }
  },
  cyberpunk: {
    name: 'Cyberpunk',
    description: 'Neon futuristic theme',
    icon: '⚡',
    preview: {
      bg: '#0a0118',
      accent: '#ff00ff',
      text: '#00ffff'
    }
  },
  minimal: {
    name: 'Minimal',
    description: 'Clean modern theme',
    icon: '✨',
    preview: {
      bg: '#ffffff',
      accent: '#0EA5E9',
      text: '#1a1a1a'
    }
  }
};
