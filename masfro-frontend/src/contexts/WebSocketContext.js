'use client';

import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';

const WebSocketContext = createContext(null);

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function WebSocketProvider({ children }) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [simulationState, setSimulationState] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const mountedRef = useRef(true);

  const cleanup = useCallback(() => {
    console.log('🧹 WebSocketProvider: Cleaning up connection');

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      try {
        wsRef.current.close(1000, 'Component unmounting');
      } catch (e) {
        console.warn('Error closing WebSocket:', e);
      }
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    // Don't connect if already connected or connecting
    if (wsRef.current &&
        (wsRef.current.readyState === WebSocket.CONNECTING ||
         wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('⚠️ WebSocket already connected/connecting, skipping');
      return;
    }

    // Don't attempt if URL is not configured
    const url = `${WS_URL}/ws/route-updates`;
    if (!WS_URL || WS_URL.includes('undefined')) {
      console.warn('WebSocket URL not configured. Running in offline mode.');
      setIsConnected(false);
      return;
    }

    // Don't attempt if component is unmounted
    if (!mountedRef.current) {
      console.log('⚠️ Component unmounted, skipping connection');
      return;
    }

    try {
      console.log('🔌 WebSocketProvider: Connecting to', url);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;

        console.log('✅ WebSocketProvider: Connected successfully');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;

        // Setup heartbeat
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({ type: 'ping' }));
            } catch (e) {
              console.error('Error sending ping:', e);
            }
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;

        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);

          // Handle different message types
          switch (data.type) {
            case 'connection':
              console.log('📨 Connected to MAS-FRO:', data.message);
              break;

            case 'system_status':
              setSystemStatus(data);
              break;

            case 'statistics_update':
              setStatistics(data.data);
              break;

            case 'risk_update':
              console.log('📊 Risk update received:', data);
              break;

            case 'simulation_state':
              console.log('🎮 Simulation state update:', data.event, data.data);
              setSimulationState(data);
              break;

            case 'pong':
              // Heartbeat response
              break;

            default:
              console.log('📨 Unknown message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocketProvider: Connection error');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) {
          console.log('🔌 WebSocket closed (component unmounted)');
          return;
        }

        console.log('🔌 WebSocketProvider: Disconnected', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        });
        setIsConnected(false);

        // Cleanup intervals
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt to reconnect with exponential backoff
        if (mountedRef.current && event.code !== 1000) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(5000 * reconnectAttemptsRef.current, 30000);
          console.log(`🔄 Reconnecting in ${delay / 1000}s (attempt ${reconnectAttemptsRef.current})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              connect();
            }
          }, delay);
        }
      };
    } catch (error) {
      console.error('❌ WebSocketProvider: Failed to create connection:', error);
      setIsConnected(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    console.log('🔌 WebSocketProvider: Manual disconnect requested');
    mountedRef.current = false;
    cleanup();
  }, [cleanup]);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message));
        return true;
      } catch (e) {
        console.error('Error sending message:', e);
        return false;
      }
    }
    console.warn('Cannot send message: WebSocket not connected');
    return false;
  }, []);

  const requestUpdate = useCallback(() => {
    return sendMessage({ type: 'request_update' });
  }, [sendMessage]);

  // Connect on mount
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [connect, cleanup]);

  const value = {
    isConnected,
    lastMessage,
    systemStatus,
    statistics,
    simulationState,
    sendMessage,
    requestUpdate,
    reconnect: connect
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
}
