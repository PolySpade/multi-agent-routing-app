/**
 * Graph Risk Visualization Layer for Mapbox
 *
 * Displays road network edges with color-coded risk levels.
 * Fetches GeoJSON data from backend API and renders as Mapbox layer.
 */

import { useEffect, useState, useRef } from 'react';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

/**
 * Get color based on risk score
 * @param {number} riskScore - Risk score from 0.0 to 1.0
 * @returns {string} RGB color string
 */
function getRiskColor(riskScore) {
  if (riskScore < 0.3) {
    // Low risk: Yellow to Light Orange
    return `rgb(255, ${255 - Math.floor(riskScore * 300)}, 0)`;
  } else if (riskScore < 0.6) {
    // Medium risk: Orange
    const intensity = (riskScore - 0.3) / 0.3;
    return `rgb(255, ${165 - Math.floor(intensity * 100)}, 0)`;
  } else {
    // High risk: Dark Orange to Red
    const intensity = (riskScore - 0.6) / 0.4;
    return `rgb(${200 + Math.floor(intensity * 55)}, ${Math.floor((1 - intensity) * 100)}, 0)`;
  }
}

/**
 * GraphRiskLayer Component
 *
 * @param {Object} props
 * @param {Object} props.map - Mapbox map instance
 * @param {boolean} props.visible - Whether layer should be visible
 * @param {number} props.minRisk - Minimum risk threshold (optional)
 * @param {number} props.maxRisk - Maximum risk threshold (optional)
 * @param {number} props.sampleSize - Number of edges to display (optional)
 */
export default function GraphRiskLayer({
  map,
  visible = true,
  minRisk = null,
  maxRisk = null,
  sampleSize = 5000  // Default to 5000 edges for performance
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const layerIdRef = useRef('graph-risk-edges');
  const sourceIdRef = useRef('graph-risk-source');

  /**
   * Fetch graph data from backend API
   */
  const fetchGraphData = async () => {
    if (!map) return;

    setIsLoading(true);
    setError(null);

    try {
      // Build query parameters
      const params = new URLSearchParams();
      if (minRisk !== null) params.append('min_risk', minRisk);
      if (maxRisk !== null) params.append('max_risk', maxRisk);
      if (sampleSize !== null) params.append('sample_size', sampleSize);

      const url = `${BACKEND_API_URL}/api/graph/edges/geojson?${params.toString()}`;
      console.log('Fetching graph data from:', url);

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const geojsonData = await response.json();
      console.log('Received GeoJSON data:', {
        features: geojsonData.features?.length || 0,
        properties: geojsonData.properties
      });

      // Add or update source
      if (map.getSource(sourceIdRef.current)) {
        map.getSource(sourceIdRef.current).setData(geojsonData);
      } else {
        map.addSource(sourceIdRef.current, {
          type: 'geojson',
          data: geojsonData
        });
      }

      // Add layer if it doesn't exist
      if (!map.getLayer(layerIdRef.current)) {
        map.addLayer({
          id: layerIdRef.current,
          type: 'line',
          source: sourceIdRef.current,
          paint: {
            'line-color': [
              'interpolate',
              ['linear'],
              ['get', 'risk_score'],
              0.0, '#FFFF00',  // Yellow (low risk)
              0.3, '#FFA500',  // Orange (medium risk)
              0.6, '#FF6B35',  // Red-orange (high risk)
              1.0, '#DC143C'   // Crimson (critical risk)
            ],
            'line-width': [
              'interpolate',
              ['linear'],
              ['get', 'risk_score'],
              0.0, 1,    // Thin for low risk
              0.6, 2,    // Medium for high risk
              1.0, 3     // Thick for critical risk
            ],
            'line-opacity': 0.7
          },
          layout: {
            'visibility': visible ? 'visible' : 'none'
          }
        });

        // Add click interaction
        map.on('click', layerIdRef.current, (e) => {
          const feature = e.features[0];
          const props = feature.properties;

          new mapboxgl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(`
              <div style="padding: 8px;">
                <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">
                  Road Risk Info
                </h3>
                <p style="margin: 4px 0; font-size: 12px;">
                  <strong>Risk Score:</strong> ${(props.risk_score * 100).toFixed(1)}%
                </p>
                <p style="margin: 4px 0; font-size: 12px;">
                  <strong>Category:</strong> ${props.risk_category}
                </p>
                <p style="margin: 4px 0; font-size: 12px;">
                  <strong>Road Type:</strong> ${props.highway || 'unknown'}
                </p>
              </div>
            `)
            .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', layerIdRef.current, () => {
          map.getCanvas().style.cursor = 'pointer';
        });

        map.on('mouseleave', layerIdRef.current, () => {
          map.getCanvas().style.cursor = '';
        });
      }

      setIsLoading(false);
    } catch (err) {
      console.error('Error fetching graph data:', err);
      setError(err.message);
      setIsLoading(false);
    }
  };

  /**
   * Fetch graph statistics
   */
  const fetchGraphStats = async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/api/graph/statistics`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
        console.log('Graph statistics:', data);
      }
    } catch (err) {
      console.error('Error fetching graph statistics:', err);
    }
  };

  /**
   * Initialize layer when map is ready
   */
  useEffect(() => {
    if (map && map.isStyleLoaded()) {
      fetchGraphData();
      fetchGraphStats();
    }
  }, [map, minRisk, maxRisk, sampleSize]);

  /**
   * Toggle visibility when prop changes
   */
  useEffect(() => {
    if (map && map.getLayer(layerIdRef.current)) {
      map.setLayoutProperty(
        layerIdRef.current,
        'visibility',
        visible ? 'visible' : 'none'
      );
    }
  }, [visible, map]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (map) {
        if (map.getLayer(layerIdRef.current)) {
          map.removeLayer(layerIdRef.current);
        }
        if (map.getSource(sourceIdRef.current)) {
          map.removeSource(sourceIdRef.current);
        }
      }
    };
  }, [map]);

  // Return stats and control functions
  return {
    isLoading,
    error,
    stats,
    refreshData: fetchGraphData,
    refreshStats: fetchGraphStats
  };
}
