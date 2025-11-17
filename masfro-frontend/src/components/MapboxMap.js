import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import shp from 'shpjs';
import { fromUrl, fromBlob } from 'geotiff';
import proj4 from 'proj4';
import { useWebSocket } from '../hooks/useWebSocket';
import FloodAlerts from './FloodAlerts';

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:3001';

// Define projections for coordinate conversion
// EPSG:3857 is Web Mercator, used by many web maps and found in your GeoTIFF
// EPSG:4326 is WGS 84, the standard lat/lng coordinate system
proj4.defs("EPSG:3857", "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs");
proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");

export default function MapboxMap({ startPoint, endPoint, routePath, onMapClick, onLocationSearch, showTraffic = true, panelCollapsed = false, selectionMode = null }) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const startMarkerRef = useRef(null);
  const endMarkerRef = useRef(null);
  const initialCenterRef = useRef(startPoint ? [startPoint.lng, startPoint.lat] : [121.0943, 14.6507]);
  const initialZoomRef = useRef(startPoint ? 12 : 10);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [boundaryFeature, setBoundaryFeature] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [floodTimeStep, setFloodTimeStep] = useState(18); //modify this to one if you wanna test everything
  const [returnPeriod, setReturnPeriod] = useState('rr01');
  const [floodEnabled, setFloodEnabled] = useState(false);
  const onMapClickRef = useRef(onMapClick);
  const selectionModeRef = useRef(selectionMode);

  // WebSocket connection for real-time flood updates and alerts
  const {
    isConnected,
    floodData,
    criticalAlerts,
    schedulerStatus,
    clearAlerts
  } = useWebSocket();

  // Log WebSocket connection status
  useEffect(() => {
    console.log('WebSocket connection status:', isConnected ? 'Connected ✅' : 'Disconnected ❌');
  }, [isConnected]);

  // Log when new flood data arrives via WebSocket
  useEffect(() => {
    if (floodData) {
      console.log('🌊 Received real-time flood data update:', floodData);
    }
  }, [floodData]);

  useEffect(() => {
    onMapClickRef.current = onMapClick;
  }, [onMapClick]);

  useEffect(() => {
    selectionModeRef.current = selectionMode;
  }, [selectionMode]);

  useEffect(() => {
    if (!MAPBOX_TOKEN) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    mapRef.current = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11', //navigation-night-v1
      center: initialCenterRef.current,
      zoom: initialZoomRef.current,
    });

    mapRef.current.on('load', () => {
      setIsMapLoaded(true);

      // === GRAPH RISK LAYER - Load after map is ready ===
      console.log('🔄 Loading graph risk visualization...');

      // Fetch road risk data from backend (no sample_size = ALL edges)
      fetch('http://localhost:8000/api/graph/edges/geojson')
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
          return response.json();
        })
        .then(geojsonData => {
          console.log('✅ Loaded graph data:', {
            totalEdges: geojsonData.features.length,
            sampled: geojsonData.properties?.sampled
          });

          // Store graph data in state to be processed when boundary is available
          setGraphData(geojsonData);
        })
        .catch(error => {
          console.error('❌ Error loading graph risk data:', error);
          console.error('Make sure backend is running: uvicorn app.main:app --reload');
        });
    });

    // Add general map click handler for selecting start/end points
    mapRef.current.on('click', (e) => {
      console.log('Mapbox click event:', e.lngLat);
      const coords = { lat: e.lngLat.lat, lng: e.lngLat.lng };
      console.log('Calling onMapClick with:', coords);
      const clickHandler = onMapClickRef.current;
      if (clickHandler) {
        clickHandler(coords);
      } else {
        console.warn('onMapClick handler is not defined');
      }
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
      }
    };
  }, []);

  // Update graph visualization when boundary or graph data changes
  useEffect(() => {
    if (!mapRef.current || !isMapLoaded || !graphData) return;

    // Helper function: Point-in-polygon check using ray casting
    const isPointInPolygon = (lng, lat, polygon) => {
      if (!polygon) return true;
      let inside = false;
      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i][0], yi = polygon[i][1];
        const xj = polygon[j][0], yj = polygon[j][1];
        const intersect = ((yi > lat) !== (yj > lat)) &&
          (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
      }
      return inside;
    };

    // Get boundary polygon for clipping
    let boundaryRing = null;
    if (boundaryFeature?.geometry) {
      const geom = boundaryFeature.geometry;
      boundaryRing = geom.type === 'Polygon'
        ? geom.coordinates[0]
        : geom.coordinates[0][0];
      console.log('🗺️ Clipping graph edges to boundary with', boundaryRing.length, 'points');
    }

    // Filter edges: keep only if BOTH endpoints are within boundary (strict clipping)
    const filteredFeatures = graphData.features.filter(feature => {
      if (!boundaryRing) return true; // No boundary = show all

      const coords = feature.geometry.coordinates;
      // LineString: check if both start AND end points are within boundary
      if (coords.length >= 2) {
        const startPoint = coords[0];
        const endPoint = coords[coords.length - 1];
        const startInside = isPointInPolygon(startPoint[0], startPoint[1], boundaryRing);
        const endInside = isPointInPolygon(endPoint[0], endPoint[1], boundaryRing);

        // Keep edge only if BOTH endpoints are inside boundary (stricter clipping)
        return startInside && endInside;
      }
      return true;
    });

    console.log(`✂️ Filtered graph edges: ${graphData.features.length} → ${filteredFeatures.length} (removed ${graphData.features.length - filteredFeatures.length} edges outside boundary)`);

    const filteredData = {
      type: 'FeatureCollection',
      features: filteredFeatures
    };

    // Remove existing graph layer and source if they exist
    if (mapRef.current.getLayer('graph-risk-edges')) {
      mapRef.current.removeLayer('graph-risk-edges');
    }
    if (mapRef.current.getSource('graph-risk-source')) {
      mapRef.current.removeSource('graph-risk-source');
    }

    // Add GeoJSON source
    mapRef.current.addSource('graph-risk-source', {
      type: 'geojson',
      data: filteredData,
      tolerance: 0.5  // Simplify for better performance
    });

    // Find first symbol layer (labels) to insert our layer before it
    const layers = mapRef.current.getStyle().layers;
    let firstSymbolId;
    for (const layer of layers) {
      if (layer.type === 'symbol') {
        firstSymbolId = layer.id;
        break;
      }
    }

    // Add the risk visualization layer
    mapRef.current.addLayer({
      id: 'graph-risk-edges',
      type: 'line',
      source: 'graph-risk-source',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
        'visibility': 'visible'  // Make sure it's visible!
      },
      paint: {
        // Color based on risk score
        'line-color': [
          'interpolate',
          ['linear'],
          ['get', 'risk_score'],
          0.0, '#248ea8',   // Blue - safe
          0.3, '#FFA500',   // Orange - caution
          0.6, '#FF6347',   // Tomato - danger
          1.0, 'rgba(110, 17, 0, 1)'    // Dark red - critical
        ],
        // Width based on risk score (thicker = more dangerous)
        'line-width': [
          'interpolate',
          ['linear'],
          ['get', 'risk_score'],
          0.0, 2,
          0.6, 3,
          1.0, 4
        ],
        // Opacity
        'line-opacity': 0.4
      }
    }, firstSymbolId);  // Insert before labels so text is readable

    console.log('✅ Graph risk layer added successfully!');
    console.log('📊 You should see colored roads on the map now');

    // Add click handler for road details (only once)
    if (!mapRef.current._graphClickHandlerAdded) {
      mapRef.current.on('click', 'graph-risk-edges', (e) => {
        // Stop propagation to prevent general map click from firing
        e.originalEvent.stopPropagation();

        // Don't show popup if we're in selection mode (selecting start/end points)
        if (selectionModeRef.current) {
          return;
        }

        const feature = e.features[0];
        const props = feature.properties;

        new mapboxgl.Popup()
          .setLngLat(e.lngLat)
          .setHTML(`
            <div style="padding: 10px; font-family: sans-serif;">
              <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold; color: #333;">
                🛣️ Road Risk Info
              </h3>
              <p style="margin: 4px 0; font-size: 12px; color: #666;">
                <strong>Risk Level:</strong> ${(props.risk_score * 100).toFixed(1)}%
              </p>
              <p style="margin: 4px 0; font-size: 12px; color: #666;">
                <strong>Category:</strong>
                <span style="color: ${
                  props.risk_category === 'low' ? '#4CAF50' :
                  props.risk_category === 'medium' ? '#FF9800' :
                  '#F44336'
                }; font-weight: bold;">
                  ${props.risk_category.toUpperCase()}
                </span>
              </p>
              <p style="margin: 4px 0; font-size: 12px; color: #666;">
                <strong>Road Type:</strong> ${props.highway || 'unknown'}
              </p>
            </div>
          `)
          .addTo(mapRef.current);
      });

      // Change cursor on hover
      mapRef.current.on('mouseenter', 'graph-risk-edges', () => {
        mapRef.current.getCanvas().style.cursor = 'pointer';
      });

      mapRef.current.on('mouseleave', 'graph-risk-edges', () => {
        mapRef.current.getCanvas().style.cursor = '';
      });

      mapRef.current._graphClickHandlerAdded = true;
    }
  }, [isMapLoaded, graphData, boundaryFeature]);

  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) return;

    const resizeMap = () => {
      if (mapRef.current) {
        mapRef.current.resize();
      }
    };

    resizeMap();

    let observer;
    const container = mapContainerRef.current;

    if (typeof ResizeObserver !== 'undefined' && container) {
      observer = new ResizeObserver(() => resizeMap());
      observer.observe(container);
    } else {
      window.addEventListener('resize', resizeMap);
    }

    return () => {
      if (observer && container) {
        observer.unobserve(container);
        observer.disconnect();
      } else {
        window.removeEventListener('resize', resizeMap);
      }
    };
  }, [isMapLoaded]);

  useEffect(() => {
    if (isMapLoaded && mapRef.current) {
      mapRef.current.resize();
    }
  }, [panelCollapsed, isMapLoaded]);

  // Google Places API search function
  const searchLocation = async (query) => {
    if (!GOOGLE_MAPS_API_KEY || !query) return null;

    try {
      const response = await fetch(
        `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(query + ', Marikina City, Philippines')}&key=${GOOGLE_MAPS_API_KEY}`
      );
      
      const data = await response.json();
      
      if (data.results && data.results.length > 0) {
        const location = data.results[0].geometry.location;
        return {
          lat: location.lat,
          lng: location.lng,
          address: data.results[0].formatted_address
        };
      }
      return null;
    } catch (error) {
      console.error('Error searching location:', error);
      return null;
    }
  };

  // Expose search function to parent component
  useEffect(() => {
    if (onLocationSearch) {
      onLocationSearch(searchLocation);
    }
  }, [onLocationSearch]);

  useEffect(() => {
    if (!mapRef.current || !isMapLoaded) return;

    // Remove previous route layer and source if they exist
    if (mapRef.current.getLayer('route')) {
      mapRef.current.removeLayer('route');
    }
    if (mapRef.current.getSource('route')) {
      mapRef.current.removeSource('route');
    }

    // Remove previous markers if they exist
    if (startMarkerRef.current) {
      startMarkerRef.current.remove();
      startMarkerRef.current = null;
    }
    if (endMarkerRef.current) {
      endMarkerRef.current.remove();
      endMarkerRef.current = null;
    }

    // Add start marker
    if (startPoint) {
      startMarkerRef.current = new mapboxgl.Marker({ color: 'green' })
        .setLngLat([startPoint.lng, startPoint.lat])
        .addTo(mapRef.current);

      // Gently center map on start point without changing zoom level when no other context is set
      if (!endPoint && (!routePath || routePath.length === 0)) {
        const currentZoom = mapRef.current.getZoom();
        mapRef.current.easeTo({
          center: [startPoint.lng, startPoint.lat],
          zoom: currentZoom,
          duration: 800,
          easing: (t) => t,
          essential: true,
        });
      }
    }

    // Add end marker
    if (endPoint) {
      endMarkerRef.current = new mapboxgl.Marker({ color: 'red' })
        .setLngLat([endPoint.lng, endPoint.lat])
        .addTo(mapRef.current);
      
      // If both points exist, fit bounds to show both
      if (startPoint) {
        const bounds = new mapboxgl.LngLatBounds();
        bounds.extend([startPoint.lng, startPoint.lat]);
        bounds.extend([endPoint.lng, endPoint.lat]);
        mapRef.current.fitBounds(bounds, { padding: 50 });
      }
    }

    // Add route line
    if (routePath && Array.isArray(routePath) && routePath.length > 0) {
      // Handle different coordinate formats from backend
      const coordinates = routePath.map((pt) => {
        if (Array.isArray(pt)) {
          return [pt[1], pt[0]]; // Convert [lat, lng] to [lng, lat]
        }
        return [pt.lng, pt.lat];
      });

      mapRef.current.addSource('route', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: coordinates,
          },
        },
      });
      mapRef.current.addLayer({
        id: 'route',
        type: 'line',
        source: 'route',
        paint: {
          'line-color': '#76a9ff',
          'line-width': 4,
        },
      });
      
      // Fit bounds to show entire route
      if (coordinates.length > 1) {
        const bounds = new mapboxgl.LngLatBounds();
        coordinates.forEach(coord => bounds.extend(coord));
        mapRef.current.fitBounds(bounds, { padding: 60, maxZoom: 15 });
      }
    }
  }, [startPoint, endPoint, routePath, isMapLoaded]);

  useEffect(() => {
    let isSubscribed = true;

    const loadBoundary = async () => {
      try {
        const geojson = await shp('/data/marikina-boundary.zip');
        const feature = geojson?.features ? geojson.features[0] : geojson;
        if (isSubscribed && feature?.geometry) {
          setBoundaryFeature(feature);
        }
      } catch (error) {
        console.error('Failed to load Marikina boundary shapefile:', error);
      }
    };

    loadBoundary();
    return () => {
      isSubscribed = false;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !isMapLoaded || !boundaryFeature?.geometry) return;

    const maskSourceId = 'marikina-mask';
    const outlineSourceId = 'marikina-outline';
    const maskLayerId = 'marikina-dim';
    const outlineLayerId = 'marikina-outline';
    const boundaryGeometry = boundaryFeature.geometry;
    const boundaryRing =
      boundaryGeometry.type === 'Polygon'
        ? boundaryGeometry.coordinates[0]
        : boundaryGeometry.coordinates[0][0];
    if (!boundaryRing) return;

    const outerRing = [
      [-180, -85],
      [180, -85],
      [180, 85],
      [-180, 85],
      [-180, -85],
    ];
    const maskFeature = {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [outerRing, [...boundaryRing].reverse()],
      },
    };
    const outlineFeature = {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [...boundaryRing, boundaryRing[0]],
      },
    };
    const labelLayerId = mapRef.current
      .getStyle()
      ?.layers?.find((layer) => layer.type === 'symbol' && layer.layout?.['text-field'])?.id;

    if (!mapRef.current.getSource(maskSourceId)) {
      mapRef.current.addSource(maskSourceId, { type: 'geojson', data: maskFeature });
    } else {
      mapRef.current.getSource(maskSourceId).setData(maskFeature);
    }

    if (!mapRef.current.getSource(outlineSourceId)) {
      mapRef.current.addSource(outlineSourceId, { type: 'geojson', data: outlineFeature });
    } else {
      mapRef.current.getSource(outlineSourceId).setData(outlineFeature);
    }

    if (!mapRef.current.getLayer(maskLayerId)) {
      mapRef.current.addLayer(
        {
          id: maskLayerId,
          type: 'fill',
          source: maskSourceId,
          paint: {
            'fill-color': 'rgba(11, 17, 42, 0.6)',
            'fill-opacity': 0.55,
          },
        },
        labelLayerId
      );
    }

    if (!mapRef.current.getLayer(outlineLayerId)) {
      mapRef.current.addLayer(
        {
          id: outlineLayerId,
          type: 'line',
          source: outlineSourceId,
          paint: {
            'line-color': '#5eead4',
            'line-width': 2,
            'line-opacity': 0.8,
          },
        },
        labelLayerId
      );
    }
  }, [isMapLoaded, boundaryFeature]);

  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) return;

    const floodLayerId = 'flood-layer';
    let isCancelled = false;

    const loadFloodMap = async () => {
      try {
        console.log('Loading flood map for time step:', floodTimeStep);
        console.log('Boundary feature available:', !!boundaryFeature);
        
        // Remove existing layer and source
        if (mapRef.current.getLayer(floodLayerId)) {
          mapRef.current.removeLayer(floodLayerId);
        }
        if (mapRef.current.getSource(floodLayerId)) {
          mapRef.current.removeSource(floodLayerId);
        }

        // Fetch and parse the GeoTIFF from backend server
        const tiffUrl = `${BACKEND_API_URL}/data/timed_floodmaps/${returnPeriod}/${returnPeriod}-${floodTimeStep}.tif`;
        console.log('Fetching TIFF from:', tiffUrl);
        
        const response = await fetch(tiffUrl);
        console.log('Response status:', response.status, response.statusText);
        
        if (!response.ok) {
          console.error(`Failed to fetch flood map: ${response.status} ${response.statusText}`);
          return;
        }

        console.log('Parsing GeoTIFF...');
        const arrayBuffer = await response.arrayBuffer();
        console.log('ArrayBuffer size:', arrayBuffer.byteLength, 'bytes');

        const tiff = await fromBlob(new Blob([arrayBuffer]));
        const image = await tiff.getImage();
        const width = image.getWidth();
        const height = image.getHeight();
        const tiffAspectRatio = width / height;

        console.log('TIFF dimensions:', width, 'x', height, 'pixels');
        console.log('TIFF aspect ratio:', tiffAspectRatio.toFixed(3));

        // MARIKINA CITY CENTER AND COVERAGE
        // Center point of Marikina flood-prone area
        const centerLng = 121.10305;
        const centerLat = 14.6456;

        // Calculate bounds based on TIFF aspect ratio to prevent stretching
        const baseCoverage = 0.06;  // Base coverage in degrees
        let coverageWidth, coverageHeight;

        if (tiffAspectRatio > 1) {
          // Wider TIFF (landscape)
          coverageWidth = baseCoverage;
          coverageHeight = baseCoverage / tiffAspectRatio;
        } else {
          // Taller TIFF (portrait) or square
          coverageHeight = baseCoverage * 1.5;
          coverageWidth = coverageHeight * tiffAspectRatio;
        }

        const MARIKINA_BOUNDS = {
          west:  centerLng - (coverageWidth / 2),
          east:  centerLng + (coverageWidth / 2),
          south: centerLat - (coverageHeight / 2),
          north: centerLat + (coverageHeight / 2)
        };

        console.log('Auto-calculated Marikina bounds (aspect ratio corrected):', MARIKINA_BOUNDS);
        console.log('Coverage width:', coverageWidth.toFixed(4), '° | height:', coverageHeight.toFixed(4), '°');

        const reprojectedCoords = [
          [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.north], // top-left
          [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.north], // top-right
          [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.south], // bottom-right
          [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.south]  // bottom-left
        ];

        console.log('Flood map coordinates:', reprojectedCoords);
        
        const rasters = await image.readRasters();
        
        if (isCancelled) return;

        // Create canvas to render the raster data
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(width, height);

        // Convert raster data to RGBA
        const data = rasters[0]; // First band
        let minVal = Infinity;
        let maxVal = -Infinity;

        // Threshold: ignore very small values (< 0.01m) to remove artifacts
        const FLOOD_THRESHOLD = 0.01;

        // Find min/max values for better color scaling (excluding no-flood areas)
        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          if (value > FLOOD_THRESHOLD) {
            minVal = Math.min(minVal, value);
            maxVal = Math.max(maxVal, value);
          }
        }

        console.log('Flood depth range:', minVal.toFixed(2), 'to', maxVal.toFixed(2), 'meters');
        console.log('Flood threshold:', FLOOD_THRESHOLD, 'meters (values below this are transparent)');

        // Get boundary polygon for clipping (if available)
        let boundaryRing = null;
        if (boundaryFeature?.geometry) {
          const geom = boundaryFeature.geometry;
          boundaryRing = geom.type === 'Polygon'
            ? geom.coordinates[0]
            : geom.coordinates[0][0];
          console.log('Applying boundary clipping with', boundaryRing.length, 'points');
        }

        // Point-in-polygon check (ray casting algorithm)
        const isPointInPolygon = (lng, lat, polygon) => {
          if (!polygon) return true; // No boundary = show all

          let inside = false;
          for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i][0], yi = polygon[i][1];
            const xj = polygon[j][0], yj = polygon[j][1];

            const intersect = ((yi > lat) !== (yj > lat))
              && (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
          }
          return inside;
        };

        // Realistic flood water colors - from light cyan to deep blue
        // ONLY show areas with actual flood water (above threshold) AND within boundary
        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          const pixelIndex = i * 4;

          // Calculate pixel's geographic coordinates
          const row = Math.floor(i / width);
          const col = i % width;
          const lng = MARIKINA_BOUNDS.west + (col / width) * (MARIKINA_BOUNDS.east - MARIKINA_BOUNDS.west);
          const lat = MARIKINA_BOUNDS.north - (row / height) * (MARIKINA_BOUNDS.north - MARIKINA_BOUNDS.south);

          // Check if pixel is within boundary
          const inBoundary = isPointInPolygon(lng, lat, boundaryRing);

          // Only render pixels with significant flood depth AND within boundary
          if (value > FLOOD_THRESHOLD && inBoundary) {
            // Normalize value to 0-1 range (0 = shallow, 1 = deep)
            const normalized = maxVal > minVal ? (value - minVal) / (maxVal - minVal) : 0;

            // Realistic flood water color gradient
            // Shallow water: Light cyan/aqua (#40E0D0)
            // Medium water: Bright blue (#1E90FF)
            // Deep water: Dark blue (#00008B)

            let r, g, b, a;

            if (normalized < 0.3) {
              // Shallow flood: Light cyan to aqua (64, 224, 208) → (30, 144, 255)
              const t = normalized / 0.3;
              r = Math.floor(64 + t * (30 - 64));
              g = Math.floor(224 + t * (144 - 224));
              b = Math.floor(208 + t * (255 - 208));
              a = Math.floor(180 + normalized * 200); // 180-240
            } else if (normalized < 0.7) {
              // Medium flood: Aqua to bright blue (30, 144, 255) → (0, 100, 255)
              const t = (normalized - 0.3) / 0.4;
              r = Math.floor(30 * (1 - t));
              g = Math.floor(144 + t * (100 - 144));
              b = 255;
              a = Math.floor(220 + normalized * 35); // 240-255
            } else {
              // Deep flood: Bright blue to dark blue (0, 100, 255) → (0, 0, 139)
              const t = (normalized - 0.7) / 0.3;
              r = 0;
              g = Math.floor(100 * (1 - t));
              b = Math.floor(255 - t * (255 - 139));
              a = 255; // Fully opaque for deep water
            }

            imageData.data[pixelIndex] = r;
            imageData.data[pixelIndex + 1] = g;
            imageData.data[pixelIndex + 2] = b;
            imageData.data[pixelIndex + 3] = a;
          } else {
            // Complete transparency for non-flooded areas
            imageData.data[pixelIndex] = 0;
            imageData.data[pixelIndex + 1] = 0;
            imageData.data[pixelIndex + 2] = 0;
            imageData.data[pixelIndex + 3] = 0;
          }
        }

        ctx.putImageData(imageData, 0, 0);
        console.log('Canvas created successfully');

        if (isCancelled || !mapRef.current) return;

        // Add the canvas as an image source
        mapRef.current.addSource(floodLayerId, {
          type: 'image',
          url: canvas.toDataURL(),
          coordinates: reprojectedCoords
        });

        // Add flood layer on top of everything except route layer
        const layers = mapRef.current.getStyle().layers;
        // Find the first symbol layer (labels) to insert flood layer before it
        let firstSymbolId;
        for (let i = 0; i < layers.length; i++) {
          if (layers[i].type === 'symbol') {
            firstSymbolId = layers[i].id;
            break;
          }
        }

        mapRef.current.addLayer({
          id: floodLayerId,
          type: 'raster',
          source: floodLayerId,
          layout: {
            'visibility': floodEnabled ? 'visible' : 'none'
          },
          paint: {
            'raster-opacity': 0.5,  // Increased visibility (was 0.7)
            'raster-fade-duration': 0,
            'raster-brightness-max': 1.0,
            'raster-saturation': 0.3  // Enhance color saturation
          }
        }, firstSymbolId); // Insert before labels so labels remain visible
        
        // Move route layer on top of flood layer if it exists
        if (mapRef.current.getLayer('route')) {
          mapRef.current.moveLayer('route');
        }
        
        console.log('FLOOD MAP LOADED SUCCESSFULLY with manual Marikina bounds!');

      } catch (error) {
        console.warn('Flood map not available:', error.message);
        // Silently fail - flood maps are optional for basic map functionality
      }
    };

    loadFloodMap();

    return () => {
      isCancelled = true;
    };
  }, [isMapLoaded, floodTimeStep, returnPeriod, floodEnabled, boundaryFeature]);

  // Control flood layer visibility based on floodEnabled state
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) return;

    const floodLayerId = 'flood-layer';

    // Check if the flood layer exists
    if (mapRef.current.getLayer(floodLayerId)) {
      mapRef.current.setLayoutProperty(
        floodLayerId,
        'visibility',
        floodEnabled ? 'visible' : 'none'
      );
      console.log('Flood layer visibility set to:', floodEnabled ? 'visible' : 'none');
    }
  }, [floodEnabled, isMapLoaded, floodTimeStep, returnPeriod]);

  return (
    <div
      ref={mapContainerRef}
      style={{ width: '100%', height: '100%', minHeight: '100vh' }}
    >
      <div style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        background: 'linear-gradient(160deg, rgba(36, 142, 168, 0.3) 0%, rgba(255,255,255,0.1) 100%)',
        backdropFilter: 'blur(12px)',
        padding: '1.25rem 1.5rem',
        borderRadius: '14px',
        boxShadow: '0 10px 35px rgba(36, 142, 168, 0.4)',
        zIndex: 1,
        border: '1px solid rgba(255, 255, 255, 0.25)',
        minWidth: '240px'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '0.75rem'
        }}>
          <div style={{
            fontSize: '1.1rem',
            fontWeight: 600,
            color: 'white',
            letterSpacing: '0.025rem'
          }}>
            🌊 Flood Simulation
          </div>
          <button
            onClick={() => setFloodEnabled(!floodEnabled)}
            style={{
              background: floodEnabled ? 'rgba(16, 185, 129, 0.9)' : 'rgba(239, 68, 68, 0.9)',
              border: 'none',
              borderRadius: '8px',
              padding: '0.4rem 0.8rem',
              color: 'white',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'scale(1.05)';
              e.target.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'scale(1)';
              e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';
            }}
          >
            <span style={{ fontSize: '0.9rem' }}>{floodEnabled ? '✓' : '✕'}</span>
            {floodEnabled ? 'ON' : 'OFF'}
          </button>
        </div>

        {/* Return Period Selector */}
        <div style={{ marginBottom: '0.75rem' }}>
          <label style={{
            display: 'block',
            color: 'rgba(255, 255, 255, 0.9)',
            fontSize: '0.875rem',
            marginBottom: '0.5rem',
            fontWeight: 500
          }}>
            Return Period:
          </label>
          <select
            value={returnPeriod}
            onChange={(e) => setReturnPeriod(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: '6px',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              background: 'rgba(255, 255, 255, 0.15)',
              color: 'white',
              fontSize: '0.875rem',
              cursor: 'pointer',
              outline: 'none',
              fontWeight: 500
            }}
          >
            <option value="rr01" style={{ background: '#667eea', color: 'white' }}>
              2-Year Flood (RR01)
            </option>
            <option value="rr02" style={{ background: '#667eea', color: 'white' }}>
              5-Year Flood (RR02)
            </option>
            <option value="rr03" style={{ background: '#667eea', color: 'white' }}>
              Return Period 3 (RR03)
            </option>
            <option value="rr04" style={{ background: '#667eea', color: 'white' }}>
              10-Year Flood (RR04)
            </option>
          </select>
        </div>
{/* 
        <input
          type="range"
          min="1"
          max="18"
          value={floodTimeStep}
          onChange={(e) => setFloodTimeStep(parseInt(e.target.value))}
          style={{
            width: '100%',
            height: '6px',
            borderRadius: '3px',
            background: 'rgba(255, 255, 255, 0.3)',
            outline: 'none',
            marginBottom: '0.5rem',
            cursor: 'pointer'
          }}
        />
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          color: 'rgba(255, 255, 255, 0.9)',
          fontSize: '0.875rem'
        }}>
          <span>Time Step:</span>
          <span style={{
            fontWeight: 600,
            fontSize: '1rem',
            background: 'rgba(255, 255, 255, 0.2)',
            padding: '0.25rem 0.75rem',
            borderRadius: '6px'
          }}>
            {floodTimeStep} / 18
          </span>
        </div>
 */}
        
      </div>

      {/* Real-time Flood Alerts */}
      <FloodAlerts
        alerts={criticalAlerts}
        onClear={clearAlerts}
        isConnected={isConnected}
      />
    </div>
  );
}
