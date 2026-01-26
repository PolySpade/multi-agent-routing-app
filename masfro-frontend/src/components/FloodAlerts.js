'use client';

import { useState, useEffect } from 'react';

/**
 * FloodAlerts Component
 *
 * Displays real-time critical flood alerts from WebSocket.
 * Shows warnings when river stations reach ALARM or CRITICAL water levels.
 */
export default function FloodAlerts({ alerts, onClear, isConnected }) {
  const [visible, setVisible] = useState(true);
  const [expandedAlerts, setExpandedAlerts] = useState(new Set());

  useEffect(() => {
    // Auto-show alerts panel when new critical alerts arrive
    if (alerts && alerts.length > 0) {
      setVisible(true);
    }
  }, [alerts]);

  const toggleAlert = (alertId) => {
    setExpandedAlerts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(alertId)) {
        newSet.delete(alertId);
      } else {
        newSet.add(alertId);
      }
      return newSet;
    });
  };

  const dismissAlert = (alertId) => {
    // Filter out the dismissed alert
    const remainingAlerts = alerts.filter(alert => alert.id !== alertId);
    if (remainingAlerts.length === 0) {
      onClear();
    }
  };

  if (!visible || !alerts || alerts.length === 0) {
    return null;
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-600 border-red-700';
      case 'alarm':
        return 'bg-orange-500 border-orange-600';
      case 'alert':
        return 'bg-yellow-500 border-yellow-600';
      default:
        return 'bg-blue-500 border-blue-600';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return '🚨';
      case 'alarm':
        return '⚠️';
      case 'alert':
        return '⚡';
      default:
        return 'ℹ️';
    }
  };

  return (
    <div className="fixed top-20 right-4 z-50 max-w-md">
      {/* Connection Status Indicator */}
      <div className="mb-2 flex items-center justify-end space-x-2">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
        <span className="text-xs text-white">
          {isConnected ? 'Live Updates' : 'Disconnected'}
        </span>
      </div>

      {/* Alerts Container */}
      <div className="space-y-2">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`${getSeverityColor(alert.severity)} text-white rounded-lg shadow-lg border-2 overflow-hidden animate-fade-in`}
          >
            {/* Alert Header */}
            <div
              className="p-4 cursor-pointer hover:opacity-90 transition-opacity"
              onClick={() => toggleAlert(alert.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2 flex-1">
                  <span className="text-2xl">{getSeverityIcon(alert.severity)}</span>
                  <div className="flex-1">
                    <h3 className="font-bold text-sm uppercase tracking-wide">
                      {alert.risk_level} FLOOD WARNING
                    </h3>
                    <p className="text-xs opacity-90 mt-1">
                      {alert.station}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs opacity-75">
                    {expandedAlerts.has(alert.id) ? '▼' : '▶'}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      dismissAlert(alert.id);
                    }}
                    className="text-white hover:text-gray-200 text-lg leading-none"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>

            {/* Expanded Alert Details */}
            {expandedAlerts.has(alert.id) && (
              <div className="bg-black bg-opacity-20 p-4 border-t border-white border-opacity-20">
                <p className="text-sm mb-3">
                  {alert.message}
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="opacity-75">Water Level:</span>
                    <p className="font-bold">{alert.water_level}m</p>
                  </div>
                  <div>
                    <span className="opacity-75">Time:</span>
                    <p className="font-bold">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                {alert.action_required && (
                  <div className="mt-3 p-2 bg-white bg-opacity-10 rounded">
                    <p className="text-xs font-bold">
                      ⚡ ACTION REQUIRED: {alert.severity === 'critical' ? 'Evacuate immediately!' : 'Prepare for possible evacuation'}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Clear All Button */}
      {alerts.length > 0 && (
        <button
          onClick={onClear}
          className="mt-2 w-full bg-gray-800 hover:bg-gray-700 text-white text-xs py-2 px-4 rounded transition-colors"
        >
          Clear All ({alerts.length})
        </button>
      )}

      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateX(20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
