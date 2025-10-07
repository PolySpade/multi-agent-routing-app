'use client'; // This directive is necessary for React hooks

import { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';

export default function Home() {
  // State variables to hold our application's data
  const [startPoint, setStartPoint] = useState(null);
  const [endPoint, setEndPoint] = useState(null);
  const [routePath, setRoutePath] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('Click on the map to select a starting point.');

  // Dynamically import the Map component with SSR turned off
  const Map = useMemo(() => dynamic(() => import('@/components/map'), { 
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
          Loading map...
        </div>
      </div>
    ),
    ssr: false 
  }), []);

  // Handle clicks on the map to set start/end points
  const handleMapClick = (latlng) => {
    if (!startPoint) {
      setStartPoint(latlng);
      setMessage('Start point selected. Now click to select a destination.');
    } else if (!endPoint) {
      setEndPoint(latlng);
      setMessage('Destination selected. Click "Find Route" to calculate.');
    }
  };
  
  // Function to call the FastAPI backend
  const handleFindRoute = async () => {
    if (!startPoint || !endPoint) {
      setMessage('Please select both a start and end point on the map.');
      return;
    }
    
    setLoading(true);
    setRoutePath(null); // Clear previous route
    setMessage('Calculating safest route...');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_location: [startPoint.lat, startPoint.lng],
          end_location: [endPoint.lat, endPoint.lng],
        }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      setRoutePath(data.path); // The path should be an array of [lat, lng] tuples
      setMessage(`Route found! Press Reset to try again.`);

    } catch (error) {
      console.error('Failed to fetch route:', error);
      setMessage('Error: Could not calculate route. Is the backend server running?');
    } finally {
      setLoading(false);
    }
  };

  // Reset the selection
  const handleReset = () => {
    setStartPoint(null);
    setEndPoint(null);
    setRoutePath(null);
    setMessage('Click on the map to select a starting point.');
  };

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
        display: 'flex', 
        height: '100vh', 
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        background: '#f8fafc'
      }}>
        <div style={{ 
          width: '350px', 
          padding: '2rem', 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          borderRight: '1px solid #e2e8f0',
          color: 'white',
          boxShadow: '2px 0 10px rgba(0,0,0,0.1)',
          overflow: 'auto'
        }}>
          <div style={{ marginBottom: '2rem' }}>
            <h1 style={{ 
              margin: '0 0 0.5rem 0', 
              fontSize: '2rem', 
              fontWeight: '700',
              background: 'linear-gradient(45deg, #fff, #e2e8f0)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              MAS-FRO
            </h1>
            <p style={{ 
              margin: '0', 
              fontSize: '1.1rem', 
              opacity: '0.9',
              fontWeight: '300'
            }}>
              🌊 Smart Flood Route Optimization
            </p>
          </div>
          
          <hr style={{ 
            margin: '1.5rem 0', 
            border: 'none', 
            height: '1px', 
            background: 'rgba(255,255,255,0.2)' 
          }}/>
          
          <div style={{ 
            background: 'rgba(255,255,255,0.1)', 
            borderRadius: '12px', 
            padding: '1.5rem',
            marginBottom: '1.5rem',
            backdropFilter: 'blur(10px)'
          }}>
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                marginBottom: '0.5rem' 
              }}>
                <span style={{ marginRight: '8px', fontSize: '1.2rem' }}>📍</span>
                <strong style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Start Point
                </strong>
              </div>
              <p style={{ 
                margin: '0', 
                padding: '0.5rem', 
                background: startPoint ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255,255,255,0.1)',
                borderRadius: '6px',
                fontSize: '0.9rem',
                fontFamily: 'monospace'
              }}>
                {startPoint ? `${startPoint.lat.toFixed(4)}, ${startPoint.lng.toFixed(4)}` : 'Not selected'}
              </p>
            </div>
            
            <div>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                marginBottom: '0.5rem' 
              }}>
                <span style={{ marginRight: '8px', fontSize: '1.2rem' }}>🎯</span>
                <strong style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Destination
                </strong>
              </div>
              <p style={{ 
                margin: '0', 
                padding: '0.5rem', 
                background: endPoint ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255,255,255,0.1)',
                borderRadius: '6px',
                fontSize: '0.9rem',
                fontFamily: 'monospace'
              }}>
                {endPoint ? `${endPoint.lat.toFixed(4)}, ${endPoint.lng.toFixed(4)}` : 'Not selected'}
              </p>
            </div>
          </div>
          
          <button 
            onClick={handleFindRoute} 
            disabled={loading || !startPoint || !endPoint} 
            style={{ 
              width: '100%', 
              padding: '1rem', 
              background: (loading || !startPoint || !endPoint) 
                ? 'rgba(255,255,255,0.3)' 
                : 'linear-gradient(45deg, #10b981, #059669)',
              color: 'white', 
              border: 'none', 
              borderRadius: '10px', 
              cursor: (loading || !startPoint || !endPoint) ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              fontWeight: '600',
              transition: 'all 0.3s ease',
              boxShadow: (loading || !startPoint || !endPoint) 
                ? 'none' 
                : '0 4px 15px rgba(16, 185, 129, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            {loading ? (
              <>
                <div style={{ 
                  width: '16px', 
                  height: '16px', 
                  border: '2px solid rgba(255,255,255,0.3)', 
                  borderTop: '2px solid white',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }}></div>
                Calculating...
              </>
            ) : (
              <>
                🚗 Find Safest Route
              </>
            )}
          </button>
          
          <button 
            onClick={handleReset} 
            style={{ 
              width: '100%', 
              padding: '0.75rem', 
              background: 'rgba(255,255,255,0.2)', 
              color: 'white', 
              border: '1px solid rgba(255,255,255,0.3)', 
              borderRadius: '8px', 
              cursor: 'pointer', 
              marginTop: '0.75rem',
              fontSize: '0.9rem',
              fontWeight: '500',
              transition: 'all 0.3s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = 'rgba(255,255,255,0.3)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'rgba(255,255,255,0.2)';
            }}
          >
            🔄 Reset Selection
          </button>

          <div style={{ 
            marginTop: '2rem', 
            paddingTop: '1.5rem', 
            borderTop: '1px solid rgba(255,255,255,0.2)'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              marginBottom: '0.75rem' 
            }}>
              <span style={{ marginRight: '8px', fontSize: '1.1rem' }}>ℹ️</span>
              <strong style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Status
              </strong>
            </div>
            <div style={{ 
              background: 'rgba(255,255,255,0.1)', 
              borderRadius: '8px', 
              padding: '1rem',
              backdropFilter: 'blur(5px)'
            }}>
              <p style={{ 
                margin: '0', 
                fontSize: '0.9rem', 
                lineHeight: '1.4',
                animation: loading ? 'pulse 2s infinite' : 'none'
              }}>
                {message}
              </p>
            </div>
          </div>
        </div>
        
        <div style={{ 
          flex: 1, 
          position: 'relative',
          overflow: 'hidden'
        }}>
          <Map 
            startPoint={startPoint} 
            endPoint={endPoint}
            routePath={routePath}
            onMapClick={handleMapClick} 
          />
        </div>
      </main>
    </>
  );
}