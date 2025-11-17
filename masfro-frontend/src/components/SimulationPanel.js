import React, { useState, useEffect } from 'react';

export default function SimulationPanel({ isConnected, floodData }) {
  const [simulationMode, setSimulationMode] = useState('light');
  const [isExpanded, setIsExpanded] = useState(true);
  const [agentLogs, setAgentLogs] = useState([]);

  // Add logs when flood data or connection changes
  useEffect(() => {
    if (floodData) {
      addLog('flood', `Flood update received: ${JSON.stringify(floodData).substring(0, 50)}...`);
    }
  }, [floodData]);

  useEffect(() => {
    if (isConnected) {
      addLog('system', 'Connected to backend agents');
    } else {
      addLog('system', 'Disconnected from backend');
    }
  }, [isConnected]);

  const addLog = (source, message) => {
    const timestamp = new Date().toLocaleTimeString();
    setAgentLogs(prev => [
      { source, message, timestamp, id: Date.now() },
      ...prev.slice(0, 49) // Keep last 50 logs
    ]);
  };

  const getSourceIcon = (source) => {
    switch (source) {
      case 'flood': return '🌊';
      case 'scout': return '🔍';
      case 'system': return '⚙️';
      default: return '📝';
    }
  };

  const getSourceColor = (source) => {
    switch (source) {
      case 'flood': return '#248ea8';
      case 'scout': return '#10b981';
      case 'system': return '#8b5cf6';
      default: return '#6b7280';
    }
  };

  return (
    <div style={{
      position: 'fixed',
      right: '20px',
      top: '100px',
      width: isExpanded ? '380px' : '70px',
      maxHeight: isExpanded ? 'calc(100vh - 120px)' : 'auto',
      background: 'linear-gradient(160deg, rgba(15, 20, 25, 0.95) 0%, rgba(30, 35, 40, 0.95) 100%)',
      backdropFilter: 'blur(16px)',
      borderRadius: '16px',
      boxShadow: '0 12px 40px rgba(0, 0, 0, 0.5)',
      border: '1px solid rgba(36, 142, 168, 0.3)',
      zIndex: 1000,
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Collapsed State - Show icon button */}
      {!isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          style={{
            background: 'transparent',
            border: 'none',
            padding: '1.25rem',
            color: 'white',
            cursor: 'pointer',
            fontSize: '1.75rem',
            transition: 'all 0.2s',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            width: '100%'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(36, 142, 168, 0.15)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
          }}
          title="Open Simulation Panel"
        >
          <span>🎮</span>
          <span style={{
            fontSize: '1.25rem',
            letterSpacing: '1px',
            fontWeight: 700,
            color: '#248ea8'
          }}>←</span>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: isConnected ? '#10b981' : '#ef4444',
            animation: isConnected ? 'pulse 2s infinite' : 'none'
          }} />
        </button>
      )}

      {/* Expanded State - Full Header */}
      {isExpanded && (
        <div style={{
          padding: '1.25rem',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(36, 142, 168, 0.1)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem'
          }}>
            <span style={{ fontSize: '1.25rem' }}>🎮</span>
            <div>
              <h3 style={{
                margin: 0,
                fontSize: '1rem',
                fontWeight: 700,
                color: 'white',
                letterSpacing: '0.5px'
              }}>
                SIMULATION MODE
              </h3>
              <div style={{
                fontSize: '0.65rem',
                color: isConnected ? '#10b981' : '#ef4444',
                fontWeight: 600,
                marginTop: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}>
                <span style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: isConnected ? '#10b981' : '#ef4444',
                  animation: isConnected ? 'pulse 2s infinite' : 'none'
                }} />
                {isConnected ? 'LIVE' : 'OFFLINE'}
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsExpanded(false)}
            style={{
              background: 'rgba(36, 142, 168, 0.2)',
              border: '1px solid rgba(36, 142, 168, 0.4)',
              borderRadius: '8px',
              padding: '0.5rem',
              color: 'white',
              cursor: 'pointer',
              fontSize: '1rem',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minWidth: '32px',
              minHeight: '32px'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = 'rgba(36, 142, 168, 0.3)';
              e.target.style.transform = 'scale(1.05)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'rgba(36, 142, 168, 0.2)';
              e.target.style.transform = 'scale(1)';
            }}
            title="Collapse Panel"
          >
            →
          </button>
        </div>
      )}

      {/* Content - only visible when expanded */}
      {isExpanded && (
        <>
          {/* Scenario Selector */}
          <div style={{
            padding: '1.25rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <label style={{
              display: 'block',
              color: 'rgba(255, 255, 255, 0.7)',
              fontSize: '0.75rem',
              marginBottom: '0.5rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Flood Scenario
            </label>
            <select
              value={simulationMode}
              onChange={(e) => {
                setSimulationMode(e.target.value);
                addLog('system', `Scenario changed to: ${e.target.value.toUpperCase()} FLOOD`);
              }}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '10px',
                border: '1px solid rgba(36, 142, 168, 0.3)',
                background: 'rgba(36, 142, 168, 0.1)',
                color: 'white',
                fontSize: '0.875rem',
                cursor: 'pointer',
                outline: 'none',
                fontWeight: 600,
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.target.style.background = 'rgba(36, 142, 168, 0.15)';
                e.target.style.borderColor = 'rgba(36, 142, 168, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.target.style.background = 'rgba(36, 142, 168, 0.1)';
                e.target.style.borderColor = 'rgba(36, 142, 168, 0.3)';
              }}
            >
              <option value="light" style={{ background: '#1a1f25', color: 'white' }}>
                💧 Light Flood
              </option>
              <option value="medium" style={{ background: '#1a1f25', color: 'white' }}>
                🌊 Medium Flood
              </option>
              <option value="heavy" style={{ background: '#1a1f25', color: 'white' }}>
                ⚠️ Heavy Flood
              </option>
            </select>

            {/* Scenario info */}
            <div style={{
              marginTop: '0.75rem',
              padding: '0.75rem',
              background: 'rgba(36, 142, 168, 0.05)',
              borderRadius: '8px',
              border: '1px solid rgba(36, 142, 168, 0.15)'
            }}>
              <div style={{
                fontSize: '0.75rem',
                color: 'rgba(255, 255, 255, 0.6)',
                lineHeight: '1.5'
              }}>
                {simulationMode === 'light' && '< 0.5m depth • Low risk areas'}
                {simulationMode === 'medium' && '0.5m - 1.0m depth • Moderate risk'}
                {simulationMode === 'heavy' && '> 1.0m depth • High risk zones'}
              </div>
            </div>
          </div>

          {/* Agent Logs */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0
          }}>
            <div style={{
              padding: '1rem 1.25rem 0.75rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h4 style={{
                margin: 0,
                fontSize: '0.75rem',
                fontWeight: 700,
                color: 'rgba(255, 255, 255, 0.7)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Agent Logs
              </h4>
              <button
                onClick={() => setAgentLogs([])}
                style={{
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '6px',
                  padding: '0.35rem 0.6rem',
                  color: '#ef4444',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = 'rgba(239, 68, 68, 0.25)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = 'rgba(239, 68, 68, 0.15)';
                }}
              >
                Clear
              </button>
            </div>

            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '0 1.25rem 1.25rem',
              minHeight: 0
            }}>
              {agentLogs.length === 0 ? (
                <div style={{
                  textAlign: 'center',
                  padding: '2rem 1rem',
                  color: 'rgba(255, 255, 255, 0.4)',
                  fontSize: '0.875rem'
                }}>
                  <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📝</div>
                  No logs yet...
                </div>
              ) : (
                agentLogs.map((log) => (
                  <div
                    key={log.id}
                    style={{
                      marginBottom: '0.75rem',
                      padding: '0.75rem',
                      background: 'rgba(255, 255, 255, 0.03)',
                      borderRadius: '8px',
                      border: `1px solid ${getSourceColor(log.source)}33`,
                      borderLeft: `3px solid ${getSourceColor(log.source)}`,
                      transition: 'all 0.2s',
                      animation: 'slideIn 0.3s ease-out'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      marginBottom: '0.4rem'
                    }}>
                      <span style={{ fontSize: '0.9rem' }}>{getSourceIcon(log.source)}</span>
                      <span style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        color: getSourceColor(log.source),
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        {log.source}
                      </span>
                      <span style={{
                        marginLeft: 'auto',
                        fontSize: '0.65rem',
                        color: 'rgba(255, 255, 255, 0.4)',
                        fontFamily: 'monospace'
                      }}>
                        {log.timestamp}
                      </span>
                    </div>
                    <div style={{
                      fontSize: '0.75rem',
                      color: 'rgba(255, 255, 255, 0.8)',
                      lineHeight: '1.4',
                      wordBreak: 'break-word'
                    }}>
                      {log.message}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Scrollbar styling */
        div::-webkit-scrollbar {
          width: 6px;
        }

        div::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 3px;
        }

        div::-webkit-scrollbar-thumb {
          background: rgba(36, 142, 168, 0.4);
          border-radius: 3px;
        }

        div::-webkit-scrollbar-thumb:hover {
          background: rgba(36, 142, 168, 0.6);
        }
      `}</style>
    </div>
  );
}
