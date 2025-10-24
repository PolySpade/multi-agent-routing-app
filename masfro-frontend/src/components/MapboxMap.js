import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import shp from 'shpjs';
import { fromUrl, fromBlob } from 'geotiff';
import proj4 from 'proj4';

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:3001';

// Define projections for coordinate conversion
// EPSG:3857 is Web Mercator, used by many web maps and found in your GeoTIFF
// EPSG:4326 is WGS 84, the standard lat/lng coordinate system
proj4.defs("EPSG:3857", "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs");
proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");

export default function MapboxMap({ startPoint, endPoint, routePath, onMapClick, onLocationSearch, showTraffic = true, panelCollapsed = false }) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const startMarkerRef = useRef(null);
  const endMarkerRef = useRef(null);
  const initialCenterRef = useRef(startPoint ? [startPoint.lng, startPoint.lat] : [121.0943, 14.6507]);
  const initialZoomRef = useRef(startPoint ? 12 : 10);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [boundaryFeature, setBoundaryFeature] = useState(null);
  const [floodTimeStep, setFloodTimeStep] = useState(1);
  const onMapClickRef = useRef(onMapClick);

  useEffect(() => {
    onMapClickRef.current = onMapClick;
  }, [onMapClick]);

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
    });

    // Add click handler with proper debugging
    mapRef.current.on('click', (e) => {
      console.log('Mapbox click event:', e.lngLat); // Debug log
      const coords = { lat: e.lngLat.lat, lng: e.lngLat.lng };
      console.log('Calling onMapClick with:', coords); // Debug log
      const clickHandler = onMapClickRef.current;
      if (clickHandler) {
        clickHandler(coords);
      } else {
        console.warn('onMapClick handler is not defined'); // Debug log
      }
    });

    mapRef.current.on('style.load', () => {
      if (mapRef.current.getLayer('add-3d-buildings')) return;
      const layers = mapRef.current.getStyle()?.layers || [];
      const labelLayer = layers.find(
        (layer) => layer.type === 'symbol' && layer.layout?.['text-field']
      );
      const labelLayerId = labelLayer?.id;

      if (!labelLayerId) return;

      mapRef.current.addLayer(
        {
          id: 'add-3d-buildings',
          source: 'composite',
          'source-layer': 'building',
          filter: ['==', 'extrude', 'true'],
          type: 'fill-extrusion',
          minzoom: 18,
          paint: {
            'fill-extrusion-color': '#3951ba',
            'fill-extrusion-height': [
              'interpolate',
              ['linear'],
              ['zoom'],
              15, 0,
              15.05, ['get', 'height'],
            ],
            'fill-extrusion-base': [
              'interpolate',
              ['linear'],
              ['zoom'],
              15, 0,
              15.05, ['get', 'min_height'],
            ],
            'fill-extrusion-opacity': 0.6,
          },
        },
        labelLayerId
      );
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
      }
      setIsMapLoaded(false);
    };
  }, []);

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
        
        // Remove existing layer and source
        if (mapRef.current.getLayer(floodLayerId)) {
          mapRef.current.removeLayer(floodLayerId);
        }
        if (mapRef.current.getSource(floodLayerId)) {
          mapRef.current.removeSource(floodLayerId);
        }

        // Fetch and parse the GeoTIFF from backend server
        const tiffUrl = `${BACKEND_API_URL}/data/timed_floodmaps/rr01/rr01-${floodTimeStep}.tif`;
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
        const bbox = image.getBoundingBox();
        const [minX, minY, maxX, maxY] = bbox;
        
        console.log('Original Bounding box (EPSG:3857):', bbox);

        // Reproject bounding box from EPSG:3857 to EPSG:4326 (lng/lat)
        const [west, south] = proj4('EPSG:3857', 'EPSG:4326', [minX, minY]);
        const [east, north] = proj4('EPSG:3857', 'EPSG:4326', [maxX, maxY]);
        
        const reprojectedCoords = [
          [west, north], // top-left
          [east, north], // top-right
          [east, south], // bottom-right
          [west, south]  // bottom-left
        ];

        console.log('Reprojected Coords (EPSG:4326):', reprojectedCoords);
        
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
        
        // Find min/max values for better color scaling
        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          if (value > 0) {
            minVal = Math.min(minVal, value);
            maxVal = Math.max(maxVal, value);
          }
        }
        
        console.log('Flood depth range:', minVal, 'to', maxVal);
        
        // Map values to colors - QGIS style: White to Black gradient, colorized blue, darken blend
        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          const pixelIndex = i * 4;
          
          if (value > 0) {
            // Normalize value to 0-1 range (white = low, black = high)
            const normalized = maxVal > minVal ? (value - minVal) / (maxVal - minVal) : 0;
            
            // White to black gradient (255 = white, 0 = black)
            const grayValue = Math.floor((1 - normalized) * 255);
            
            // Colorize with blue tint (darken blend mode simulation)
            // Apply blue color overlay while maintaining the gradient intensity
            const blueMultiplier = 0.7; // Darken intensity
            imageData.data[pixelIndex] = Math.floor(grayValue * 0.3 * blueMultiplier);     // R - minimal red
            imageData.data[pixelIndex + 1] = Math.floor(grayValue * 0.5 * blueMultiplier); // G - moderate green
            imageData.data[pixelIndex + 2] = Math.floor(grayValue * blueMultiplier);       // B - full blue channel
            imageData.data[pixelIndex + 3] = Math.floor(200 * (0.3 + normalized * 0.7));   // A - more opaque for deeper floods
          } else {
            imageData.data[pixelIndex + 3] = 0; // Transparent for no flood
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
          paint: {
            'raster-opacity': 0.7,
            'raster-fade-duration': 0
          }
        }, firstSymbolId); // Insert before labels so labels remain visible
        
        // Move route layer on top of flood layer if it exists
        if (mapRef.current.getLayer('route')) {
          mapRef.current.moveLayer('route');
        }
        
        console.log('Flood map loaded successfully!');

      } catch (error) {
        console.error('Error loading flood map:', error);
        console.error('Error details:', error.message, error.stack);
      }
    };

    loadFloodMap();

    return () => {
      isCancelled = true;
    };
  }, [isMapLoaded, floodTimeStep]);

  return (
    <div
      ref={mapContainerRef}
      style={{ width: '100%', height: '100%', minHeight: '100vh' }}
    >
      <div style={{ 
        position: 'absolute', 
        top: '20px', 
        right: '20px', 
        background: 'linear-gradient(160deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%)',
        backdropFilter: 'blur(10px)',
        padding: '1.25rem 1.5rem',
        borderRadius: '12px',
        boxShadow: '0 8px 32px rgba(15, 23, 42, 0.4)',
        zIndex: 1,
        border: '1px solid rgba(226, 232, 240, 0.25)',
        minWidth: '240px'
      }}>
        <div style={{
          fontSize: '1.1rem',
          fontWeight: 600,
          color: 'white',
          marginBottom: '0.75rem',
          letterSpacing: '0.025rem'
        }}>
          🌊 Flood Simulation
        </div>
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
      </div>
    </div>
  );
}
