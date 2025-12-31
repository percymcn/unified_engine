"use client";

import { Toaster as Sonner, ToasterProps } from "sonner@2.0.3";
import { useTheme } from "../../contexts/ThemeContext";

const Toaster = ({ ...props }: ToasterProps) => {
  const { effectiveTheme } = useTheme();

  return (
    <Sonner
      theme={effectiveTheme as ToasterProps["theme"]}
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
