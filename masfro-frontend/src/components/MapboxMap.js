import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import shp from 'shpjs';

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export default function MapboxMap({ startPoint, endPoint, routePath, onMapClick, onLocationSearch, showTraffic = true, panelCollapsed = false }) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const startMarkerRef = useRef(null);
  const endMarkerRef = useRef(null);
  const initialCenterRef = useRef(startPoint ? [startPoint.lng, startPoint.lat] : [121.0943, 14.6507]);
  const initialZoomRef = useRef(startPoint ? 12 : 10);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [boundaryFeature, setBoundaryFeature] = useState(null);
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

  return (
    <div
      ref={mapContainerRef}
      style={{ width: '100%', height: '100%', minHeight: '100vh' }}
    />
  );
}