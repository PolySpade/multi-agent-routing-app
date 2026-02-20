'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

/**
 * AgentDataPanel Component
 *
 * Displays real-time data from all backend agents:
 * - Scout: Crowdsourced flood reports from social media
 * - Flood: Official flood data (river levels, weather, alerts)
 * - Hazard: Risk distribution, hazard cache, impassable edges
 * - System: Lifecycle manager, agent ticks, graph stats
 */
export default function AgentDataPanel() {
  const [activeTab, setActiveTab] = useState('scout');
  const [scoutReports, setScoutReports] = useState([]);
  const [floodData, setFloodData] = useState(null);
  const [hazardData, setHazardData] = useState(null);
  const [riskScores, setRiskScores] = useState(null);
  const [systemData, setSystemData] = useState(null);
  const [criticalAlerts, setCriticalAlerts] = useState([]);
  const [agentsStatus, setAgentsStatus] = useState(null);
  const [orchestratorData, setOrchestratorData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [graphResetting, setGraphResetting] = useState(false);

  const activeTabRef = useRef(activeTab);
  activeTabRef.current = activeTab;

  // --- Data fetchers ---

  const fetchAgentsStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agents/status`);
      const data = await res.json();
      if (data.status === 'success') {
        setAgentsStatus(data.agents);
        setLastUpdate(new Date());
      }
    } catch (err) {
      console.error('[AgentDataPanel] Failed to fetch agent status', err);
    }
  }, []);

  const fetchScoutReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/agents/scout/reports?page_size=50&hours=24`);
      const data = await res.json();
      if (data.status === 'success') {
        setScoutReports(data.reports || []);
      } else {
        setError('Failed to load scout reports');
      }
    } catch (err) {
      setError(err.message?.includes('fetch') ? 'Backend not responding' : err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFloodData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [floodRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE}/api/agents/flood/current-status`),
        fetch(`${API_BASE}/api/flood-data/critical-alerts?hours=24`),
      ]);
      const floodJson = await floodRes.json();
      const alertsJson = await alertsRes.json();
      if (floodJson.status === 'success') setFloodData(floodJson);
      else setError('Failed to load flood data');
      setCriticalAlerts(alertsJson.critical_alerts || []);
    } catch (err) {
      setError(err.message?.includes('fetch') ? 'Backend not responding' : err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHazardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cacheRes, riskRes] = await Promise.all([
        fetch(`${API_BASE}/api/debug/hazard-cache`),
        fetch(`${API_BASE}/api/debug/graph-risk-scores`),
      ]);
      const cacheJson = await cacheRes.json();
      const riskJson = await riskRes.json();
      if (cacheJson.status === 'success') setHazardData(cacheJson);
      if (riskJson.status === 'success') setRiskScores(riskJson);
    } catch (err) {
      setError(err.message?.includes('fetch') ? 'Backend not responding' : err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSystemData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [lifecycleRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/lifecycle/status`),
        fetch(`${API_BASE}/api/statistics`),
      ]);
      const lifecycleJson = await lifecycleRes.json();
      const statsJson = await statsRes.json();
      setSystemData({ lifecycle: lifecycleJson, statistics: statsJson });
    } catch (err) {
      setError(err.message?.includes('fetch') ? 'Backend not responding' : err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchOrchestratorData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [missionsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/api/orchestrator/missions`),
        fetch(`${API_BASE}/api/lifecycle/status`),
      ]);
      const missionsJson = await missionsRes.json();
      const statusJson = await statusRes.json();
      const orchStats = statusJson?.statistics?.agent_step_counts?.orchestrator_main;
      const orchErrors = statusJson?.statistics?.agent_step_errors?.orchestrator_main;
      setOrchestratorData({
        active: missionsJson.active || [],
        completed: missionsJson.completed || [],
        ticks: orchStats || 0,
        errors: orchErrors || 0,
      });
    } catch (err) {
      setError(err.message?.includes('fetch') ? 'Backend not responding' : err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleGraphReset = useCallback(async () => {
    setGraphResetting(true);
    try {
      const res = await fetch(`${API_BASE}/api/graph/reset`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        alert(`Graph reset: ${data.message}`);
        // Refresh system tab data
        fetchSystemData();
      } else {
        alert(`Graph reset failed: ${data.message}`);
      }
    } catch (err) {
      alert(`Graph reset error: ${err.message}`);
    } finally {
      setGraphResetting(false);
    }
  }, [fetchSystemData]);

  const fetchTabData = useCallback(() => {
    const tab = activeTabRef.current;
    if (tab === 'scout') fetchScoutReports();
    else if (tab === 'flood') fetchFloodData();
    else if (tab === 'hazard') fetchHazardData();
    else if (tab === 'system') fetchSystemData();
    else if (tab === 'orchestrator') fetchOrchestratorData();
  }, [fetchScoutReports, fetchFloodData, fetchHazardData, fetchSystemData, fetchOrchestratorData]);

  // --- Effects ---

  // On mount: fetch status + initial tab data
  useEffect(() => {
    fetchAgentsStatus();
    fetchTabData();

    const agentInterval = setInterval(fetchAgentsStatus, 30000);

    return () => {
      clearInterval(agentInterval);
    };
  }, [fetchAgentsStatus, fetchTabData]);

  // Tab change
  useEffect(() => {
    fetchTabData();
  }, [activeTab, fetchTabData]);

  // Auto-refresh during simulation
  useEffect(() => {
    if (!autoRefreshEnabled) return;
    const interval = setInterval(fetchTabData, 5000);
    return () => clearInterval(interval);
  }, [autoRefreshEnabled, fetchTabData]);

  // --- Helpers ---

  const getSeverityColor = (severity) => {
    if (severity >= 0.8) return '#ef4444';
    if (severity >= 0.5) return '#f97316';
    if (severity >= 0.3) return '#eab308';
    return '#3b82f6';
  };

  const getSeverityLabel = (severity) => {
    if (severity >= 0.8) return 'Critical';
    if (severity >= 0.5) return 'Dangerous';
    if (severity >= 0.3) return 'Minor';
    return 'Low';
  };

  const getRiskBarColor = (risk) => {
    if (risk >= 0.7) return '#ef4444';
    if (risk >= 0.4) return '#f97316';
    if (risk >= 0.1) return '#eab308';
    return '#22c55e';
  };

  const formatUptime = (seconds) => {
    if (!seconds) return '--';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  // Agent status entries for header
  const agentDots = [
    { key: 'scout_agent', label: 'Scout' },
    { key: 'flood_agent', label: 'Flood' },
    { key: 'hazard_agent', label: 'Hazard' },
    { key: 'routing_agent', label: 'Route' },
    { key: 'evacuation_manager', label: 'Evac' },
    { key: 'orchestrator_main', label: 'Orch' },
  ];

  return (
    <div className={`agent-data-panel ${isCollapsed ? 'collapsed' : ''}`}>
      <style jsx>{`
        .agent-data-panel {
          position: relative;
          width: 100%;
          min-height: 300px;
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
          padding: 1rem 1.25rem;
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
          min-width: 0;
        }
        .panel-icon { font-size: 1.25rem; }
        .header-title-section { flex: 1; min-width: 0; }
        .panel-title {
          font-size: 1rem;
          font-weight: 700;
          color: white;
          margin: 0;
          letter-spacing: 0.5px;
        }
        .status-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          font-size: 0.7rem;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 0.25rem;
        }
        .status-item {
          display: flex;
          align-items: center;
          gap: 0.2rem;
        }
        .dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .dot-active { background: #22c55e; }
        .dot-inactive { background: #ef4444; }
        .dot-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
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
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .tab-bar {
          display: flex;
          gap: 0;
          background: rgba(0, 0, 0, 0.2);
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .tab {
          flex: 1;
          padding: 0.6rem 0.5rem;
          border: none;
          background: transparent;
          color: rgba(255, 255, 255, 0.5);
          cursor: pointer;
          font-weight: 600;
          font-size: 0.75rem;
          transition: all 0.2s;
          border-bottom: 2px solid transparent;
          text-align: center;
          white-space: nowrap;
        }
        .tab:hover { color: rgba(255, 255, 255, 0.9); }
        .tab.active {
          color: white;
          border-bottom-color: #248ea8;
          background: rgba(36, 142, 168, 0.08);
        }
        .tab .tab-badge {
          display: inline-block;
          background: #ef4444;
          color: white;
          font-size: 0.55rem;
          padding: 0.1rem 0.35rem;
          border-radius: 8px;
          margin-left: 0.3rem;
          font-weight: 700;
          vertical-align: middle;
        }
        .panel-content {
          flex: 1;
          overflow-y: auto;
          padding: 0.75rem;
          min-height: 0;
        }
        .report-item {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          padding: 0.75rem;
          margin-bottom: 0.5rem;
          border-left: 3px solid;
        }
        .report-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 0.35rem;
        }
        .report-location {
          font-weight: 600;
          color: white;
          font-size: 0.85rem;
        }
        .severity-badge {
          padding: 0.15rem 0.4rem;
          border-radius: 4px;
          font-size: 0.6rem;
          font-weight: 700;
          text-transform: uppercase;
          color: white;
        }
        .report-text {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.75);
          line-height: 1.4;
          margin-bottom: 0.35rem;
        }
        .report-meta {
          display: flex;
          justify-content: space-between;
          font-size: 0.65rem;
          color: rgba(255, 255, 255, 0.45);
        }
        .stat-card {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          padding: 0.75rem;
          margin-bottom: 0.5rem;
        }
        .stat-label {
          font-size: 0.65rem;
          text-transform: uppercase;
          color: rgba(255, 255, 255, 0.45);
          margin-bottom: 0.15rem;
          letter-spacing: 0.5px;
        }
        .stat-value {
          font-size: 1.1rem;
          font-weight: 700;
          color: white;
        }
        .stat-value.small { font-size: 0.85rem; }
        .stat-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.5rem;
        }
        .risk-bar-container {
          width: 100%;
          height: 8px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
          overflow: hidden;
          margin-top: 0.25rem;
        }
        .risk-bar {
          height: 100%;
          border-radius: 4px;
          transition: width 0.5s ease;
        }
        .hazard-entry {
          background: rgba(255, 255, 255, 0.04);
          border-radius: 6px;
          padding: 0.5rem 0.75rem;
          margin-bottom: 0.35rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .hazard-location {
          font-size: 0.8rem;
          font-weight: 600;
          color: white;
        }
        .hazard-values {
          display: flex;
          gap: 0.75rem;
          font-size: 0.7rem;
          color: rgba(255, 255, 255, 0.6);
        }
        .agent-tick-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.35rem 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.04);
          font-size: 0.75rem;
        }
        .agent-tick-row:last-child { border-bottom: none; }
        .agent-name {
          color: rgba(255, 255, 255, 0.8);
          font-weight: 600;
        }
        .tick-count {
          color: rgba(255, 255, 255, 0.5);
          font-variant-numeric: tabular-nums;
        }
        .error-badge {
          color: #ef4444;
          font-weight: 700;
          margin-left: 0.5rem;
        }
        .section-title {
          font-size: 0.7rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: rgba(36, 142, 168, 0.8);
          margin: 0.75rem 0 0.35rem;
          font-weight: 700;
        }
        .section-title:first-child { margin-top: 0; }
        .alert-item {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          padding: 0.65rem;
          margin-bottom: 0.5rem;
        }
        .alert-station {
          font-weight: 700;
          color: #fca5a5;
          font-size: 0.85rem;
          margin-bottom: 0.2rem;
        }
        .alert-detail {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
        }
        .empty-state {
          text-align: center;
          padding: 1.5rem;
          color: rgba(255, 255, 255, 0.4);
          font-size: 0.8rem;
        }
        .refresh-btn {
          background: rgba(36, 142, 168, 0.2);
          border: 1px solid rgba(36, 142, 168, 0.3);
          color: #7dd3fc;
          padding: 0.4rem 0.8rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.75rem;
          margin-top: 0.5rem;
          transition: background 0.2s;
        }
        .refresh-btn:hover {
          background: rgba(36, 142, 168, 0.3);
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.15);
          border-radius: 10px;
        }

        @media (max-width: 767px) {
          .agent-data-panel {
            min-height: 0;
            max-height: calc(70vh - 56px);
            border-radius: 0;
          }
        }
      `}</style>

      {/* Header */}
      <div className="panel-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="header-content">
          <span className="panel-icon">📊</span>
          <div className="header-title-section">
            <h2 className="panel-title">AGENT DATA MONITOR</h2>
            <div className="status-row">
              {agentsStatus && agentDots.map(({ key, label }) => (
                <div className="status-item" key={key}>
                  <div className={`dot ${agentsStatus[key]?.active ? 'dot-active' : 'dot-inactive'}`} />
                  {label}
                </div>
              ))}
              {lastUpdate && (
                <div className="status-item" style={{ marginLeft: 'auto' }}>
                  {lastUpdate.toLocaleTimeString()}
                </div>
              )}
            </div>
          </div>
        </div>
        <button
          className="collapse-btn"
          onClick={(e) => { e.stopPropagation(); setIsCollapsed(!isCollapsed); }}
          title={isCollapsed ? 'Expand' : 'Collapse'}
        >
          {isCollapsed ? '▲' : '▼'}
        </button>
      </div>

      {!isCollapsed && (
        <>
          {/* Tab Bar */}
          <div className="tab-bar">
            <button className={`tab ${activeTab === 'scout' ? 'active' : ''}`} onClick={() => setActiveTab('scout')}>
              Scout
            </button>
            <button className={`tab ${activeTab === 'flood' ? 'active' : ''}`} onClick={() => setActiveTab('flood')}>
              Flood
              {criticalAlerts.length > 0 && <span className="tab-badge">{criticalAlerts.length}</span>}
            </button>
            <button className={`tab ${activeTab === 'hazard' ? 'active' : ''}`} onClick={() => setActiveTab('hazard')}>
              Hazard
            </button>
            <button className={`tab ${activeTab === 'orchestrator' ? 'active' : ''}`} onClick={() => setActiveTab('orchestrator')}>
              Orch
            </button>
            <button className={`tab ${activeTab === 'system' ? 'active' : ''}`} onClick={() => setActiveTab('system')}>
              System
            </button>
          </div>

          {/* Content */}
          <div className="panel-content">
            {loading && <div className="empty-state">Loading...</div>}
            {error && <div className="empty-state" style={{ color: '#ef4444' }}>{error}</div>}

            {/* === SCOUT TAB === */}
            {!loading && !error && activeTab === 'scout' && (
              <>
                {scoutReports.length === 0 ? (
                  <div className="empty-state">
                    <p>No crowdsourced reports yet.</p>
                    <p style={{ fontSize: '0.7rem', marginTop: '0.35rem' }}>
                      Reports appear when ScoutAgent processes social media data.
                    </p>
                    <button className="refresh-btn" onClick={fetchScoutReports}>Refresh</button>
                  </div>
                ) : (
                  scoutReports.map((report, idx) => (
                    <div
                      key={idx}
                      className="report-item"
                      style={{ borderLeftColor: getSeverityColor(report.severity || 0) }}
                    >
                      <div className="report-header">
                        <div className="report-location">{report.location || 'Unknown Location'}</div>
                        <div
                          className="severity-badge"
                          style={{ background: getSeverityColor(report.severity || 0) }}
                        >
                          {getSeverityLabel(report.severity || 0)}
                        </div>
                      </div>
                      {report.text && <div className="report-text">{report.text}</div>}
                      <div className="report-meta">
                        <span>
                          {report.coordinates?.lat && report.coordinates?.lon
                            ? `${report.coordinates.lat.toFixed(4)}, ${report.coordinates.lon.toFixed(4)}`
                            : 'No coordinates'}
                        </span>
                        <span>
                          {report.timestamp ? new Date(report.timestamp).toLocaleTimeString() : ''}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </>
            )}

            {/* === FLOOD TAB === */}
            {!loading && !error && activeTab === 'flood' && (
              <>
                {/* Critical alerts section */}
                {criticalAlerts.length > 0 && (
                  <>
                    <div className="section-title">Critical Alerts</div>
                    {criticalAlerts.map((alert, idx) => (
                      <div key={idx} className="alert-item">
                        <div className="alert-station">{alert.station || 'Unknown Station'}</div>
                        <div className="alert-detail">
                          Level: {alert.level} | Water: {alert.water_level}m | {alert.timestamp || ''}
                        </div>
                      </div>
                    ))}
                  </>
                )}

                {!floodData || floodData.data_points === 0 ? (
                  <div className="empty-state">
                    <p>No flood data available.</p>
                    <button className="refresh-btn" onClick={fetchFloodData}>Refresh</button>
                  </div>
                ) : (
                  <>
                    <div className="stat-grid">
                      <div className="stat-card">
                        <div className="stat-label">Data Points</div>
                        <div className="stat-value">{floodData.data_points}</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Source</div>
                        <div className="stat-value small">{floodData.data_source}</div>
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-label">Last Update</div>
                      <div className="stat-value small">
                        {floodData.last_update ? new Date(floodData.last_update).toLocaleString() : 'Unknown'}
                      </div>
                    </div>
                    {floodData.note && (
                      <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.5rem' }}>
                        {floodData.note}
                      </div>
                    )}
                  </>
                )}
              </>
            )}

            {/* === HAZARD TAB === */}
            {!loading && !error && activeTab === 'hazard' && (
              <>
                {/* Risk distribution */}
                {riskScores && (
                  <>
                    <div className="section-title">Risk Distribution</div>
                    <div className="stat-grid">
                      <div className="stat-card">
                        <div className="stat-label">Safe Edges</div>
                        <div className="stat-value" style={{ color: '#22c55e' }}>
                          {riskScores.graph_stats?.safe_edges?.toLocaleString()}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Moderate Risk</div>
                        <div className="stat-value" style={{ color: '#eab308' }}>
                          {riskScores.graph_stats?.moderate_risk_edges?.toLocaleString()}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">High Risk</div>
                        <div className="stat-value" style={{ color: '#f97316' }}>
                          {riskScores.graph_stats?.high_risk_edges?.toLocaleString()}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Impassable</div>
                        <div className="stat-value" style={{ color: '#ef4444' }}>
                          {riskScores.graph_stats?.impassable_edges?.toLocaleString()}
                        </div>
                      </div>
                    </div>

                    {/* Risk bar */}
                    <div className="stat-card">
                      <div className="stat-label">
                        Average Risk: {(riskScores.risk_distribution?.avg_risk * 100).toFixed(1)}%
                        &nbsp;|&nbsp;Max: {(riskScores.risk_distribution?.max_risk * 100).toFixed(1)}%
                      </div>
                      <div className="risk-bar-container">
                        <div
                          className="risk-bar"
                          style={{
                            width: `${Math.max(riskScores.risk_distribution?.avg_risk * 100, 2)}%`,
                            background: getRiskBarColor(riskScores.risk_distribution?.avg_risk),
                          }}
                        />
                      </div>
                    </div>

                    {/* Blocking info */}
                    {riskScores.blocking_info && (
                      <div className="stat-card">
                        <div className="stat-label">Road Blocking</div>
                        <div className="stat-value small">
                          {riskScores.blocking_info.edges_that_will_block} edges blocked
                          ({riskScores.blocking_info.percentage_blocked.toFixed(2)}%)
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* Hazard cache entries */}
                {hazardData?.flood_data_cache && (
                  <>
                    <div className="section-title">
                      Flood Sensor Cache ({Object.keys(hazardData.flood_data_cache).length} stations)
                    </div>
                    {Object.entries(hazardData.flood_data_cache).map(([name, data]) => (
                      <div key={name} className="hazard-entry">
                        <div className="hazard-location">{name}</div>
                        <div className="hazard-values">
                          <span>Depth: {data.flood_depth?.toFixed(1)}m</span>
                          <span>Rain 1h: {data.rainfall_1h?.toFixed(1)}mm</span>
                        </div>
                      </div>
                    ))}
                  </>
                )}

                {!riskScores && !hazardData && (
                  <div className="empty-state">
                    <p>No hazard data available.</p>
                    <button className="refresh-btn" onClick={fetchHazardData}>Refresh</button>
                  </div>
                )}
              </>
            )}

            {/* === ORCHESTRATOR TAB === */}
            {!loading && !error && activeTab === 'orchestrator' && (
              <>
                {orchestratorData ? (
                  <>
                    <div className="stat-grid">
                      <div className="stat-card">
                        <div className="stat-label">Active Missions</div>
                        <div className="stat-value" style={{ color: orchestratorData.active.length > 0 ? '#f59e0b' : '#22c55e' }}>
                          {orchestratorData.active.length}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Completed</div>
                        <div className="stat-value">{orchestratorData.completed.length}</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Ticks</div>
                        <div className="stat-value small">{orchestratorData.ticks.toLocaleString()}</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Errors</div>
                        <div className="stat-value small" style={{ color: orchestratorData.errors > 0 ? '#ef4444' : '#22c55e' }}>
                          {orchestratorData.errors}
                        </div>
                      </div>
                    </div>

                    {/* Active missions */}
                    {orchestratorData.active.length > 0 && (
                      <>
                        <div className="section-title">Active Missions</div>
                        {orchestratorData.active.map((mission) => (
                          <div key={mission.id} className="report-item" style={{ borderLeftColor: '#f59e0b' }}>
                            <div className="report-header">
                              <div className="report-location">{mission.type?.replace(/_/g, ' ')}</div>
                              <div className="severity-badge" style={{ background: '#f59e0b' }}>
                                {mission.state}
                              </div>
                            </div>
                            <div className="report-meta">
                              <span>{mission.id?.slice(0, 8)}...</span>
                              <span>{mission.created_at ? new Date(mission.created_at).toLocaleTimeString() : ''}</span>
                            </div>
                          </div>
                        ))}
                      </>
                    )}

                    {/* Recent completed missions */}
                    {orchestratorData.completed.length > 0 && (
                      <>
                        <div className="section-title">
                          Recent Completed ({orchestratorData.completed.length})
                        </div>
                        {orchestratorData.completed.slice(0, 10).map((mission) => {
                          const isSuccess = mission.state === 'COMPLETED' || mission.state === 'completed';
                          return (
                            <div key={mission.id} className="report-item" style={{ borderLeftColor: isSuccess ? '#22c55e' : '#ef4444' }}>
                              <div className="report-header">
                                <div className="report-location">{mission.type?.replace(/_/g, ' ')}</div>
                                <div className="severity-badge" style={{ background: isSuccess ? '#22c55e' : '#ef4444' }}>
                                  {mission.state}
                                </div>
                              </div>
                              {mission.result?.summary && (
                                <div className="report-text">{mission.result.summary}</div>
                              )}
                              <div className="report-meta">
                                <span>{mission.id?.slice(0, 8)}...</span>
                                <span>{mission.completed_at ? new Date(mission.completed_at).toLocaleTimeString() : ''}</span>
                              </div>
                            </div>
                          );
                        })}
                      </>
                    )}

                    {orchestratorData.active.length === 0 && orchestratorData.completed.length === 0 && (
                      <div className="empty-state" style={{ marginTop: '0.5rem' }}>
                        <p>No missions recorded yet.</p>
                        <p style={{ fontSize: '0.7rem', marginTop: '0.35rem' }}>
                          Use the AI Chat or send orchestrator commands to create missions.
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty-state">
                    <p>No orchestrator data available.</p>
                    <button className="refresh-btn" onClick={fetchOrchestratorData}>Refresh</button>
                  </div>
                )}
              </>
            )}

            {/* === SYSTEM TAB === */}
            {!loading && !error && activeTab === 'system' && (
              <>
                {systemData?.lifecycle && (
                  <>
                    <div className="section-title">Lifecycle Manager</div>
                    <div className="stat-grid">
                      <div className="stat-card">
                        <div className="stat-label">Status</div>
                        <div className="stat-value small" style={{ color: systemData.lifecycle.is_running ? '#22c55e' : '#ef4444' }}>
                          {systemData.lifecycle.is_running ? 'Running' : 'Stopped'}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Uptime</div>
                        <div className="stat-value small">
                          {formatUptime(systemData.lifecycle.uptime_seconds)}
                        </div>
                      </div>
                    </div>

                    {/* Agent tick counts */}
                    {systemData.lifecycle.statistics?.agent_step_counts && (
                      <>
                        <div className="section-title">Agent Ticks</div>
                        <div className="stat-card" style={{ padding: '0.5rem 0.75rem' }}>
                          {Object.entries(systemData.lifecycle.statistics.agent_step_counts).map(([agent, count]) => {
                            const errors = systemData.lifecycle.statistics.agent_step_errors?.[agent] || 0;
                            return (
                              <div key={agent} className="agent-tick-row">
                                <span className="agent-name">{agent.replace(/_/g, ' ')}</span>
                                <span>
                                  <span className="tick-count">{count.toLocaleString()}</span>
                                  {errors > 0 && <span className="error-badge">{errors} err</span>}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                  </>
                )}

                {systemData?.statistics && (
                  <>
                    <div className="section-title">Graph Statistics</div>
                    <div className="stat-grid">
                      <div className="stat-card">
                        <div className="stat-label">Nodes</div>
                        <div className="stat-value">
                          {systemData.statistics.graph_statistics?.total_nodes?.toLocaleString()}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Edges</div>
                        <div className="stat-value">
                          {systemData.statistics.graph_statistics?.total_edges?.toLocaleString()}
                        </div>
                      </div>
                    </div>

                    <div className="section-title">Route Statistics</div>
                    <div className="stat-grid">
                      <div className="stat-card">
                        <div className="stat-label">Total Routes</div>
                        <div className="stat-value">{systemData.statistics.route_statistics?.total_routes}</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-label">Distress Calls</div>
                        <div className="stat-value">{systemData.statistics.route_statistics?.total_distress_calls}</div>
                      </div>
                    </div>
                  </>
                )}

                {/* Graph Reset */}
                <div className="section-title">Actions</div>
                <button
                  className="refresh-btn"
                  onClick={handleGraphReset}
                  disabled={graphResetting}
                  style={{
                    background: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#fca5a5',
                    padding: '0.6rem 1rem',
                    width: '100%',
                    textAlign: 'center',
                    fontWeight: 600,
                  }}
                >
                  {graphResetting ? 'Resetting...' : 'Reset Graph (Reload from file)'}
                </button>
                <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.35)', marginTop: '0.25rem' }}>
                  Reloads graph from GraphML file, resets all risk scores to 0
                </div>

                {!systemData && (
                  <div className="empty-state">
                    <p>No system data available.</p>
                    <button className="refresh-btn" onClick={fetchSystemData}>Refresh</button>
                  </div>
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
