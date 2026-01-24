import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { ThemeProvider } from "@/providers/theme-provider";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Tradeflow - Auto-Execute TradingView Signals",
  description: "Route your TradingView alerts to TradeLocker, Tradovate, TopStep, and MetaTrader in <50ms. Trade while you sleep.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const isLocal = process.env.NEXT_PUBLIC_LOCAL_BANNER === "1";
  
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen bg-background text-foreground`}
      >
        {isLocal && (
          <div className="fixed top-0 left-0 right-0 z-50 bg-yellow-500 text-black text-center py-2 px-4 text-sm font-semibold border-b-2 border-yellow-600">
            🚧 LOCAL MODE - Development Environment 🚧
          </div>
        )}
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
