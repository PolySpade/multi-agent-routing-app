'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import LocationSearch from '@/components/LocationSearch';
import FeedbackForm from '@/components/FeedbackForm';
import SimulationPanel from '@/components/SimulationPanel';
import AgentDataPanel from '@/components/AgentDataPanel';
import EvacuationCentersPanel from '@/components/EvacuationCentersPanel';
import RiskLegend from '@/components/RiskLegend';
import { findRoute } from '@/utils/routingService';
import { useWebSocketContext } from '@/contexts/WebSocketContext';

// Utility formatting functions remain the same
const formatDistance = (meters) => {
  if (meters == null) return '—';
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
};

const formatDuration = (seconds) => {
  if (seconds == null) return '—';
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes} min`;
};

const formatCoordinate = (point) => {
  if (!point) return 'Not selected';
  return `${point.lat.toFixed(4)}°, ${point.lng.toFixed(4)}°`;
};

const getRiskInfo = (riskLevel) => {
  if (riskLevel === null || riskLevel === undefined) return { label: '—', color: '#94a3b8', description: 'No data' };

  // Risk level is 0-1 scale
  if (riskLevel <= 0.2) return {
    label: 'Very Low',
    color: '#10b981',
    description: 'Safe - No significant flood risk',
    depth: 'Dry or < 6 inches (ankle level)'
  };
  if (riskLevel <= 0.4) return {
    label: 'Low',
    color: '#84cc16',
    description: 'Minor risk - Passable with caution',
    depth: '6-12 inches (below knee)'
  };
  if (riskLevel <= 0.6) return {
    label: 'Moderate',
    color: '#eab308',
    description: 'Moderate risk - Drive slowly',
    depth: '1-2 feet (knee to waist)'
  };
  if (riskLevel <= 0.8) return {
    label: 'High',
    color: '#f97316',
    description: 'High risk - Dangerous conditions',
    depth: '2-3 feet (waist to chest)'
  };
  return {
    label: 'Critical',
    color: '#ef4444',
    description: 'Critical - Impassable or extremely dangerous',
    depth: '> 3 feet (chest level or higher)'
  };
};

export default function Home() {
  // --- State & Hooks ---
  const [startPoint, setStartPoint] = useState(null);
  const [endPoint, setEndPoint] = useState(null);
  const [routePath, setRoutePath] = useState(null);
  const [routeMeta, setRouteMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('Select a Start Point to begin.');
  const [selectionMode, setSelectionMode] = useState(null);
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackLocation, setFeedbackLocation] = useState(null);
  const [showAgentPanel, setShowAgentPanel] = useState(true);
  const [showEvacuationPanel, setShowEvacuationPanel] = useState(true);
  const [routingMode, setRoutingMode] = useState('balanced'); // 'safest', 'balanced', 'fastest'

  const { isConnected, systemStatus } = useWebSocketContext();

  // --- Map Component ---
  const MapboxMap = useMemo(() => dynamic(() => import('@/components/MapboxMap'), { 
    loading: () => (
      <div className="map-loader">
        <div className="spinner"></div>
        <span>Loading Mapbox...</span>
      </div>
    ),
    ssr: false 
  }), []);

  // --- Handlers ---
  const handleLocationSelect = (location, type) => {
    if (type === 'start') {
      setStartPoint({ lat: location.lat, lng: location.lng });
      setMessage('Start set. Now select your Destination.');
    } else if (type === 'end') {
      setEndPoint({ lat: location.lat, lng: location.lng });
      setMessage('Destination set. Ready to calculate route.');
    }
  };

  const handleMapClick = (latlng) => {
    if (selectionMode === 'start') {
      setStartPoint(latlng);
      setSelectionMode(null);
      setMessage('Start set. Now select Destination.');
    } else if (selectionMode === 'end') {
      setEndPoint(latlng);
      setSelectionMode(null);
      setMessage('Destination set. Ready to calculate.');
    } else {
      setMessage('Please select a button (Start/End) before clicking the map.');
    }
  };

  const handleSelectStartMode = () => {
    setSelectionMode('start');
    setMessage('Click anywhere on the map to set Start.');
  };

  const handleSelectEndMode = () => {
    if (!startPoint) {
      setMessage('Please select a start point first.');
      return;
    }
    setSelectionMode('end');
    setMessage('Click anywhere on the map to set Destination.');
  };

  const handleFindRoute = async () => {
    await findRoute(startPoint, endPoint, setRoutePath, setRouteMeta, setMessage, setLoading, routingMode);
  };

  const handleReset = () => {
    setStartPoint(null);
    setEndPoint(null);
    setRoutePath(null);
    setRouteMeta(null);
    setSelectionMode(null);
    setMessage('Route reset. Select a Start Point.');
  };

  const handleSwapPoints = () => {
    if (!startPoint || !endPoint) return;
    setStartPoint(endPoint);
    setEndPoint(startPoint);
    setRoutePath(null);
    setRouteMeta(null);
    setMessage('Points swapped. Recalculate route to update.');
  };

  const handleUseCurrentLocation = useCallback(() => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      setMessage('Geolocation not supported.');
      return;
    }
    setMessage('Locating you...');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coords = { lat: position.coords.latitude, lng: position.coords.longitude };
        setStartPoint(coords);
        setMessage('Current location applied.');
      },
      (error) => {
        console.error(error);
        setMessage('Could not get location.');
      }
    );
  }, []);

  const handleOpenFeedback = () => {
    setShowFeedback(true);
    setFeedbackLocation(startPoint);
  };

  // System Status Effect
  useEffect(() => {
    if (systemStatus && !loading) {
      if (systemStatus.graph_status === 'loaded') setMessage('System Online: Graph loaded.');
      else if (systemStatus.graph_status === 'not_loaded') setMessage('System Warning: Graph offline.');
    }
  }, [systemStatus, loading]);

  const hasRoute = Array.isArray(routePath) && routePath.length > 0;

  return (
    <div className="app-container">
      {/* --- Global Styles --- */}
      <style jsx global>{`
        :root {
          --primary: #248ea8;
          --primary-dark: #1a6b7f;
          --accent: #e15c45;
          --accent-dark: #c94a37;
          --bg-dark: #0f1419;
          --glass-bg: rgba(255, 255, 255, 0.08);
          --glass-border: rgba(255, 255, 255, 0.15);
          --text-main: #e2e8f0;
          --text-muted: #94a3b8;
        }

        * { box-sizing: border-box; }
        
        body {
          margin: 0;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          background-color: var(--bg-dark);
          color: var(--text-main);
          overflow: hidden; /* Prevent body scroll */
        }

        /* Animations */
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes pulse { 50% { opacity: 0.5; } }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* Scrollbar styling */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; }
      `}</style>

      {/* --- Component Styles --- */}
      <style jsx>{`
        .app-container {
          display: grid;
          grid-template-columns: ${isPanelCollapsed ? '0px' : '400px'} 1fr ${showAgentPanel || showEvacuationPanel ? '440px' : '0px'};
          height: 100vh;
          transition: grid-template-columns 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
          background: linear-gradient(135deg, #1a1f2e, #0f1419);
        }

        /* --- Sidebar --- */
        aside {
          background: linear-gradient(180deg, rgba(36, 142, 168, 0.15) 0%, rgba(15, 20, 25, 0.95) 100%);
          backdrop-filter: blur(20px);
          border-right: 1px solid var(--glass-border);
          display: flex;
          flex-direction: column;
          overflow-y: auto; /* Allow scrolling inside sidebar */
          overflow-x: hidden;
          position: relative;
          z-index: 10;
        }

        .sidebar-content {
          padding: 2rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          min-height: 100%;
          width: 400px; /* Fixed width to prevent layout shift during collapse transition */
          opacity: ${isPanelCollapsed ? 0 : 1};
          transition: opacity 0.3s ease;
        }

        /* Header */
        header h1 {
          font-size: 2.2rem;
          margin: 0;
          background: linear-gradient(to right, #fff, #cbd5e1);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          font-weight: 800;
        }
        
        .header-subtitle {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.15em;
          color: var(--primary);
          font-weight: 600;
          margin-top: 0.25rem;
        }

        .nav-link {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.4rem 0.8rem;
          border-radius: 20px;
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          color: var(--text-main);
          text-decoration: none;
          font-size: 0.8rem;
          transition: all 0.2s;
        }
        .nav-link:hover { background: rgba(255,255,255,0.15); }

        /* Cards & Sections */
        .glass-card {
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          border-radius: 16px;
          padding: 1.5rem;
          box-shadow: 0 4px 20px rgba(0,0,0,0.2);
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .section-title {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: var(--text-muted);
          font-weight: 700;
          margin-bottom: 0.5rem;
        }

        /* Buttons */
        .btn {
          padding: 0.75rem 1rem;
          border-radius: 10px;
          border: none;
          font-weight: 600;
          font-size: 0.9rem;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          color: white;
        }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .btn-primary {
          background: linear-gradient(135deg, var(--primary), var(--primary-dark));
          box-shadow: 0 4px 12px rgba(36, 142, 168, 0.3);
        }
        .btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(36, 142, 168, 0.5); }

        .btn-secondary {
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--glass-border);
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.3); }

        .btn-accent {
          background: rgba(225, 92, 69, 0.15);
          border: 1px solid rgba(225, 92, 69, 0.3);
          color: #ff8a75;
        }
        .btn-accent:hover { background: rgba(225, 92, 69, 0.25); }

        /* Selection Group */
        .selection-group {
          display: flex;
          gap: 0.75rem;
        }
        
        .select-btn {
          flex: 1;
          padding: 1rem;
          border-radius: 12px;
          border: 1px solid transparent;
          background: rgba(255,255,255,0.03);
          color: var(--text-muted);
          text-align: left;
          cursor: pointer;
          transition: all 0.2s;
        }
        .select-btn:hover { background: rgba(255,255,255,0.08); }
        .select-btn.active {
          background: rgba(36, 142, 168, 0.2);
          border-color: var(--primary);
          color: white;
        }
        .select-btn.filled {
          border-color: rgba(255,255,255,0.2);
          color: var(--text-main);
        }
        
        .coord-display {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.8rem;
          opacity: 0.7;
          margin-top: 0.25rem;
        }

        /* Routing Mode Selection */
        .routing-mode-group {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 0.5rem;
        }

        .routing-mode-btn {
          padding: 0.75rem 0.5rem;
          border-radius: 10px;
          border: 1px solid transparent;
          background: rgba(255,255,255,0.03);
          color: var(--text-muted);
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
        }

        .routing-mode-btn:hover {
          background: rgba(255,255,255,0.08);
          border-color: rgba(255,255,255,0.1);
        }

        .routing-mode-btn.active {
          background: rgba(36, 142, 168, 0.25);
          border-color: var(--primary);
          color: white;
        }

        .routing-mode-btn.active .mode-icon {
          transform: scale(1.1);
        }

        .mode-icon {
          font-size: 1.5rem;
          transition: transform 0.2s;
        }

        .mode-label {
          font-size: 0.8rem;
          font-weight: 600;
        }

        .mode-desc {
          font-size: 0.65rem;
          opacity: 0.7;
        }

        /* Status Box */
        .status-box {
          margin-top: auto; /* Pushes to bottom */
          background: rgba(15, 20, 25, 0.6);
          border-radius: 12px;
          padding: 1rem;
          border-left: 3px solid var(--primary);
          margin-bottom: 2rem;
        }
        .status-header {
          display: flex;
          justify-content: space-between;
          font-size: 0.75rem;
          text-transform: uppercase;
          margin-bottom: 0.5rem;
          color: var(--text-muted);
        }
        .live-dot {
          width: 8px;
          height: 8px;
          background: var(--primary);
          border-radius: 50%;
          display: inline-block;
          animation: pulse 2s infinite;
        }
        .status-msg { font-size: 0.9rem; line-height: 1.4; }

        /* Stats Grid */
        .stats-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.75rem;
          margin-top: 0.75rem;
          padding-top: 0.75rem;
          border-top: 1px solid rgba(255,255,255,0.1);
        }
        .stat-item strong { display: block; font-size: 1.1rem; }
        .stat-item span { font-size: 0.7rem; text-transform: uppercase; color: var(--text-muted); }

        /* --- Main Map Area --- */
        .map-area {
          position: relative;
          height: 100vh;
          background: #0f1419;
        }

        /* Map Overlay */
        .map-overlay {
          position: absolute;
          top: 20px;
          left: 20px;
          width: 320px;
          padding: 1.25rem;
          background: rgba(15, 20, 25, 0.85);
          backdrop-filter: blur(12px);
          border-radius: 16px;
          border: 1px solid rgba(255,255,255,0.1);
          color: white;
          box-shadow: 0 8px 32px rgba(0,0,0,0.4);
          animation: slideIn 0.4s ease-out;
          z-index: 5;
        }

        .map-loader {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          background: linear-gradient(135deg, var(--primary), var(--primary-dark));
          color: white;
        }
        .spinner {
          width: 40px; height: 40px;
          border: 4px solid rgba(255,255,255,0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 1rem;
        }

        /* Collapse/Expand Controls */
        .collapse-ctrl {
          position: absolute;
          top: 1rem;
          right: 1rem;
          background: transparent;
          border: 1px solid var(--glass-border);
          color: var(--text-muted);
          border-radius: 8px;
          padding: 0.4rem 0.8rem;
          cursor: pointer;
          font-size: 0.8rem;
        }
        .expand-ctrl {
          position: absolute;
          top: 20px;
          left: 20px;
          z-index: 20;
          background: var(--bg-dark);
          color: white;
          border: 1px solid var(--glass-border);
          padding: 0.6rem 1.2rem;
          border-radius: 30px;
          cursor: pointer;
          font-weight: 600;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        /* Feedback Modal Overlay */
        .modal-overlay {
          position: fixed; inset: 0;
          background: rgba(0,0,0,0.8);
          backdrop-filter: blur(5px);
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1rem;
        }

        /* --- Right Panels Container --- */
        .panels-container {
          background: linear-gradient(180deg, rgba(15, 20, 25, 0.95) 0%, rgba(26, 31, 46, 0.95) 100%);
          backdrop-filter: blur(20px);
          border-left: 1px solid var(--glass-border);
          display: flex;
          flex-direction: column;
          gap: 1rem;
          padding: 1rem;
          overflow-y: auto;
          overflow-x: hidden;
          position: relative;
          z-index: 30;
        }

        .panels-container::-webkit-scrollbar {
          width: 6px;
        }

        .panels-container::-webkit-scrollbar-track {
          background: transparent;
        }

        .panels-container::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.2);
          border-radius: 10px;
        }
      `}</style>

      {/* --- Sidebar --- */}
      <aside>
        {!isPanelCollapsed && (
          <div className="sidebar-content">
            <header>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
                <div>
                  <h1>MAS-FRO</h1>
                  <div className="header-subtitle">Smart Flood Routing</div>
                </div>
                <button onClick={() => setIsPanelCollapsed(true)} className="collapse-ctrl">
                  Hide ⇱
                </button>
              </div>
              <div style={{marginTop: '1rem', display:'flex', gap:'0.5rem', flexWrap: 'wrap'}}>
                <Link href="/dashboard" className="nav-link">
                  📊 Dashboard
                </Link>
                <button
                  onClick={() => setShowAgentPanel(!showAgentPanel)}
                  className="nav-link"
                  style={{ border: 'none', cursor: 'pointer' }}
                >
                  🤖 {showAgentPanel ? 'Hide' : 'Show'} Agents
                </button>
                <button
                  onClick={() => setShowEvacuationPanel(!showEvacuationPanel)}
                  className="nav-link"
                  style={{ border: 'none', cursor: 'pointer' }}
                >
                  🏥 {showEvacuationPanel ? 'Hide' : 'Show'} Centers
                </button>
              </div>
            </header>

            {/* Search Section */}
            <div className="glass-card">
              <div className="section-title">Quick Search</div>
              <LocationSearch
                onLocationSelect={(loc) => handleLocationSelect(loc, 'start')}
                placeholder="Start Address..."
                type="start"
              />
              <LocationSearch
                onLocationSelect={(loc) => handleLocationSelect(loc, 'end')}
                placeholder="Destination..."
                type="end"
              />
              <button className="btn btn-secondary" onClick={handleUseCurrentLocation}>
                📍 Use My Location as Start
              </button>
            </div>

            {/* Routing Controls */}
            <div className="glass-card">
              <div className="section-title">Manual Selection</div>
              
              {selectionMode && (
                <div style={{
                  background: 'rgba(36, 142, 168, 0.2)', 
                  color: '#7dd3fc', 
                  padding:'0.5rem', 
                  borderRadius:'8px', 
                  fontSize:'0.85rem',
                  textAlign:'center'
                }}>
                  🖱️ Click map to set {selectionMode === 'start' ? 'Start Point' : 'Destination'}
                </div>
              )}

              <div className="selection-group">
                <button 
                  className={`select-btn ${selectionMode === 'start' ? 'active' : ''} ${startPoint ? 'filled' : ''}`}
                  onClick={handleSelectStartMode}
                >
                  <div>Start Point</div>
                  <div className="coord-display">{formatCoordinate(startPoint)}</div>
                </button>

                <button 
                  className={`select-btn ${selectionMode === 'end' ? 'active' : ''} ${endPoint ? 'filled' : ''}`}
                  onClick={handleSelectEndMode}
                  disabled={!startPoint}
                >
                  <div>Destination</div>
                  <div className="coord-display">{formatCoordinate(endPoint)}</div>
                </button>
              </div>

              <div className="selection-group">
                <button className="btn btn-secondary" style={{flex:1}} onClick={handleSwapPoints}>
                  ⇅ Swap
                </button>
                <button className="btn btn-secondary" style={{flex:1}} onClick={handleReset}>
                  ✖ Reset
                </button>
              </div>

              {/* Routing Mode Selection */}
              <div style={{ marginTop: '0.5rem' }}>
                <div className="section-title" style={{ marginBottom: '0.75rem' }}>Routing Algorithm</div>
                <div className="routing-mode-group">
                  <button
                    className={`routing-mode-btn ${routingMode === 'safest' ? 'active' : ''}`}
                    onClick={() => setRoutingMode('safest')}
                  >
                    <div className="mode-icon">🛡️</div>
                    <div className="mode-label">Safest</div>
                    <div className="mode-desc">Avoid floods</div>
                  </button>
                  <button
                    className={`routing-mode-btn ${routingMode === 'balanced' ? 'active' : ''}`}
                    onClick={() => setRoutingMode('balanced')}
                  >
                    <div className="mode-icon">⚖️</div>
                    <div className="mode-label">Balanced</div>
                    <div className="mode-desc">Safety + Speed</div>
                  </button>
                  <button
                    className={`routing-mode-btn ${routingMode === 'fastest' ? 'active' : ''}`}
                    onClick={() => setRoutingMode('fastest')}
                  >
                    <div className="mode-icon">⚡</div>
                    <div className="mode-label">Fastest</div>
                    <div className="mode-desc">Risk-tolerant</div>
                  </button>
                </div>
              </div>

              <button
                className="btn btn-primary"
                onClick={handleFindRoute}
                disabled={loading || !startPoint || !endPoint}
                style={{ marginTop: '0.5rem' }}
              >
                {loading ? 'Calculating...' : `🚗 Find ${routingMode === 'safest' ? 'Safest' : routingMode === 'fastest' ? 'Fastest' : 'Best'} Route`}
              </button>
            </div>

            {/* Risk Legend */}
            <RiskLegend />

            {/* <button className="btn btn-accent" onClick={handleOpenFeedback}>
              ⚠️ Report Flood / Road Issue
            </button> */}

            {/* Status Bar */}
            <div className="status-box">
              <div className="status-header">
                <span>System Status</span>
                <span>{isConnected ? <span className="live-dot"/> : 'Offline'}</span>
              </div>
              <div className="status-msg">{message}</div>
              
              {routeMeta && (
                <div className="stats-grid">
                  <div className="stat-item">
                    <span>Distance</span>
                    <strong>{formatDistance(routeMeta.distance)}</strong>
                  </div>
                  {/* <div className="stat-item">
                    <span>Est. Time</span>
                    <strong>{formatDuration(routeMeta.duration)}</strong>
                  </div> */}
                  <div className="stat-item" style={{ gridColumn: '1 / -1' }}>
                    <span>Provider</span>
                    <strong style={{
                      color: routeMeta.provider === 'backend' ? '#10b981' : '#f59e0b',
                      fontSize: '0.85rem'
                    }}>
                      {routeMeta.provider === 'backend' ? '🤖 MAS-FRO Backend' : '🗺️ Mapbox (Fallback)'}
                    </strong>
                  </div>
                  {routeMeta.riskLevel !== null && routeMeta.riskLevel !== undefined && (
                    <div className="stat-item" style={{ gridColumn: '1 / -1' }}>
                      <span>Average Risk</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                        <div style={{
                          width: '12px',
                          height: '12px',
                          borderRadius: '50%',
                          backgroundColor: getRiskInfo(routeMeta.riskLevel).color,
                          boxShadow: `0 0 8px ${getRiskInfo(routeMeta.riskLevel).color}66`
                        }} />
                        <strong style={{ color: getRiskInfo(routeMeta.riskLevel).color }}>
                          {getRiskInfo(routeMeta.riskLevel).label}
                        </strong>
                        <span style={{ fontSize: '0.85rem', opacity: 0.7, marginLeft: 'auto' }}>
                          ({(routeMeta.riskLevel * 100).toFixed(0)}%)
                        </span>
                      </div>
                      <div style={{ fontSize: '0.7rem', opacity: 0.7, marginTop: '0.25rem' }}>
                        {getRiskInfo(routeMeta.riskLevel).description}
                      </div>
                    </div>
                  )}
                  {routeMeta.provider === 'mapbox' && (
                    <div style={{
                      gridColumn: '1 / -1',
                      fontSize: '0.7rem',
                      opacity: 0.7,
                      padding: '0.5rem',
                      background: 'rgba(245, 158, 11, 0.1)',
                      borderRadius: '6px',
                      color: '#f59e0b'
                    }}>
                      ⚠️ Using Mapbox fallback - Backend may be unavailable. Check browser console for errors.
                    </div>
                  )}

                  {/* Display warnings from backend */}
                  {routeMeta.warnings && routeMeta.warnings.length > 0 && (
                    <div style={{
                      gridColumn: '1 / -1',
                      marginTop: '0.5rem'
                    }}>
                      {routeMeta.warnings.map((warning, idx) => {
                        const isImpassable = warning.includes('IMPASSABLE');
                        const isCritical = warning.includes('CRITICAL');
                        const isWarning = warning.includes('WARNING');
                        const isFastestMode = warning.includes('FASTEST MODE ACTIVE');

                        let bgColor = 'rgba(156, 163, 175, 0.1)';
                        let textColor = '#9ca3af';
                        let icon = '💬';

                        if (isImpassable) {
                          bgColor = 'rgba(239, 68, 68, 0.15)';
                          textColor = '#ef4444';
                          icon = '⛔';
                        } else if (isCritical) {
                          bgColor = 'rgba(239, 68, 68, 0.1)';
                          textColor = '#f87171';
                          icon = '🚨';
                        } else if (isFastestMode) {
                          bgColor = 'rgba(251, 191, 36, 0.15)';
                          textColor = '#fbbf24';
                          icon = '⚡';
                        } else if (isWarning) {
                          bgColor = 'rgba(251, 146, 60, 0.1)';
                          textColor = '#fb923c';
                          icon = '⚠️';
                        }

                        return (
                          <div
                            key={idx}
                            style={{
                              fontSize: '0.75rem',
                              padding: '0.5rem',
                              background: bgColor,
                              borderRadius: '6px',
                              color: textColor,
                              marginBottom: idx < routeMeta.warnings.length - 1 ? '0.5rem' : '0',
                              lineHeight: '1.4',
                              borderLeft: `3px solid ${textColor}`
                            }}
                          >
                            <span style={{ marginRight: '0.3rem' }}>{icon}</span>
                            {warning}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Status indicator for impassable/no_safe_route */}
                  {routeMeta.status && routeMeta.status !== 'success' && (
                    <div style={{
                      gridColumn: '1 / -1',
                      marginTop: '0.5rem',
                      padding: '0.75rem',
                      background: routeMeta.status === 'impassable'
                        ? 'rgba(239, 68, 68, 0.2)'
                        : 'rgba(251, 146, 60, 0.15)',
                      borderRadius: '8px',
                      border: `2px solid ${routeMeta.status === 'impassable' ? '#ef4444' : '#fb923c'}`,
                      textAlign: 'center'
                    }}>
                      <div style={{
                        fontSize: '1.5rem',
                        marginBottom: '0.25rem'
                      }}>
                        {routeMeta.status === 'impassable' ? '⛔' : '⚠️'}
                      </div>
                      <div style={{
                        fontSize: '0.85rem',
                        fontWeight: 'bold',
                        color: routeMeta.status === 'impassable' ? '#ef4444' : '#fb923c',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        {routeMeta.status === 'impassable' ? 'All Roads Impassable' : 'No Safe Route'}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </aside>

      {/* --- Map Area --- */}
      <section className="map-area">
        {isPanelCollapsed && (
          <button onClick={() => setIsPanelCollapsed(false)} className="expand-ctrl">
            Show Controls ⇲
          </button>
        )}

        {/* Map Overlay - Shows summary when route is active, useful if panel is hidden */}
        {/* <div className="map-overlay" style={{ display: !hasRoute && !isPanelCollapsed ? 'none' : 'block' }}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'0.5rem'}}>
                <strong style={{textTransform:'uppercase', letterSpacing:'1px', fontSize:'0.8rem', color:'var(--primary)'}}>
                    Route Status
                </strong>
                <span style={{
                    fontSize:'0.7rem', 
                    background: hasRoute ? 'rgba(36, 142, 168, 0.3)' : 'rgba(255,255,255,0.1)', 
                    padding:'2px 8px', 
                    borderRadius:'10px'
                }}>
                    {hasRoute ? 'Active' : 'Pending'}
                </span>
            </div>
            <div style={{fontSize:'0.9rem', opacity: 0.9}}>
                {hasRoute ? 'Optimized path displayed.' : 'Awaiting configuration.'}
            </div>
            {hasRoute && routeMeta && (
                <div className="stats-grid" style={{borderTopColor: 'rgba(255,255,255,0.1)'}}>
                     <div className="stat-item">
                        <span>Distance</span>
                        <strong>{formatDistance(routeMeta.distance)}</strong>
                    </div>
                    <div className="stat-item">
                        <span>Time</span>
                        <strong>{formatDuration(routeMeta.duration)}</strong>
                    </div>
                    {routeMeta.riskLevel !== null && routeMeta.riskLevel !== undefined && (
                      <div className="stat-item" style={{ gridColumn: '1 / -1' }}>
                        <span>Risk</span>
                        <strong style={{ color: getRiskInfo(routeMeta.riskLevel).color }}>
                          {getRiskInfo(routeMeta.riskLevel).label}
                        </strong>
                      </div>
                    )}
                </div>
            )}
        </div> */}

        <MapboxMap
          startPoint={startPoint}
          endPoint={endPoint}
          routePath={routePath}
          onMapClick={handleMapClick}
          panelCollapsed={isPanelCollapsed}
          selectionMode={selectionMode}
        />
      </section>

      {/* --- Right Panels Container --- */}
      {(showAgentPanel || showEvacuationPanel) && (
        <section className="panels-container">
          {/* Simulation Panel */}
          <SimulationPanel
            isConnected={isConnected}
            floodData={null}
          />

          {/* Agent Data Panel */}
          {showAgentPanel && <AgentDataPanel />}

          {/* Evacuation Centers Panel */}
          {showEvacuationPanel && (
            <EvacuationCentersPanel
              onSelectDestination={(lat, lng, name) => {
                setEndPoint({ lat, lng });
                setMessage(`Destination set to ${name}. Click "Find Safest Route" to calculate.`);
              }}
            />
          )}
        </section>
      )}

      {/* --- Feedback Modal --- */}
      {showFeedback && (
        <div className="modal-overlay" onClick={() => setShowFeedback(false)}>
          <div onClick={(e) => e.stopPropagation()}>
            <FeedbackForm
              routeId={routePath ? 'current-route' : null}
              onClose={() => setShowFeedback(false)}
              currentLocation={feedbackLocation}
            />
          </div>
        </div>
      )}
    </div>
  );
}