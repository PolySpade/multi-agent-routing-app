'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

/**
 * EvacuationCentersPanel Component
 *
 * Dedicated panel for displaying evacuation centers with detailed information
 * including location, capacity, contact details, and availability status.
 */
export default function EvacuationCentersPanel({ onSelectDestination, onReportIssue }) {
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
          position: relative;
          width: 100%;
          /* max-height controlled by parent scroll container */
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

        .evacuation-panel.collapsed {
          min-height: auto;
          max-height: 80px;
        }

        .panel-header {
          padding: 1.25rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(36, 142, 168, 0.1);
          cursor: pointer;
          user-select: none;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .panel-header:hover {
          background: rgba(36, 142, 168, 0.15);
        }

        .header-content {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .panel-icon {
          font-size: 1.25rem;
          color: #248ea8;
        }

        .panel-title {
          font-size: 1rem;
          font-weight: 700;
          color: white;
          margin: 0;
          letter-spacing: 0.5px;
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

        .status-bar {
          display: flex;
          gap: 0.75rem;
          margin-top: 0.25rem;
          font-size: 0.7rem;
          color: rgba(255, 255, 255, 0.6);
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
          position: relative;
        }

        .center-card:hover {
          background: rgba(255, 255, 255, 0.08);
          transform: translateY(-2px);
        }

        .go-btn {
          position: absolute;
          bottom: 1rem;
          right: 1rem;
          background: rgba(36, 142, 168, 0.2);
          border: 1px solid rgba(36, 142, 168, 0.4);
          color: #7dd3fc;
          padding: 0.2rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          transition: all 0.2s;
        }

        .go-btn:hover {
          background: rgba(36, 142, 168, 0.3);
          border-color: rgba(36, 142, 168, 0.6);
          transform: scale(1.05);
        }

        .go-btn:active {
          transform: scale(0.95);
        }

        .report-btn {
          position: absolute;
          bottom: 1rem;
          right: 5rem;
          background: rgba(139, 92, 246, 0.2);
          border: 1px solid rgba(139, 92, 246, 0.4);
          color: #c4b5fd;
          padding: 0.2rem 0.6rem;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.75rem;
          font-weight: 600;
          transition: all 0.2s;
        }

        .report-btn:hover {
          background: rgba(139, 92, 246, 0.3);
          border-color: rgba(139, 92, 246, 0.6);
        }

        .feedback-top-btn {
          width: 100%;
          padding: 0.5rem;
          border-radius: 8px;
          border: 1px solid rgba(139, 92, 246, 0.3);
          background: rgba(139, 92, 246, 0.15);
          color: #c4b5fd;
          cursor: pointer;
          font-size: 0.8rem;
          font-weight: 600;
          margin-bottom: 0.75rem;
          transition: all 0.2s;
        }

        .feedback-top-btn:hover {
          background: rgba(139, 92, 246, 0.25);
          border-color: rgba(139, 92, 246, 0.5);
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

        @media (max-width: 767px) {
          .evacuation-panel {
            border-radius: 0;
          }
        }
      `}</style>

      {/* Header */}
      <div className="panel-header" onClick={() => setIsPanelCollapsed(!isPanelCollapsed)}>
        <div className="header-content">
          <span className="panel-icon">🏥</span>
          <div>
            <h2 className="panel-title">EVACUATION CENTERS</h2>
            {!isPanelCollapsed && (
              <div className="status-bar">
                <div className="status-item">
                  {evacuationCenters.length} Centers
                </div>
                {lastUpdate && (
                  <div className="status-item">
                    Updated: {lastUpdate.toLocaleTimeString()}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        <button
          className="collapse-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsPanelCollapsed(!isPanelCollapsed);
          }}
          title={isPanelCollapsed ? "Expand Panel" : "Collapse Panel"}
        >
          {isPanelCollapsed ? '▲' : '▼'}
        </button>
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
              {/* Submit Feedback Button */}
              {onReportIssue && (
                <button
                  className="feedback-top-btn"
                  onClick={() => onReportIssue(null)}
                >
                  Submit Evacuation Feedback
                </button>
              )}

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
                  {/* GO Button */}
                  {onSelectDestination && center.coordinates && (
                    <button
                      className="go-btn"
                      onClick={() => {
                        onSelectDestination(
                          center.coordinates.lat,
                          center.coordinates.lon,
                          center.name
                        );
                      }}
                      title={`Set ${center.name} as destination`}
                    >
                      GO
                    </button>
                  )}

                  {/* Report Issue Button */}
                  {onReportIssue && (
                    <button
                      className="report-btn"
                      onClick={() => onReportIssue(center.name)}
                      title={`Report issue at ${center.name}`}
                    >
                      Report
                    </button>
                  )}

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
                          {center.current_occupancy !== undefined && (
                            <span style={{
                              marginLeft: '0.5rem',
                              color: getStatusColor(center.status),
                              fontWeight: 'bold'
                            }}>
                              ({center.current_occupancy}/{center.capacity} occupied - {center.occupancy_percentage}%)
                            </span>
                          )}
                        </span>
                      </div>
                    )}

                    {center.available_slots !== undefined && center.status !== 'available' && (
                      <div className="detail-row">
                        <svg className="detail-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="detail-value" style={{
                          color: center.status === 'full' ? '#ef4444' : '#eab308',
                          fontWeight: '600'
                        }}>
                          {center.status === 'full'
                            ? 'FULL - No available slots'
                            : `${center.available_slots} slots remaining`
                          }
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
