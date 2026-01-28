'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage, ConnectionStatus } from '@/types/websocket';

export interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  autoConnect?: boolean;
}

export interface UseWebSocketReturn {
  status: ConnectionStatus;
  connect: () => void;
  disconnect: () => void;
  send: (message: WebSocketMessage) => void;
  lastMessage: WebSocketMessage | null;
  reconnectAttempts: number;
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    autoConnect = true,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isUnmountingRef = useRef(false);

  // Clear all timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // Disconnect handler
  const disconnect = useCallback(() => {
    clearTimers();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, [clearTimers]);

  // Connect handler
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Clear any existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmountingRef.current) return;

        setStatus('connected');
        setReconnectAttempts(0);
        onConnect?.();

        // Start heartbeat - send ping to keep connection alive
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({
                type: 'ping',
              }));
            } catch {
              // Ignore send errors during heartbeat
            }
          }
        }, 30000); // Every 30 seconds
      };

      ws.onmessage = (event) => {
        if (isUnmountingRef.current) return;

        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
          onMessage?.(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (error) => {
        if (isUnmountingRef.current) return;

        // Only log first error to reduce spam
        if (reconnectAttempts === 0) {
          console.warn('WebSocket connection failed - will retry with backoff');
        }
        setStatus('error');
        onError?.(error);
      };

      ws.onclose = () => {
        if (isUnmountingRef.current) return;

        clearTimers();
        setStatus('disconnected');
        onDisconnect?.();

        // Attempt reconnect with exponential backoff if within limits
        setReconnectAttempts((currentAttempts) => {
          if (currentAttempts < maxReconnectAttempts) {
            // Exponential backoff: 3s, 6s, 12s, 24s, 48s... capped at 60s
            const backoffMs = Math.min(reconnectInterval * Math.pow(2, currentAttempts), 60000);
            reconnectTimeoutRef.current = setTimeout(() => {
              if (!isUnmountingRef.current) {
                connectRef.current();
              }
            }, backoffMs);
            return currentAttempts + 1;
          }
          return currentAttempts;
        });
      };
    } catch {
      // Only log first creation error
      if (reconnectAttempts === 0) {
        console.warn('Failed to create WebSocket connection');
      }
      setStatus('error');
    }
  // Note: reconnectAttempts is NOT in dependencies to prevent connect from being recreated on each attempt
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    url,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval,
    maxReconnectAttempts,
    clearTimers,
  ]);

  // Send message
  const send = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Cannot send message.');
    }
  }, []);

  // Store latest callbacks in refs to avoid dependency issues
  const connectRef = useRef(connect);
  const disconnectRef = useRef(disconnect);

  useEffect(() => {
    connectRef.current = connect;
    disconnectRef.current = disconnect;
  }, [connect, disconnect]);

  // Auto-connect on mount - only run once
  useEffect(() => {
    isUnmountingRef.current = false;

    if (autoConnect) {
      // Use a small delay to ensure component is fully mounted
      const timeoutId = setTimeout(() => {
        connectRef.current();
      }, 100);

      return () => {
        clearTimeout(timeoutId);
        isUnmountingRef.current = true;
        disconnectRef.current();
      };
    }

    return () => {
      isUnmountingRef.current = true;
      disconnectRef.current();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]); // Only depend on autoConnect, not the callbacks

  return {
    status,
    connect,
    disconnect,
    send,
    lastMessage,
    reconnectAttempts,
  };
}
