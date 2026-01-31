'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Maximize2,
  Settings,
  Eye,
  EyeOff,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChartConfig, ChartPosition } from '../types';
import {
  installTradingViewErrorFilter,
  uninstallTradingViewErrorFilter,
} from '@/lib/tradingview-error-filter';

interface TradingViewChartProps {
  symbol?: string;
  onSymbolChange?: (symbol: string) => void;
  onTimeframeChange?: (timeframe: string) => void;
  showPositions?: boolean;
  className?: string;
}

const TIMEFRAMES = [
  { value: '1', label: '1m' },
  { value: '5', label: '5m' },
  { value: '15', label: '15m' },
  { value: '30', label: '30m' },
  { value: '60', label: '1H' },
  { value: '240', label: '4H' },
  { value: 'D', label: '1D' },
  { value: 'W', label: '1W' },
];

const CHART_STYLES = [
  { value: '1', label: 'Candles' },
  { value: '8', label: 'Heikin Ashi' },
  { value: '9', label: 'Hollow Candles' },
  { value: '0', label: 'Bars' },
  { value: '3', label: 'Area' },
  { value: '2', label: 'Line' },
];

const POPULAR_SYMBOLS = [
  // Forex Majors
  'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
  // Commodities
  'XAUUSD', 'XAGUSD', 'USOIL',
  // Indices
  'US30', 'US100', 'US500', 'NAS100', 'MES1!', 'MNQ1!',
  // Crypto
  'BTCUSD', 'ETHUSD', 'SOLUSD',
];

export function TradingViewChart({
  symbol: initialSymbol = 'EURUSD',
  onSymbolChange,
  onTimeframeChange,
  showPositions: initialShowPositions = true,
  className,
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<any>(null);
  const [symbol, setSymbol] = useState(initialSymbol);
  const [timeframe, setTimeframe] = useState('60');
  const [chartStyle, setChartStyle] = useState('1'); // Default to candles
  const [isLoading, setIsLoading] = useState(true);
  const [showPositions, setShowPositions] = useState(initialShowPositions);
  const [positions, setPositions] = useState<ChartPosition[]>([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Install TradingView error filter to suppress known harmless CORS errors
  useEffect(() => {
    installTradingViewErrorFilter();
    return () => {
      uninstallTradingViewErrorFilter();
    };
  }, []);

  // Fetch open positions from TradeFlow
  const fetchPositions = useCallback(async () => {
    try {
      const response = await fetch('/api/dashboard/positions', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        // Filter positions matching current symbol
        const filteredPositions = (data.positions || []).filter(
          (p: any) => p.symbol?.toUpperCase().includes(symbol.toUpperCase())
        );
        setPositions(filteredPositions.map((p: any) => ({
          id: p.id,
          symbol: p.symbol,
          side: p.side?.toLowerCase() === 'sell' ? 'short' : 'long',
          entryPrice: p.open_price || p.entry_price || 0,
          currentPrice: p.current_price || 0,
          stopLoss: p.stop_loss,
          takeProfit: p.take_profit,
          size: p.volume || p.size || 0,
          unrealizedPnl: p.unrealized_pnl || 0,
          entryTime: p.open_time || p.entry_time,
        })));
      }
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    }
  }, [symbol]);

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 10000);
    return () => clearInterval(interval);
  }, [fetchPositions]);

  // Initialize TradingView widget
  useEffect(() => {
    if (!containerRef.current) return;

    setIsLoading(true);

    // Clean up existing widget
    if (widgetRef.current) {
      containerRef.current.innerHTML = '';
    }

    // Create TradingView widget script
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: symbol,
      interval: timeframe,
      timezone: 'Etc/UTC',
      theme: 'dark',
      style: chartStyle,
      locale: 'en',
      enable_publishing: false,
      allow_symbol_change: true,
      calendar: false,
      support_host: 'https://www.tradingview.com',
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: true,
      studies: [
        'RSI@tv-basicstudies',
        'MASimple@tv-basicstudies',
      ],
      show_popup_button: true,
      popup_width: '1000',
      popup_height: '650',
    });

    // Create container div for widget
    const widgetContainer = document.createElement('div');
    widgetContainer.className = 'tradingview-widget-container';
    widgetContainer.style.height = '100%';
    widgetContainer.style.width = '100%';

    const widgetInner = document.createElement('div');
    widgetInner.className = 'tradingview-widget-container__widget';
    widgetInner.style.height = 'calc(100% - 32px)';
    widgetInner.style.width = '100%';

    widgetContainer.appendChild(widgetInner);
    widgetContainer.appendChild(script);

    containerRef.current.appendChild(widgetContainer);
    widgetRef.current = widgetContainer;

    script.onload = () => {
      setIsLoading(false);
    };

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [symbol, timeframe, chartStyle]);

  const handleSymbolChange = (newSymbol: string) => {
    setSymbol(newSymbol.toUpperCase());
    onSymbolChange?.(newSymbol.toUpperCase());
  };

  const handleTimeframeChange = (newTimeframe: string) => {
    setTimeframe(newTimeframe);
    onTimeframeChange?.(newTimeframe);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.parentElement?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <Card className={cn('cyber-card flex flex-col w-full', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            Live Chart
          </CardTitle>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Symbol Input */}
            <div className="flex items-center gap-1">
              <Input
                value={symbol}
                onChange={(e) => handleSymbolChange(e.target.value)}
                className="w-28 h-8 text-sm"
                placeholder="Symbol"
              />
              <Select value={symbol} onValueChange={handleSymbolChange}>
                <SelectTrigger className="w-10 h-8 p-0">
                  <Settings className="h-4 w-4" />
                </SelectTrigger>
                <SelectContent>
                  {POPULAR_SYMBOLS.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Timeframe Select */}
            <Select value={timeframe} onValueChange={handleTimeframeChange}>
              <SelectTrigger className="w-20 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEFRAMES.map((tf) => (
                  <SelectItem key={tf.value} value={tf.value}>
                    {tf.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Chart Style Select */}
            <Select value={chartStyle} onValueChange={setChartStyle}>
              <SelectTrigger className="w-32 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHART_STYLES.map((style) => (
                  <SelectItem key={style.value} value={style.value}>
                    {style.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Toggle Positions */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => setShowPositions(!showPositions)}
                  >
                    {showPositions ? (
                      <Eye className="h-4 w-4" />
                    ) : (
                      <EyeOff className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {showPositions ? 'Hide Positions' : 'Show Positions'}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            {/* Refresh */}
            <Button
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={fetchPositions}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>

            {/* Fullscreen */}
            <Button
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={toggleFullscreen}
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 relative min-h-[500px]">
        {/* Chart Container */}
        <div
          ref={containerRef}
          className="w-full h-full min-h-[500px] relative"
        >
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}
        </div>

        {/* Positions Overlay */}
        {showPositions && positions.length > 0 && (
          <div className="absolute top-2 right-2 z-20 space-y-1">
            {positions.map((pos) => (
              <div
                key={pos.id}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium backdrop-blur-sm',
                  pos.side === 'long'
                    ? 'bg-emerald-500/20 border border-emerald-500/50 text-emerald-400'
                    : 'bg-red-500/20 border border-red-500/50 text-red-400'
                )}
              >
                <div className="flex items-center gap-2">
                  {pos.side === 'long' ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  <span>{pos.symbol}</span>
                  <span>{pos.size}</span>
                  <Badge
                    variant="outline"
                    className={cn(
                      'text-[10px] px-1',
                      pos.unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                    )}
                  >
                    {pos.unrealizedPnl >= 0 ? '+' : ''}
                    ${pos.unrealizedPnl.toFixed(2)}
                  </Badge>
                </div>
                <div className="flex gap-2 mt-0.5 text-muted-foreground">
                  <span>Entry: {pos.entryPrice.toFixed(5)}</span>
                  {pos.stopLoss && <span>SL: {pos.stopLoss}</span>}
                  {pos.takeProfit && <span>TP: {pos.takeProfit}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
