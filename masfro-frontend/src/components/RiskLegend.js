'use client';

import { useState } from 'react';

const RISK_LEVELS = [
  {
    range: '0-20%',
    label: 'Very Low',
    color: '#10b981',
    description: 'Safe - No significant flood risk',
    depth: 'Dry or < 6 inches',
    bodyLevel: 'Ankle level',
    icon: '✅',
    action: 'Safe to travel normally'
  },
  {
    range: '20-40%',
    label: 'Low',
    color: '#84cc16',
    description: 'Minor risk - Passable with caution',
    depth: '6-12 inches',
    bodyLevel: 'Below knee',
    icon: '⚠️',
    action: 'Drive with caution'
  },
  {
    range: '40-60%',
    label: 'Moderate',
    color: '#eab308',
    description: 'Moderate risk - Drive slowly',
    depth: '1-2 feet',
    bodyLevel: 'Knee to waist',
    icon: '⚡',
    action: 'Slow down, avoid if possible'
  },
  {
    range: '60-80%',
    label: 'High',
    color: '#f97316',
    description: 'High risk - Dangerous conditions',
    depth: '2-3 feet',
    bodyLevel: 'Waist to chest',
    icon: '🚨',
    action: 'Avoid this route - dangerous'
  },
  {
    range: '80-100%',
    label: 'Critical',
    color: '#ef4444',
    description: 'Critical - Impassable or extremely dangerous',
    depth: '> 3 feet',
    bodyLevel: 'Chest level or higher',
    icon: '🛑',
    action: 'DO NOT TRAVEL - impassable'
  }
];

export default function RiskLegend({ isCollapsed = false }) {
  const [expanded, setExpanded] = useState(!isCollapsed);

  return (
    <div className="risk-legend-container">
      <style jsx>{`
        .risk-legend-container {
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          border-radius: 16px;
          padding: 1rem;
          box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }

        .legend-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
          user-select: none;
          margin-bottom: ${expanded ? '1rem' : '0'};
        }

        .legend-title {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: var(--text-muted);
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .toggle-btn {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 0.25rem;
          font-size: 0.9rem;
          transition: transform 0.2s;
          transform: rotate(${expanded ? '180deg' : '0deg'});
        }

        .legend-content {
          display: ${expanded ? 'flex' : 'none'};
          flex-direction: column;
          gap: 0.75rem;
        }

        .risk-item {
          display: grid;
          grid-template-columns: 24px auto;
          gap: 0.75rem;
          padding: 0.75rem;
          background: rgba(255,255,255,0.03);
          border-radius: 10px;
          border-left: 3px solid;
          transition: all 0.2s;
        }

        .risk-item:hover {
          background: rgba(255,255,255,0.08);
          transform: translateX(2px);
        }

        .risk-icon {
          font-size: 1.2rem;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .risk-details {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .risk-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 0.5rem;
        }

        .risk-label {
          font-weight: 600;
          font-size: 0.9rem;
        }

        .risk-range {
          font-size: 0.7rem;
          opacity: 0.7;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .risk-description {
          font-size: 0.75rem;
          opacity: 0.8;
          line-height: 1.4;
        }

        .depth-info {
          display: flex;
          gap: 0.5rem;
          margin-top: 0.25rem;
          flex-wrap: wrap;
        }

        .depth-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.15rem 0.5rem;
          background: rgba(255,255,255,0.05);
          border-radius: 12px;
          font-size: 0.65rem;
          font-weight: 500;
        }

        .action-text {
          font-size: 0.7rem;
          opacity: 0.7;
          font-style: italic;
          margin-top: 0.25rem;
        }

        .legend-footer {
          margin-top: 0.5rem;
          padding-top: 0.75rem;
          border-top: 1px solid rgba(255,255,255,0.1);
          font-size: 0.65rem;
          opacity: 0.7;
          text-align: center;
        }
      `}</style>

      <div className="legend-header" onClick={() => setExpanded(!expanded)}>
        <div className="legend-title">
          <span>📊</span>
          <span>Flood Risk Legend</span>
        </div>
        <button className="toggle-btn" aria-label={expanded ? 'Collapse' : 'Expand'}>
          ▼
        </button>
      </div>

      <div className="legend-content">
        {RISK_LEVELS.map((level, index) => (
          <div
            key={index}
            className="risk-item"
            style={{ borderLeftColor: level.color }}
          >
            <div className="risk-icon">{level.icon}</div>
            <div className="risk-details">
              <div className="risk-header">
                <span className="risk-label" style={{ color: level.color }}>
                  {level.label}
                </span>
                <span className="risk-range">{level.range}</span>
              </div>
              <div className="risk-description">{level.description}</div>
              <div className="depth-info">
                <span className="depth-badge">
                  💧 {level.depth}
                </span>
                <span className="depth-badge">
                  🧍 {level.bodyLevel}
                </span>
              </div>
              <div className="action-text">{level.action}</div>
            </div>
          </div>
        ))}

        <div className="legend-footer">
          Risk levels calculated from real-time flood data, weather reports, and crowdsourced observations
        </div>
      </div>
    </div>
  );
}
