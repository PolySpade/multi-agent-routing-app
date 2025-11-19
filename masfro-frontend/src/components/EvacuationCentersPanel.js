'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * EvacuationCentersPanel Component
 *
 * Dedicated panel for displaying evacuation centers with detailed information
 * including location, capacity, contact details, and availability status.
 */
export default function EvacuationCentersPanel() {
  const [evacuationCenters, setEvacuationCenters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);

  // Fetch evacuation centers on mount
  useEffect(() => {
    fetchEvacuationCenters();
    const interval = setInterval(fetchEvacuationCenters, 60000); // Every 60s
    return () => clearInterval(interval);
  }, []);

  const fetchEvacuationCenters = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/agents/evacuation/centers`);
      const data = await response.json();
      if (data.status === 'success') {
        setEvacuationCenters(data.centers);
        setLastUpdate(new Date());
      } else {
        setError('Failed to load evacuation centers');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    if (status === 'available') return '#22c55e';
    if (status === 'limited') return '#eab308';
    if (status === 'full') return '#ef4444';
    return '#6b7280';
  };

  const getStatusLabel = (status) => {
    if (status === 'available') return 'Available';
    if (status === 'limited') return 'Limited Space';
    if (status === 'full') return 'Full';
    return 'Unknown';
  };

  return (
    <div className="evacuation-panel">
      <style jsx>{`
        .evacuation-panel {
          position: fixed;
          top: 80px;
          right: 20px;
          width: 420px;
          max-height: calc(100vh - 120px);
          background: rgba(15, 20, 25, 0.95);
          backdrop-filter: blur(12px);
          border-radius: 16px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
          display: flex;
          flex-direction: column;
          z-index: 35;
          overflow: hidden;
          transition: all 0.3s ease;
        }

        .evacuation-panel.collapsed {
          max-height: 60px;
        }

        .panel-header {
          padding: 1.25rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          cursor: pointer;
          user-select: none;
        }

        .header-content {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .panel-title {
          font-size: 1.15rem;
          font-weight: 700;
          color: white;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .title-icon {
          width: 20px;
          height: 20px;
          color: #248ea8;
        }

        .collapse-btn {
          background: none;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          cursor: pointer;
          font-size: 1.2rem;
          transition: color 0.2s;
        }

        .collapse-btn:hover {
          color: white;
        }

        .status-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 0.5rem;
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
        }

        .status-info {
          display: flex;
          gap: 1rem;
        }

        .status-item {
          display: flex;
          align-items: center;
          gap: 0.25rem;
        }

        .panel-content {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
        }

        .center-card {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 10px;
          padding: 1.25rem;
          margin-bottom: 1rem;
          border-left: 4px solid #248ea8;
          transition: all 0.2s;
        }

        .center-card:hover {
          background: rgba(255, 255, 255, 0.08);
          transform: translateY(-2px);
        }

        .center-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 0.75rem;
        }

        .center-name {
          font-weight: 700;
          font-size: 1rem;
          color: white;
          line-height: 1.3;
        }

        .status-badge {
          padding: 0.25rem 0.625rem;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
          text-transform: uppercase;
          color: white;
          white-space: nowrap;
        }

        .center-details {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .detail-row {
          display: flex;
          align-items: flex-start;
          gap: 0.5rem;
          font-size: 0.85rem;
        }

        .detail-icon {
          width: 16px;
          height: 16px;
          color: #248ea8;
          margin-top: 2px;
          flex-shrink: 0;
        }

        .detail-label {
          font-weight: 600;
          color: rgba(255, 255, 255, 0.7);
          min-width: 70px;
        }

        .detail-value {
          color: rgba(255, 255, 255, 0.9);
          line-height: 1.4;
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
          padding: 0.625rem 1.25rem;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.85rem;
          margin-top: 1rem;
          transition: all 0.2s;
          font-weight: 600;
        }

        .refresh-btn:hover {
          background: rgba(36, 142, 168, 0.3);
          border-color: rgba(36, 142, 168, 0.5);
        }

        .summary-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 0.5rem;
          padding: 0.75rem;
          background: rgba(0, 0, 0, 0.2);
          border-radius: 8px;
          margin-bottom: 1rem;
        }

        .stat-box {
          text-align: center;
        }

        .stat-number {
          font-size: 1.5rem;
          font-weight: 700;
          color: white;
        }

        .stat-label {
          font-size: 0.7rem;
          color: rgba(255, 255, 255, 0.6);
          text-transform: uppercase;
          margin-top: 0.25rem;
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
      <div className="panel-header" onClick={() => setIsPanelCollapsed(!isPanelCollapsed)}>
        <div className="header-content">
          <h2 className="panel-title">
            <svg className="title-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Evacuation Centers
          </h2>
          <button className="collapse-btn">
            {isPanelCollapsed ? '▼' : '▲'}
          </button>
        </div>
        {!isPanelCollapsed && (
          <div className="status-bar">
            <div className="status-info">
              <div className="status-item">
                {evacuationCenters.length} Centers
              </div>
            </div>
            {lastUpdate && (
              <div className="status-item">
                Updated: {lastUpdate.toLocaleTimeString()}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      {!isPanelCollapsed && (
        <div className="panel-content">
          {loading && <div className="loading">Loading evacuation centers...</div>}
          {error && (
            <div className="error">
              <p>{error}</p>
              <button className="refresh-btn" onClick={fetchEvacuationCenters}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && evacuationCenters.length === 0 && (
            <div className="empty">
              <p>No evacuation centers available.</p>
              <p style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                Centers will appear here when data is loaded.
              </p>
              <button className="refresh-btn" onClick={fetchEvacuationCenters}>
                Refresh
              </button>
            </div>
          )}

          {!loading && !error && evacuationCenters.length > 0 && (
            <>
              {/* Summary Statistics */}
              <div className="summary-stats">
                <div className="stat-box">
                  <div className="stat-number">{evacuationCenters.length}</div>
                  <div className="stat-label">Total</div>
                </div>
                <div className="stat-box">
                  <div className="stat-number" style={{ color: '#22c55e' }}>
                    {evacuationCenters.filter(c => c.status === 'available').length}
                  </div>
                  <div className="stat-label">Available</div>
                </div>
                <div className="stat-box">
                  <div className="stat-number" style={{ color: '#eab308' }}>
                    {evacuationCenters.filter(c => c.status === 'limited').length}
                  </div>
                  <div className="stat-label">Limited</div>
                </div>
              </div>

              {/* Evacuation Center Cards */}
              {evacuationCenters.map((center, idx) => (
                <div key={idx} className="center-card">
                  <div className="center-header">
                    <div className="center-name">{center.name}</div>
                    <div
                      className="status-badge"
                      style={{ backgroundColor: getStatusColor(center.status) }}
                    >
                      {getStatusLabel(center.status)}
                    </div>
                  </div>

                  <div className="center-details">
                    {center.location && (
                      <div className="detail-row">
                        <svg className="detail-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        </svg>
                        <span className="detail-value">{center.location}</span>
                      </div>
                    )}

                    {center.coordinates && (
                      <div className="detail-row">
                        <svg className="detail-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                        </svg>
                        <span className="detail-value">
                          {center.coordinates.lat.toFixed(4)}, {center.coordinates.lon.toFixed(4)}
                        </span>
                      </div>
                    )}

                    {center.capacity && (
                      <div className="detail-row">
                        <svg className="detail-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                        </svg>
                        <span className="detail-value">
                          Capacity: {center.capacity} persons
                        </span>
                      </div>
                    )}

                    {center.contact && (
                      <div className="detail-row">
                        <svg className="detail-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                        </svg>
                        <span className="detail-value">{center.contact}</span>
                      </div>
                    )}

                    {center.facilities && center.facilities.length > 0 && (
                      <div className="detail-row">
                        <svg className="detail-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                        </svg>
                        <span className="detail-value">
                          {center.facilities.join(', ')}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
