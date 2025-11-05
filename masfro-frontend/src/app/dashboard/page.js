'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export default function Dashboard() {
  const [statistics, setStatistics] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsMessages, setWsMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch statistics from API
  const fetchStatistics = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/api/statistics`);
      if (response.ok) {
        const data = await response.json();
        setStatistics(data);
        setError(null);
      } else {
        throw new Error('Failed to fetch statistics');
      }
    } catch (err) {
      setError(err.message);
      console.error('Error fetching statistics:', err);
    }
  }, []);

  // Fetch health status
  const fetchHealthStatus = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/api/health`);
      if (response.ok) {
        const data = await response.json();
        setHealthStatus(data);
        setError(null);
      } else {
        throw new Error('Failed to fetch health status');
      }
    } catch (err) {
      setError(err.message);
      console.error('Error fetching health:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Setup WebSocket connection
  useEffect(() => {
    // Don't attempt WebSocket if URL not configured
    if (!WS_URL || WS_URL.includes('undefined') || WS_URL.includes('localhost')) {
      console.warn('WebSocket not configured. Dashboard will show cached data only.');
      return;
    }

    const ws = new WebSocket(`${WS_URL}/ws/route-updates`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);

      ws.pingInterval = pingInterval;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setWsMessages((prev) => [data, ...prev].slice(0, 50)); // Keep last 50 messages

        // Update statistics if received
        if (data.type === 'statistics_update') {
          setStatistics((prev) => ({
            ...prev,
            route_statistics: data.data
          }));
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.warn('WebSocket connection unavailable. Showing API data only.');
      setWsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
      if (ws.pingInterval) {
        clearInterval(ws.pingInterval);
      }
    };

    return () => {
      if (ws.pingInterval) {
        clearInterval(ws.pingInterval);
      }
      ws.close();
    };
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchStatistics();
    fetchHealthStatus();

    // Refresh data every 30 seconds
    const interval = setInterval(() => {
      fetchStatistics();
      fetchHealthStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchStatistics, fetchHealthStatus]);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f172a, #312e81)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '50px',
            height: '50px',
            border: '5px solid rgba(255,255,255,0.3)',
            borderTop: '5px solid white',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 20px'
          }} />
          <p>Loading dashboard...</p>
        </div>
        <style jsx global>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f172a, #312e81)',
      padding: '2rem',
      color: 'white',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <style jsx global>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>

      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem'
        }}>
          <div>
            <h1 style={{
              margin: 0,
              fontSize: '2.5rem',
              fontWeight: 700,
              background: 'linear-gradient(45deg, #ffffff, #e2e8f0)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              MAS-FRO Dashboard
            </h1>
            <p style={{ margin: '0.5rem 0 0', opacity: 0.8 }}>
              System Monitoring & Statistics
            </p>
          </div>
          <Link href="/" style={{
            padding: '0.75rem 1.5rem',
            background: 'rgba(102, 126, 234, 0.3)',
            border: '1px solid rgba(102, 126, 234, 0.5)',
            borderRadius: '10px',
            color: 'white',
            textDecoration: 'none',
            fontSize: '0.95rem',
            fontWeight: 600,
            transition: 'all 0.3s ease'
          }}>
            ← Back to Map
          </Link>
        </div>

        {error && (
          <div style={{
            padding: '1rem',
            background: 'rgba(244, 63, 94, 0.2)',
            border: '1px solid rgba(244, 63, 94, 0.5)',
            borderRadius: '12px',
            marginBottom: '2rem'
          }}>
            Error: {error}
          </div>
        )}

        {/* System Status Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          {/* Health Status */}
          <div style={{
            background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)',
            borderRadius: '16px',
            padding: '1.5rem',
            border: '1px solid rgba(226, 232, 240, 0.15)'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              marginBottom: '1rem'
            }}>
              <div style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                background: healthStatus?.status === 'healthy' ? '#22c55e' : '#f43f5e',
                animation: 'pulse 2s infinite'
              }} />
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
                System Health
              </h3>
            </div>
            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', opacity: 0.8 }}>
              Status: <strong>{healthStatus?.status || 'Unknown'}</strong>
            </p>
            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', opacity: 0.8 }}>
              Graph: <strong>{healthStatus?.graph_status || 'Unknown'}</strong>
            </p>
          </div>

          {/* WebSocket Status */}
          <div style={{
            background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)',
            borderRadius: '16px',
            padding: '1.5rem',
            border: '1px solid rgba(226, 232, 240, 0.15)'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              marginBottom: '1rem'
            }}>
              <div style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                background: wsConnected ? '#22c55e' : '#f43f5e',
                animation: 'pulse 2s infinite'
              }} />
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
                Real-time Connection
              </h3>
            </div>
            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', opacity: 0.8 }}>
              Status: <strong>{wsConnected ? 'Connected' : 'Disconnected'}</strong>
            </p>
            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', opacity: 0.8 }}>
              Messages: <strong>{wsMessages.length}</strong>
            </p>
          </div>

          {/* Graph Statistics */}
          <div style={{
            background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)',
            borderRadius: '16px',
            padding: '1.5rem',
            border: '1px solid rgba(226, 232, 240, 0.15)'
          }}>
            <h3 style={{
              margin: '0 0 1rem',
              fontSize: '1.1rem',
              fontWeight: 600
            }}>
              Road Network
            </h3>
            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', opacity: 0.8 }}>
              Nodes: <strong>{statistics?.graph_statistics?.total_nodes || 0}</strong>
            </p>
            <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', opacity: 0.8 }}>
              Edges: <strong>{statistics?.graph_statistics?.total_edges || 0}</strong>
            </p>
          </div>
        </div>

        {/* Agent Status */}
        <div style={{
          background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)',
          borderRadius: '16px',
          padding: '1.5rem',
          border: '1px solid rgba(226, 232, 240, 0.15)',
          marginBottom: '2rem'
        }}>
          <h3 style={{ margin: '0 0 1rem', fontSize: '1.25rem', fontWeight: 600 }}>
            Agent Status
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem'
          }}>
            {healthStatus?.agents && Object.entries(healthStatus.agents).map(([name, status]) => (
              <div key={name} style={{
                padding: '1rem',
                background: 'rgba(15, 23, 42, 0.3)',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <div style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: status === 'active' ? '#22c55e' : '#94a3b8'
                  }} />
                  <p style={{
                    margin: 0,
                    fontSize: '0.85rem',
                    textTransform: 'capitalize',
                    opacity: 0.9
                  }}>
                    {name.replace(/_/g, ' ')}
                  </p>
                </div>
                <p style={{
                  margin: '0.5rem 0 0',
                  fontSize: '0.8rem',
                  opacity: 0.7
                }}>
                  {status}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Route Statistics */}
        <div style={{
          background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)',
          borderRadius: '16px',
          padding: '1.5rem',
          border: '1px solid rgba(226, 232, 240, 0.15)',
          marginBottom: '2rem'
        }}>
          <h3 style={{ margin: '0 0 1rem', fontSize: '1.25rem', fontWeight: 600 }}>
            Route Statistics
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem'
          }}>
            <div style={{
              padding: '1rem',
              background: 'rgba(15, 23, 42, 0.3)',
              borderRadius: '12px'
            }}>
              <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', opacity: 0.7, textTransform: 'uppercase' }}>
                Total Routes
              </p>
              <p style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700 }}>
                {statistics?.route_statistics?.total_routes || 0}
              </p>
            </div>
            <div style={{
              padding: '1rem',
              background: 'rgba(15, 23, 42, 0.3)',
              borderRadius: '12px'
            }}>
              <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', opacity: 0.7, textTransform: 'uppercase' }}>
                Total Feedback
              </p>
              <p style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700 }}>
                {statistics?.route_statistics?.total_feedback || 0}
              </p>
            </div>
            <div style={{
              padding: '1rem',
              background: 'rgba(15, 23, 42, 0.3)',
              borderRadius: '12px'
            }}>
              <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', opacity: 0.7, textTransform: 'uppercase' }}>
                Avg Risk Level
              </p>
              <p style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700 }}>
                {statistics?.route_statistics?.average_risk_level?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>

        {/* WebSocket Messages */}
        <div style={{
          background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)',
          borderRadius: '16px',
          padding: '1.5rem',
          border: '1px solid rgba(226, 232, 240, 0.15)'
        }}>
          <h3 style={{ margin: '0 0 1rem', fontSize: '1.25rem', fontWeight: 600 }}>
            Real-time Messages {wsMessages.length > 0 && `(${wsMessages.length})`}
          </h3>
          <div style={{
            maxHeight: '300px',
            overflowY: 'auto',
            padding: '0.5rem'
          }}>
            {wsMessages.length === 0 ? (
              <p style={{ margin: 0, opacity: 0.6, textAlign: 'center', padding: '2rem' }}>
                No messages received yet...
              </p>
            ) : (
              wsMessages.map((msg, index) => (
                <div key={index} style={{
                  padding: '0.75rem',
                  background: 'rgba(15, 23, 42, 0.3)',
                  borderRadius: '8px',
                  marginBottom: '0.5rem',
                  border: '1px solid rgba(255,255,255,0.1)'
                }}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: '0.25rem'
                  }}>
                    <span style={{
                      fontSize: '0.85rem',
                      fontWeight: 600,
                      color: '#76a9ff'
                    }}>
                      {msg.type}
                    </span>
                    <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  <pre style={{
                    margin: 0,
                    fontSize: '0.75rem',
                    opacity: 0.8,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    {JSON.stringify(msg, null, 2)}
                  </pre>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
