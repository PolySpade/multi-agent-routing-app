import { useEffect, useState, useCallback, useRef } from 'react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function useWebSocket(url = `${WS_URL}/ws/route-updates`) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);

  const connect = useCallback(() => {
    // Don't attempt WebSocket connection if URL is not configured
    if (!url || url.includes('undefined') || url.includes('localhost')) {
      console.warn('WebSocket URL not configured for production. Running in offline mode.');
      setIsConnected(false);
      return;
    }

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected to', url);
        setIsConnected(true);

        // Send ping every 30 seconds to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);

          // Handle different message types
          switch (data.type) {
            case 'connection':
              console.log('Connected to MAS-FRO:', data.message);
              break;

            case 'system_status':
              setSystemStatus(data);
              break;

            case 'statistics_update':
              setStatistics(data.data);
              break;

            case 'risk_update':
              // Handle risk level updates
              console.log('Risk update received:', data);
              break;

            case 'pong':
              // Heartbeat response
              break;

            default:
              console.log('Unknown message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.warn('WebSocket connection error. Running in offline mode.');
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);

        // Clean up ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, 5000);
      };
    } catch (error) {
      console.warn('Unable to establish WebSocket connection:', error.message);
      setIsConnected(false);
    }
  }, [url]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const requestUpdate = useCallback(() => {
    return sendMessage({ type: 'request_update' });
  }, [sendMessage]);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    systemStatus,
    statistics,
    sendMessage,
    requestUpdate,
    reconnect: connect
  };
}
