'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Enhanced logging utility for AgentDataPanel
const logger = {
  info: (message, data = null) => {
    const timestamp = new Date().toISOString();
    console.log(`[AgentDataPanel][INFO][${timestamp}]`, message, data || '');
  },
  warn: (message, data = null) => {
    const timestamp = new Date().toISOString();
    console.warn(`[AgentDataPanel][WARN][${timestamp}]`, message, data || '');
  },
  error: (message, error = null) => {
    const timestamp = new Date().toISOString();
    console.error(`[AgentDataPanel][ERROR][${timestamp}]`, message, error || '');
  },
  debug: (message, data = null) => {
    const timestamp = new Date().toISOString();
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[AgentDataPanel][DEBUG][${timestamp}]`, message, data || '');
    }
  }
};

/**
 * AgentDataPanel Component
 *
 * Displays real-time data from all backend agents:
 * - ScoutAgent: Crowdsourced flood reports from social media
 * - FloodAgent: Official flood data from PAGASA/OpenWeatherMap
 * - EvacuationManagerAgent: Evacuation center information
 */
export default function AgentDataPanel() {
  const [activeTab, setActiveTab] = useState('scout'); // scout, flood
  const [scoutReports, setScoutReports] = useState([]);
  const [floodData, setFloodData] = useState(null);
  const [agentsStatus, setAgentsStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false); // NEW: Collapse state

  // NEW: Simulation state tracking
  const [simulationState, setSimulationState] = useState(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);

  // NEW: Fetch simulation status
  const fetchSimulationStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulation/status`);
      const data = await response.json();

      if (data.status === 'success') {
        const previousState = simulationState?.state;
        setSimulationState(data);

        // Log state changes
        if (previousState && previousState !== data.state) {
          logger.info(`Simulation state changed: ${previousState} → ${data.state}`);
        }

        // Enable auto-refresh when simulation is running
        const isRunning = data.state === 'running';
        if (autoRefreshEnabled !== isRunning) {
          setAutoRefreshEnabled(isRunning);
          logger.info(`Auto-refresh ${isRunning ? 'ENABLED' : 'DISABLED'}`);
        }
      }
    } catch (err) {
      logger.error('Failed to fetch simulation status', err);
    }
  };

  // Fetch agent status on mount
  useEffect(() => {
    logger.info('AgentDataPanel mounted - initializing data fetch');
    fetchAgentsStatus();
    fetchSimulationStatus(); // NEW: Fetch simulation status on mount

    const agentInterval = setInterval(fetchAgentsStatus, 30000); // Every 30s
    const simInterval = setInterval(fetchSimulationStatus, 3000); // NEW: Every 3s for simulation state

    return () => {
      logger.info('AgentDataPanel unmounting - clearing intervals');
      clearInterval(agentInterval);
      clearInterval(simInterval);
    };
  }, []);

  // Fetch data when tab changes
  useEffect(() => {
    logger.info(`Tab changed to: ${activeTab}`);
    if (activeTab === 'scout') fetchScoutReports();
    else if (activeTab === 'flood') fetchFloodData();
  }, [activeTab]);

  // NEW: Auto-refresh data during simulation
  useEffect(() => {
    if (!autoRefreshEnabled) {
      logger.debug('Auto-refresh disabled');
      return;
    }

    logger.info('Auto-refresh enabled - polling every 5 seconds during simulation');

    const refreshInterval = setInterval(() => {
      logger.debug('Auto-refresh: fetching latest data');
      if (activeTab === 'scout') {
        fetchScoutReports();
      } else if (activeTab === 'flood') {
        fetchFloodData();
      }
    }, 5000); // Refresh every 5 seconds during simulation

    return () => {
      logger.info('Auto-refresh stopped');
      clearInterval(refreshInterval);
    };
  }, [autoRefreshEnabled, activeTab]);

  const fetchAgentsStatus = async () => {
    const endpoint = `${API_BASE}/api/agents/status`;
    logger.debug('Fetching agent status', { endpoint });

    try {
      const response = await fetch(endpoint);
      logger.debug('Agent status response received', {
        status: response.status,
        ok: response.ok
      });

      const data = await response.json();
      logger.debug('Agent status data parsed', data);

      if (data.status === 'success') {
        setAgentsStatus(data.agents);
        setLastUpdate(new Date());
        logger.info('Agent status updated successfully', {
          agents: Object.keys(data.agents || {}),
          activeCount: Object.values(data.agents || {}).filter(a => a?.active).length
        });
      } else {
        logger.warn('Agent status fetch returned non-success', data);
      }
    } catch (err) {
      logger.error('Error fetching agent status', err);
    }
  };

  const fetchScoutReports = async () => {
    const endpoint = `${API_BASE}/api/agents/scout/reports?limit=50&hours=24`;
    logger.info('Fetching scout reports', { endpoint });

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(endpoint);
      logger.debug('Scout reports response received', {
        status: response.status,
        ok: response.ok,
        contentType: response.headers.get('content-type')
      });

      const data = await response.json();
      logger.debug('Scout reports data parsed', {
        status: data.status,
        reportCount: data.reports?.length || 0
      });

      if (data.status === 'success') {
        setScoutReports(data.reports);
        logger.info(`Scout reports loaded: ${data.reports.length} reports`, {
          reportCount: data.reports.length,
          locations: data.reports.map(r => r.location).filter(Boolean)
        });
      } else {
        const errorMsg = 'Failed to load scout reports';
        setError(errorMsg);
        logger.warn(errorMsg, data);
      }
    } catch (err) {
      let errorMsg = 'Unable to load scout reports';

      if (!navigator.onLine) {
        errorMsg = 'No internet connection detected';
      } else if (err.message.includes('fetch') || err.name === 'TypeError') {
        errorMsg = 'Backend server not responding. Ensure the backend is running on port 8000.';
      } else if (err.message.includes('CORS')) {
        errorMsg = 'CORS error: Backend may not allow requests from this origin';
      } else {
        errorMsg = `Error: ${err.message}`;
      }

      setError(errorMsg);
      logger.error('Failed to fetch scout reports', {
        error: err.message,
        stack: err.stack,
        endpoint
      });
    } finally {
      setLoading(false);
      logger.debug('Scout reports fetch complete');
    }
  };

  const fetchFloodData = async () => {
    const endpoint = `${API_BASE}/api/agents/flood/current-status`;
    logger.info('Fetching flood data', { endpoint });

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(endpoint);
      logger.debug('Flood data response received', {
        status: response.status,
        ok: response.ok,
        contentType: response.headers.get('content-type')
      });

      const data = await response.json();
      logger.debug('Flood data parsed', {
        status: data.status,
        dataPoints: data.data_points,
        source: data.data_source
      });

      if (data.status === 'success') {
        setFloodData(data);
        logger.info('Flood data loaded successfully', {
          dataPoints: data.data_points,
          source: data.data_source,
          lastUpdate: data.last_update
        });
      } else {
        const errorMsg = 'Failed to load flood data';
        setError(errorMsg);
        logger.warn(errorMsg, data);
      }
    } catch (err) {
      let errorMsg = 'Unable to load flood data';

      if (!navigator.onLine) {
        errorMsg = 'No internet connection detected';
      } else if (err.message.includes('fetch') || err.name === 'TypeError') {
        errorMsg = 'Backend server not responding. Ensure the backend is running on port 8000.';
      } else if (err.message.includes('CORS')) {
        errorMsg = 'CORS error: Backend may not allow requests from this origin';
      } else {
        errorMsg = `Error: ${err.message}`;
      }

      setError(errorMsg);
      logger.error('Failed to fetch flood data', {
        error: err.message,
        stack: err.stack,
        endpoint
      });
    } finally {
      setLoading(false);
      logger.debug('Flood data fetch complete');
    }
  };

  const getSeverityColor = (severity) => {
    if (severity >= 0.8) return 'bg-red-500';
    if (severity >= 0.5) return 'bg-orange-500';
    if (severity >= 0.3) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  const getSeverityLabel = (severity) => {
    if (severity >= 0.8) return 'Critical';
    if (severity >= 0.5) return 'Dangerous';
    if (severity >= 0.3) return 'Minor';
    return 'Low';
  };

  return (
    <div className={`agent-data-panel ${isCollapsed ? 'collapsed' : ''}`}>
      <style jsx>{`
        .agent-data-panel {
          position: relative;
          width: 100%;
          min-height: 300px;
          max-height: 500px;
          background: linear-gradient(160deg, rgba(15, 20, 25, 0.95) 0%, rgba(30, 35, 40, 0.95) 100%);
          backdrop-filter: blur(16px);
          border-radius: 16px;
          border: 1px solid rgba(36, 142, 168, 0.3);
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .agent-data-panel.collapsed {
          min-height: auto;
          max-height: 80px;
        }

        .panel-header {
          padding: 1.25rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(36, 142, 168, 0.1);
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
          user-select: none;
        }

        .panel-header:hover {
          background: rgba(36, 142, 168, 0.15);
        }

        .header-content {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex: 1;
        }

        .panel-icon {
          font-size: 1.25rem;
        }

        .header-title-section {
          flex: 1;
        }

        .panel-title {
          font-size: 1rem;
          font-weight: 700;
          color: white;
          margin: 0;
          letter-spacing: 0.5px;
        }

        .status-indicator {
          display: flex;
          gap: 0.75rem;
          font-size: 0.7rem;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 0.25rem;
        }

        .status-item {
          display: flex;
          align-items: center;
          gap: 0.25rem;
        }

        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
        }

        .status-active {
          background: #22c55e;
        }

        .status-inactive {
          background: #ef4444;
        }

        .status-warning {
          background: #f59e0b;
        }

        .status-pulse {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        .collapse-btn {
          background: rgba(36, 142, 168, 0.2);
          border: 1px solid rgba(36, 142, 168, 0.4);
          border-radius: 8px;
          padding: 0.5rem;
          color: white;
          cursor: pointer;
          font-size: 1rem;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 32px;
          min-height: 32px;
        }

        .collapse-btn:hover {
          background: rgba(36, 142, 168, 0.3);
          transform: scale(1.05);
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        .tab-bar {
          display: flex;
          gap: 0.5rem;
          padding: 0 1rem;
          background: rgba(0, 0, 0, 0.2);
        }

        .tab {
          flex: 1;
          padding: 0.75rem 1rem;
          border: none;
          background: transparent;
          color: rgba(255, 255, 255, 0.6);
          cursor: pointer;
          font-weight: 600;
          font-size: 0.85rem;
          transition: all 0.2s;
          border-bottom: 2px solid transparent;
        }

        .tab:hover {
          color: rgba(255, 255, 255, 0.9);
        }

        .tab.active {
          color: white;
          border-bottom-color: #248ea8;
        }

        .panel-content {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
        }

        .report-item {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 0.75rem;
          border-left: 3px solid;
        }

        .report-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 0.5rem;
        }

        .report-location {
          font-weight: 600;
          color: white;
          font-size: 0.95rem;
        }

        .severity-badge {
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.7rem;
          font-weight: 700;
          text-transform: uppercase;
          color: white;
        }

        .report-text {
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.8);
          line-height: 1.4;
          margin-bottom: 0.5rem;
        }

        .report-meta {
          display: flex;
          justify-content: space-between;
          font-size: 0.7rem;
          color: rgba(255, 255, 255, 0.5);
        }

        .flood-stat {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 0.75rem;
        }

        .stat-label {
          font-size: 0.7rem;
          text-transform: uppercase;
          color: rgba(255, 255, 255, 0.5);
          margin-bottom: 0.25rem;
        }

        .stat-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: white;
        }

        .center-item {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 0.75rem;
          border-left: 3px solid #248ea8;
        }

        .center-name {
          font-weight: 600;
          color: white;
          margin-bottom: 0.5rem;
        }

        .center-detail {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.7);
          margin-bottom: 0.25rem;
        }

        .loading, .error, .empty {
          text-align: center;
          padding: 2rem;
          color: rgba(255, 255, 255, 0.6);
        }

        .error {
          color: #ef4444;
        }

        .refresh-btn {
          background: rgba(36, 142, 168, 0.2);
          border: 1px solid rgba(36, 142, 168, 0.3);
          color: #7dd3fc;
          padding: 0.5rem 1rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.8rem;
          margin-top: 0.5rem;
        }

        .refresh-btn:hover {
          background: rgba(36, 142, 168, 0.3);
        }

        ::-webkit-scrollbar {
          width: 6px;
        }

        ::-webkit-scrollbar-track {
          background: transparent;
        }

        ::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 10px;
        }
      `}</style>

      {/* Header */}
      <div className="panel-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="header-content">
          <span className="panel-icon">📊</span>
          <div className="header-title-section">
            <h2 className="panel-title">AGENT DATA MONITOR</h2>
            <div className="status-indicator">
              {agentsStatus && (
                <>
                  <div className="status-item">
                    <div className={`status-dot ${agentsStatus.scout_agent?.active ? 'status-active' : 'status-inactive'}`}></div>
                    Scout
                  </div>
                  <div className="status-item">
                    <div className={`status-dot ${agentsStatus.flood_agent?.active ? 'status-active' : 'status-inactive'}`}></div>
                    Flood
                  </div>
                  {/* Simulation status indicator */}
                  {/* {simulationState && (
                    <div className="status-item">
                      <div className={`status-dot ${
                        simulationState.state === 'running' ? 'status-active status-pulse' :
                        simulationState.state === 'paused' ? 'status-warning' :
                        'status-inactive'
                      }`}></div>
                      Sim: {simulationState.state === 'running' ? `${simulationState.mode.toUpperCase()}` :
                            simulationState.state === 'paused' ? 'PAUSED' :
                            'OFF'}
                    </div>
                  )} */}
                </>
              )}
              {lastUpdate && (
                <div className="status-item">
                  Updated: {lastUpdate.toLocaleTimeString()}
                </div>
              )}
            </div>
          </div>
        </div>
        <button
          className="collapse-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsCollapsed(!isCollapsed);
          }}
          title={isCollapsed ? "Expand Panel" : "Collapse Panel"}
        >
          {isCollapsed ? '▲' : '▼'}
        </button>
      </div>

      {/* Tab Bar and Content - only visible when not collapsed */}
      {!isCollapsed && (
        <>
          {/* Tab Bar */}
          <div className="tab-bar">
            <button
              className={`tab ${activeTab === 'scout' ? 'active' : ''}`}
              onClick={() => setActiveTab('scout')}
            >
              Scout Reports
            </button>
            <button
              className={`tab ${activeTab === 'flood' ? 'active' : ''}`}
              onClick={() => setActiveTab('flood')}
            >
              Flood Data
            </button>
          </div>

          {/* Content */}
          <div className="panel-content">
        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error">{error}</div>}

        {/* Scout Reports Tab */}
        {!loading && !error && activeTab === 'scout' && (
          <>
            {scoutReports.length === 0 ? (
              <div className="empty">
                <p>No crowdsourced reports available.</p>
                <p style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                  Reports appear here when ScoutAgent processes social media data.
                </p>
                <button className="refresh-btn" onClick={fetchScoutReports}>
                  Refresh
                </button>
              </div>
            ) : (
              scoutReports.map((report, idx) => (
                <div
                  key={idx}
                  className="report-item"
                  style={{ borderLeftColor: getSeverityColor(report.severity || 0) }}
                >
                  <div className="report-header">
                    <div className="report-location">
                      {report.location || 'Unknown Location'}
                    </div>
                    <div className={`severity-badge ${getSeverityColor(report.severity || 0)}`}>
                      {getSeverityLabel(report.severity || 0)}
                    </div>
                  </div>
                  {report.text && (
                    <div className="report-text">
                      {report.text}
                    </div>
                  )}
                  <div className="report-meta">
                    <span>
                      {report.coordinates?.lat && report.coordinates?.lon ?
                        `${report.coordinates.lat.toFixed(4)}, ${report.coordinates.lon.toFixed(4)}`
                        : 'No coordinates'}
                    </span>
                    <span>
                      {report.timestamp ? new Date(report.timestamp).toLocaleTimeString() : 'Unknown time'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </>
        )}

        {/* Flood Data Tab */}
        {!loading && !error && activeTab === 'flood' && (
          <>
            {!floodData || floodData.data_points === 0 ? (
              <div className="empty">
                <p>No flood data available.</p>
                <button className="refresh-btn" onClick={fetchFloodData}>
                  Refresh
                </button>
              </div>
            ) : (
              <>
                <div className="flood-stat">
                  <div className="stat-label">Total Data Points</div>
                  <div className="stat-value">{floodData.data_points}</div>
                </div>
                <div className="flood-stat">
                  <div className="stat-label">Data Source</div>
                  <div className="stat-value" style={{ fontSize: '0.9rem' }}>
                    {floodData.data_source}
                  </div>
                </div>
                <div className="flood-stat">
                  <div className="stat-label">Last Update</div>
                  <div className="stat-value" style={{ fontSize: '0.9rem' }}>
                    {floodData.last_update ?
                      new Date(floodData.last_update).toLocaleString()
                      : 'Unknown'}
                  </div>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginTop: '1rem' }}>
                  {floodData.note}
                </div>
              </>
            )}
          </>
        )}
          </div>
        </>
      )}
    </div>
  );
}
