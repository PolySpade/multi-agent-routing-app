import { useEffect, useState, useCallback, useRef } from 'react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function useWebSocket(url = `${WS_URL}/ws/route-updates`) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [floodData, setFloodData] = useState(null);
  const [criticalAlerts, setCriticalAlerts] = useState([]);
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);

  const connect = useCallback(() => {
    // Don't attempt WebSocket connection if URL is not properly configured
    if (!url || url.includes('undefined')) {
      console.warn('WebSocket URL not configured. Running in offline mode.');
      setIsConnected(false);
      return;
    }

    try {
      console.log('🔌 Attempting WebSocket connection to:', url);
      console.log('🔌 URL breakdown:', {
        protocol: url.split(':')[0],
        host: url.split('/')[2],
        path: '/' + url.split('/').slice(3).join('/')
      });

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected successfully!');
        console.log('📡 Connected to:', url);
        console.log('🔗 Connection state: OPEN (ready for real-time updates)');
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
              console.log('✅ Connected to MAS-FRO:', data.message);
              break;

            case 'system_status':
              setSystemStatus(data);
              console.log('📊 System status updated:', data);
              break;

            case 'statistics_update':
              setStatistics(data.data);
              break;

            case 'flood_update':
              // Real-time flood data update from scheduler
              setFloodData(data.data);
              console.log('🌊 Flood data updated:', {
                timestamp: data.timestamp,
                source: data.source,
                dataPoints: Object.keys(data.data || {}).length
              });
              break;

            case 'critical_alert':
              // Critical water level alert
              setCriticalAlerts(prev => {
                const newAlert = {
                  ...data,
                  id: `${data.station}_${Date.now()}`,
                  receivedAt: new Date().toISOString()
                };
                console.warn('🚨 CRITICAL ALERT:', data.message);
                // Keep last 10 alerts
                return [newAlert, ...prev].slice(0, 10);
              });
              break;

            case 'scheduler_update':
              // Scheduler status update
              setSchedulerStatus(data.status);
              console.log('⏰ Scheduler update:', data.status);
              break;

            case 'risk_update':
              // Handle risk level updates
              console.log('⚠️ Risk update received:', data);
              break;

            case 'pong':
              // Heartbeat response
              break;

            default:
              console.log('❓ Unknown message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.warn('⚠️ WebSocket connection issue (will auto-retry)');
        console.debug('Connection state:', {
          readyState: ws.readyState,
          url: url,
          timestamp: new Date().toISOString()
        });
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('🔌 WebSocket disconnected - reconnecting in 5s');
        console.debug('Close details:', {
          code: event.code,
          reason: event.reason || 'No reason provided',
          wasClean: event.wasClean,
          timestamp: new Date().toISOString()
        });
        setIsConnected(false);

        // Clean up ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('🔄 Reconnecting to WebSocket...');
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
    // Prevent multiple connection attempts
    if (wsRef.current &&
        (wsRef.current.readyState === WebSocket.CONNECTING ||
         wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('⚠️ WebSocket already connected/connecting, skipping new connection');
      return;
    }

    connect();

    return () => {
      console.log('🧹 Cleaning up WebSocket connection');
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    systemStatus,
    statistics,
    floodData,
    criticalAlerts,
    schedulerStatus,
    sendMessage,
    requestUpdate,
    reconnect: connect,
    clearAlerts: () => setCriticalAlerts([])
  };
}
