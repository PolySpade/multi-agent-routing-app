'use client'; // This directive is necessary for React hooks

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import LocationSearch from '@/components/LocationSearch';
import { findRoute } from '@/utils/routingService';

const formatDistance = (meters) => {
  if (meters == null) return '—';
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)} km`;
  }
  return `${Math.round(meters)} m`;
};

const formatDuration = (seconds) => {
  if (seconds == null) return '—';
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes} min`;
};

export default function Home() {
  // State variables to hold our application's data
  const [startPoint, setStartPoint] = useState(null);
  const [endPoint, setEndPoint] = useState(null);
  const [routePath, setRoutePath] = useState(null);
  const [routeMeta, setRouteMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('Click "Select Start Point" button, then click on the map.');
  const [selectionMode, setSelectionMode] = useState(null); // 'start', 'end', or null
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);

  // Dynamically import the MapboxMap component with SSR turned off
  const MapboxMap = useMemo(() => dynamic(() => import('@/components/MapboxMap'), { 
    loading: () => (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100%',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        fontSize: '18px'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            border: '4px solid rgba(255,255,255,0.3)', 
            borderTop: '4px solid white',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 10px'
          }}></div>
          Loading Mapbox...
        </div>
      </div>
    ),
    ssr: false 
  }), []);

  // Handle location selection from search
  const handleLocationSelect = (location, type) => {
    console.log(`${type} location selected:`, location); // Debug log
    
    if (type === 'start') {
      setStartPoint({ lat: location.lat, lng: location.lng });
      setMessage('Start point selected from search. Click "Select Destination" or search for destination.');
    } else if (type === 'end') {
      setEndPoint({ lat: location.lat, lng: location.lng });
      setMessage('Destination selected from search. Click "Find Route" to calculate the safest route.');
    }
  };

  // Handle clicks on the map based on selection mode
  const handleMapClick = (latlng) => {
    console.log('Map clicked:', latlng, 'Selection mode:', selectionMode); // Debug log
    
    if (selectionMode === 'start') {
      setStartPoint(latlng);
      setSelectionMode(null);
      setMessage('Start point selected. Click "Select Destination" to choose your destination.');
    } else if (selectionMode === 'end') {
      setEndPoint(latlng);
      setSelectionMode(null);
      setMessage('Destination selected. Click "Find Route" to calculate the safest route.');
    } else {
      setMessage('Please select a mode first using the buttons below.');
    }
  };

  // Functions to enter selection modes
  const handleSelectStartMode = () => {
    setSelectionMode('start');
    setMessage('Click on the map to select your starting point.');
    console.log('Start mode activated'); // Debug log
  };

  const handleSelectEndMode = () => {
    if (!startPoint) {
      setMessage('Please select a start point first.');
      return;
    }
    setSelectionMode('end');
    setMessage('Click on the map to select your destination.');
    console.log('End mode activated'); // Debug log
  };

  // Function to call the FastAPI backend
  const handleFindRoute = async () => {
    await findRoute(startPoint, endPoint, setRoutePath, setRouteMeta, setMessage, setLoading);
  };

  // Reset the selection
  const handleReset = () => {
    setStartPoint(null);
    setEndPoint(null);
    setRoutePath(null);
    setRouteMeta(null);
    setSelectionMode(null);
    setMessage('Click "Select Start Point" button, then click on the map.');
  };

  const handleSwapPoints = () => {
    if (!startPoint || !endPoint) {
      setMessage('You need both a start and destination to swap.');
      return;
    }

    setStartPoint(endPoint);
    setEndPoint(startPoint);
    setRoutePath(null);
    setRouteMeta(null);
    setMessage('Start and destination swapped. Click "Find Route" to recalculate.');
  };

  const handleUseCurrentLocation = useCallback(() => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      setMessage('Geolocation is not supported in this browser.');
      return;
    }

    setMessage('Fetching your current location...');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        const coords = { lat: latitude, lng: longitude };
        setStartPoint(coords);
        setSelectionMode(null);
        setMessage('Current location set as start point. Select your destination.');
      },
      (error) => {
        console.error('Error getting current location:', error);
        setMessage('Unable to fetch current location. Please allow location access or choose manually.');
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 1000 * 60,
      }
    );
  }, []);
  const handleShowInstructions = () => {
    setMessage('Tip: Select start, then destination, and press “Find Safest Route” when both are set.');
  };

  const togglePanel = () => {
    setIsPanelCollapsed((prev) => !prev);
  };

  const formatCoordinate = (point) => {
    if (!point) return 'Not selected';
    return `${point.lat.toFixed(4)}°, ${point.lng.toFixed(4)}°`;
  };

  const hasRoute = Array.isArray(routePath) && routePath.length > 0;
  const panelWidth = isPanelCollapsed ? '0px' : '380px';

  return (
    <>
      <style jsx global>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
        
        body {
          margin: 0;
          padding: 0;
        }
      `}</style>
      
      <main style={{
        display: 'grid',
        gridTemplateColumns: `minmax(0, ${panelWidth}) 1fr`,
        transition: 'grid-template-columns 0.4s ease',
        minHeight: '100vh',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        background: 'linear-gradient(135deg, #0f172a, #312e81)'
      }}>
        <aside style={{
          overflow: 'hidden',
          opacity: isPanelCollapsed ? 0 : 1,
          transition: 'opacity 0.3s ease',
          background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%)',
          borderRight: isPanelCollapsed ? 'none' : '1px solid rgba(226, 232, 240, 0.25)',
          color: 'white',
          boxShadow: isPanelCollapsed ? 'none' : '2px 0 18px rgba(15, 23, 42, 0.45)'
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            padding: isPanelCollapsed ? '0' : '2.25rem 2rem',
            gap: '1.75rem'
          }}>
            {!isPanelCollapsed && (
              <header style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h1 style={{
                      margin: '0',
                      fontSize: '2.25rem',
                      fontWeight: 700,
                      background: 'linear-gradient(45deg, #ffffff, #e2e8f0)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      backgroundClip: 'text'
                    }}>
                      MAS-FRO
                    </h1>
                    <p style={{
                      margin: '0',
                      fontSize: '1rem',
                      letterSpacing: '0.1rem',
                      textTransform: 'uppercase',
                      opacity: 0.85,
                      fontWeight: 500
                    }}>
                      Smart Flood Routing
                    </p>
                  </div>
                  <button
                    onClick={togglePanel}
                    style={{
                      background: 'rgba(15, 23, 42, 0.25)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: 'white',
                      borderRadius: '999px',
                      padding: '0.4rem 0.9rem',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem'
                    }}
                  >
                    Hide
                    <span aria-hidden="true">⤴</span>
                  </button>
                </div>
                <p style={{
                  margin: '0',
                  fontSize: '0.95rem',
                  opacity: 0.85,
                  lineHeight: 1.5
                }}>
                  Define safe origin and destination either via search or by selecting straight on the map, then compute the safest flood-aware route.
                </p>
              </header>
            )}

            {!isPanelCollapsed && (
              <section style={{
                background: 'rgba(255,255,255,0.12)',
                borderRadius: '18px',
                padding: '1.5rem',
                boxShadow: '0 10px 35px rgba(15, 23, 42, 0.25)',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem'
              }}>
                <div>
                  <h3 style={{
                    margin: 0,
                    fontSize: '0.95rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08rem',
                    color: 'rgba(226, 232, 240, 0.8)'
                  }}>
                    Search Locations
                  </h3>
                </div>
                <LocationSearch
                  onLocationSelect={(location) => handleLocationSelect(location, 'start')}
                  placeholder="Search start address..."
                  type="start"
                />
                <LocationSearch
                  onLocationSelect={(location) => handleLocationSelect(location, 'end')}
                  placeholder="Search destination..."
                  type="end"
                />
                <button
                  onClick={handleUseCurrentLocation}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.45rem',
                    background: 'rgba(15, 23, 42, 0.25)',
                    border: '1px solid rgba(255,255,255,0.35)',
                    color: 'white',
                    padding: '0.65rem 1rem',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    transition: 'all 0.3s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(15, 23, 42, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(15, 23, 42, 0.25)';
                  }}
                >
                  📡 Use current location for start
                </button>
              </section>
            )}

            {!isPanelCollapsed && (
              <section style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
                background: 'rgba(15, 23, 42, 0.25)',
                borderRadius: '18px',
                padding: '1.5rem',
                border: '1px solid rgba(255,255,255,0.15)'
              }}>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    onClick={handleSelectStartMode}
                    disabled={loading}
                    style={{
                      flex: 1,
                      padding: '0.85rem',
                      borderRadius: '12px',
                      border: 'none',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      background: selectionMode === 'start'
                        ? 'linear-gradient(135deg, rgba(34,197,94,0.7), rgba(22,163,74,0.9))'
                        : startPoint
                          ? 'rgba(34, 197, 94, 0.25)'
                          : 'rgba(59, 130, 246, 0.45)',
                      color: 'white',
                      boxShadow: selectionMode === 'start' ? '0 6px 15px rgba(34,197,94,0.3)' : 'none',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    {startPoint ? '✅ Start Set' : '📍 Select Start'}
                  </button>
                  <button
                    onClick={handleSelectEndMode}
                    disabled={loading || !startPoint}
                    style={{
                      flex: 1,
                      padding: '0.85rem',
                      borderRadius: '12px',
                      border: 'none',
                      cursor: (loading || !startPoint) ? 'not-allowed' : 'pointer',
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      background: selectionMode === 'end'
                        ? 'linear-gradient(135deg, rgba(244,63,94,0.78), rgba(220,38,38,0.9))'
                        : endPoint
                          ? 'rgba(244, 63, 94, 0.25)'
                          : (!startPoint ? 'rgba(148,163,184,0.35)' : 'rgba(244, 114, 182, 0.35)'),
                      color: 'white',
                      boxShadow: selectionMode === 'end' ? '0 6px 15px rgba(244,63,94,0.3)' : 'none',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    {endPoint ? '✅ Destination Set' : '🎯 Select Destination'}
                  </button>
                </div>

                {selectionMode && (
                  <div style={{
                    padding: '0.65rem 0.75rem',
                    borderRadius: '10px',
                    fontSize: '0.9rem',
                    textAlign: 'center',
                    border: '1px solid rgba(34,197,94,0.35)',
                    background: 'rgba(34, 197, 94, 0.18)'
                  }}>
                    {selectionMode === 'start' ? '🖱️ Click the map to set your start point.' : '🖱️ Click the map to set your destination.'}
                  </div>
                )}

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                  gap: '0.75rem'
                }}>
                  <div style={{
                    padding: '0.75rem',
                    borderRadius: '12px',
                    background: startPoint ? 'rgba(34,197,94,0.2)' : 'rgba(148,163,184,0.2)',
                    backdropFilter: 'blur(6px)'
                  }}>
                    <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05rem', opacity: 0.7 }}>Start</div>
                    <div style={{ fontFamily: 'monospace', fontSize: '0.95rem', marginTop: '0.4rem' }}>
                      {formatCoordinate(startPoint)}
                    </div>
                  </div>
                  <div style={{
                    padding: '0.75rem',
                    borderRadius: '12px',
                    background: endPoint ? 'rgba(244,63,94,0.2)' : 'rgba(148,163,184,0.2)',
                    backdropFilter: 'blur(6px)'
                  }}>
                    <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05rem', opacity: 0.7 }}>Destination</div>
                    <div style={{ fontFamily: 'monospace', fontSize: '0.95rem', marginTop: '0.4rem' }}>
                      {formatCoordinate(endPoint)}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <button
                    onClick={handleSwapPoints}
                    style={{
                      flex: 1,
                      minWidth: '140px',
                      padding: '0.65rem',
                      borderRadius: '10px',
                      border: '1px solid rgba(255,255,255,0.3)',
                      background: 'rgba(255,255,255,0.18)',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      fontWeight: 600
                    }}
                  >
                    🔁 Swap Start & End
                  </button>
                  <button
                    onClick={handleReset}
                    style={{
                      flex: 1,
                      minWidth: '140px',
                      padding: '0.65rem',
                      borderRadius: '10px',
                      border: '1px solid rgba(255,255,255,0.3)',
                      background: 'rgba(15,23,42,0.2)',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      fontWeight: 600
                    }}
                  >
                    🔄 Reset Selection
                  </button>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent:'center'}}>
                  <button
                    onClick={handleFindRoute}
                    disabled={loading || !startPoint || !endPoint}
                    style={{
                      padding: '0.95rem',
                      borderRadius: '12px',
                      border: 'none',
                      cursor: (loading || !startPoint || !endPoint) ? 'not-allowed' : 'pointer',
                      fontSize: '1rem',
                      fontWeight: 700,
                      background: (loading || !startPoint || !endPoint)
                        ? 'rgba(226,232,240,0.3)'
                        : 'linear-gradient(135deg, #22c55e, #16a34a)',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.6rem',
                      boxShadow: (loading || !startPoint || !endPoint)
                        ? 'none'
                        : '0 12px 28px rgba(34,197,94,0.35)'
                    }}
                  >
                    {loading ? (
                      <>
                        <div style={{
                          width: '18px',
                          height: '18px',
                          border: '3px solid rgba(255,255,255,0.3)',
                          borderTop: '3px solid white',
                          borderRadius: '50%',
                          animation: 'spin 1s linear infinite'
                        }} />
                        Calculating...
                      </>
                    ) : (
                      <>
                        🚗 Find Safest Route
                      </>
                    )}
                  </button>
                </div>
              </section>
            )}

            {!isPanelCollapsed && (
              <section style={{
                marginTop: 'auto',
                background: 'rgba(15, 23, 42, 0.3)',
                borderRadius: '16px',
                padding: '1.4rem',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.8rem' }}>
                  <span style={{ fontSize: '1rem' }}>ℹ️</span>
                  <strong style={{ fontSize: '0.95rem', letterSpacing: '0.05rem', textTransform: 'uppercase' }}>
                    Status
                  </strong>
                </div>
                <p style={{
                  margin: 0,
                  fontSize: '0.95rem',
                  lineHeight: 1.5,
                  animation: loading ? 'pulse 2s infinite' : 'none'
                }}>
                  {message}
                </p>
                {routeMeta && (
                  <div style={{
                    marginTop: '1rem',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                    gap: '0.6rem',
                    background: 'rgba(15, 23, 42, 0.45)',
                    borderRadius: '14px',
                    padding: '0.9rem',
                    border: '1px solid rgba(255,255,255,0.15)'
                  }}>
                    <div>
                      <div style={{ fontSize: '0.75rem', letterSpacing: '0.06rem', textTransform: 'uppercase', opacity: 0.75 }}>Est. Duration</div>
                      <strong style={{ fontSize: '1.05rem' }}>{formatDuration(routeMeta.duration)}</strong>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', letterSpacing: '0.06rem', textTransform: 'uppercase', opacity: 0.75 }}>Distance</div>
                      <strong style={{ fontSize: '1.05rem' }}>{formatDistance(routeMeta.distance)}</strong>
                    </div>
                    <div style={{ gridColumn: 'span 2', fontSize: '0.78rem', opacity: 0.7 }}>
                      Route source: {routeMeta.provider === 'backend' ? 'MAS-FRO backend' : 'Mapbox Directions (placeholder)'}
                    </div>
                  </div>
                )}
              </section>
            )}

            {isPanelCollapsed && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                padding: '1rem'
              }}>
                <button
                  onClick={togglePanel}
                  style={{
                    background: 'rgba(255,255,255,0.15)',
                    border: '1px solid rgba(255,255,255,0.3)',
                    color: 'white',
                    borderRadius: '999px',
                    padding: '0.6rem 1rem',
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  Show controls
                </button>
              </div>
            )}
          </div>
        </aside>

        <section style={{
          position: 'relative',
          minHeight: '100vh',
          overflow: 'hidden'
        }}>
          <MapboxMap
            startPoint={startPoint}
            endPoint={endPoint}
            routePath={routePath}
            onMapClick={handleMapClick}
            panelCollapsed={isPanelCollapsed}
          />

          <div style={{
            position: 'absolute',
            top: '1.25rem',
            right: '1.25rem',
            padding: '0.85rem 1.1rem',
            borderRadius: '14px',
            background: 'rgba(15, 23, 42, 0.65)',
            color: 'white',
            boxShadow: '0 12px 30px rgba(15, 23, 42, 0.35)',
            maxWidth: '320px',
            backdropFilter: 'blur(12px)'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '0.4rem'
            }}>
              <strong style={{ fontSize: '0.95rem', letterSpacing: '0.05rem', textTransform: 'uppercase' }}>
                Route status
              </strong>
              <span style={{
                fontSize: '0.75rem',
                padding: '0.15rem 0.5rem',
                borderRadius: '999px',
                background: hasRoute ? 'rgba(34,197,94,0.35)' : 'rgba(148,163,184,0.35)'
              }}>
                {hasRoute ? 'Active' : 'Pending'}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: 1.4 }}>
              {hasRoute
                ? 'Safest path plotted on map. Review the blue route overlay before dispatch.'
                : 'Set both start and destination to unlock flood-optimized routing.'}
            </p>
            {routeMeta && (
              <div style={{
                marginTop: '0.75rem',
                display: 'grid',
                gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                gap: '0.5rem',
                fontSize: '0.8rem',
                background: 'rgba(15,23,42,0.35)',
                padding: '0.65rem',
                borderRadius: '10px',
                border: '1px solid rgba(255,255,255,0.12)'
              }}>
                <div>
                  <div style={{ opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.05rem' }}>Distance</div>
                  <strong style={{ fontSize: '0.95rem' }}>{formatDistance(routeMeta.distance)}</strong>
                </div>
                <div>
                  <div style={{ opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.05rem' }}>ETA</div>
                  <strong style={{ fontSize: '0.95rem' }}>{formatDuration(routeMeta.duration)}</strong>
                </div>
                <div style={{ gridColumn: 'span 2', opacity: 0.75 }}>
                  Source: {routeMeta.provider === 'backend' ? 'MAS-FRO backend' : 'Mapbox Directions (placeholder)'}
                </div>
              </div>
            )}
          </div>

          {isPanelCollapsed && (
            <button
              onClick={togglePanel}
              style={{
                position: 'absolute',
                top: '1.5rem',
                left: '1.5rem',
                background: 'rgba(15,23,42,0.7)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: 'white',
                borderRadius: '999px',
                padding: '0.6rem 1.05rem',
                cursor: 'pointer',
                fontSize: '0.85rem'
              }}
            >
              Show controls
            </button>
          )}
        </section>
      </main>
    </>
  );
}