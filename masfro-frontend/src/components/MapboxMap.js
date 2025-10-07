import React, { useRef, useEffect, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import shp from 'shpjs';
import { fromArrayBuffer } from 'geotiff';


const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
const MARIKINA_BOUNDARY_RING = [
  [121.084555, 14.613768],
  [121.09623, 14.611346],
  [121.101761, 14.627829],
  [121.10614, 14.625804],
  [121.112633, 14.620768],
  [121.122589, 14.622586],
  [121.129112, 14.625384],
  [121.138039, 14.63171],
  [121.14249, 14.64646],
  [121.13994, 14.65342],
  [121.13749, 14.6599],
  [121.1322, 14.66715],
  [121.1219, 14.67623],
  [121.11832, 14.70217],
  [121.11249, 14.71329],
  [121.10288, 14.71753],
  [121.094, 14.70246],
  [121.08677, 14.70194],
  [121.07939, 14.7099],
  [121.07012, 14.70761],
  [121.06273, 14.70109],
  [121.05178, 14.69232],
  [121.04463, 14.67502],
  [121.04498, 14.64848],
  [121.04959, 14.63981],
  [121.05852, 14.62961],
  [121.06297, 14.62799],
  [121.06377, 14.62771],
  [121.06456, 14.62744],
  [121.06594, 14.62697],
  [121.06713, 14.62646],
  [121.0682, 14.62586],
  [121.06917, 14.62529],
  [121.07011, 14.62473],
  [121.07127, 14.62413],
  [121.07253, 14.62352],
  [121.07384, 14.62291],
  [121.07474, 14.62243],
  [121.07548, 14.62187],
  [121.07604, 14.62125],
  [121.07641, 14.62055],
  [121.07666, 14.61985],
  [121.07693, 14.61919],
  [121.07736, 14.6184],
  [121.07797, 14.61755],
  [121.07865, 14.61678],
  [121.07953, 14.61598],
  [121.08047, 14.61536],
  [121.08154, 14.61486],
  [121.08272, 14.61439],
  [121.08388, 14.61403],
  [121.084555, 14.613768]
]; //backup boundary ring

const FLOOD_SERIES = ['rr01', 'rr02', 'rr03', 'rr04'];
const FLOOD_LAYER_OPACITY = 1;
const FLOOD_COLOR_MODE = process.env.NEXT_PUBLIC_FLOOD_COLOR_MODE || 'aqua';
const FLOOD_COLOR_PRESETS = {
  screen: {
    description: 'Grayscale ramp with screen-style brightness',
    baseColor: { r: 0, g: 0, b: 0 },
    highlightColor: { r: 255, g: 255, b: 255 },
    alphaBoost: 255,
    alphaExponent: 0.75,
    minAlpha: 0,
  },
  aqua: {
    description: 'Blue gradient with strong opacity floor',
    baseColor: { r: 24, g: 116, b: 205 },
    highlightColor: { r: 96, g: 200, b: 255 },
    alphaBoost: 180,
    alphaExponent: 1,
    minAlpha: 160,
  },
};
const FLOOD_FRAME_SETS = FLOOD_SERIES.reduce((acc, code) => {
  acc[code] = Array.from({ length: 18 }, (_, idx) => `/data/timed_floodmaps/${code}/${code}-${idx + 1}.tif`);
  return acc;
}, {});
const getFloodFrames = (series) => (series ? FLOOD_FRAME_SETS[series] || [] : []);



export default function MapboxMap({ startPoint, endPoint, routePath, onMapClick, onLocationSearch, showTraffic = true, panelCollapsed = false, floodEnabled = false, floodSeries = 'rr01', floodFrameIndex = null, }) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const startMarkerRef = useRef(null);
  const endMarkerRef = useRef(null);
  const initialCenterRef = useRef(startPoint ? [startPoint.lng, startPoint.lat] : [121.0943, 14.6507]);
  const initialZoomRef = useRef(startPoint ? 12 : 10);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [boundaryFeature, setBoundaryFeature] = useState(null);
  const onMapClickRef = useRef(onMapClick);
  const floodCacheRef = useRef({});

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
        console.error('onMapClick is not defined');
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


  // useEffect(() => {
  //   if (!mapRef.current || !isMapLoaded) return;

  //   const trafficSourceId = 'traffic';
  //   const trafficLayerId = 'traffic';

  //   if (showTraffic) {
  //     if (!mapRef.current.getSource(trafficSourceId)) {
  //       mapRef.current.addSource(trafficSourceId, {
  //         type: 'vector',
  //         url: 'mapbox://mapbox.mapbox-traffic-v1',
  //       });
  //     }

  //     if (!mapRef.current.getLayer(trafficLayerId)) {
  //       mapRef.current.addLayer({
  //         id: trafficLayerId,
  //         type: 'line',
  //         source: trafficSourceId,
  //         'source-layer': 'traffic',
  //         paint: {
  //           'line-width': 1,
  //           'line-opacity': 0.9,
  //           'line-color': [
  //             'match',
  //             ['get', 'congestion'],
  //             'low', '#4f9dff',
  //             'moderate', '#76a9ff',
  //             'heavy', '#9f84ff',
  //             'severe', '#c26bff',
  //             '#0b1d3a',
  //           ],
  //         },
  //       });
  //     }
  //   } else {
  //     if (mapRef.current.getLayer(trafficLayerId)) mapRef.current.removeLayer(trafficLayerId);
  //     if (mapRef.current.getSource(trafficSourceId)) mapRef.current.removeSource(trafficSourceId);
  //   }
  // }, [isMapLoaded, showTraffic]);

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
      mapRef.current.addLayer({
        id: outlineLayerId,
        type: 'line',
        source: outlineSourceId,
        paint: {
          'line-color': '#60a5fa',
          'line-width': 2,
          'line-opacity': 0.9,
        },
      });
    }
  }, [isMapLoaded, boundaryFeature]);

  const clearFloodLayer = useCallback(() => {
    if (!mapRef.current) return;
    if (mapRef.current.getLayer('flood-raster')) {
      mapRef.current.removeLayer('flood-raster');
    }
    if (mapRef.current.getSource('flood-raster')) {
      mapRef.current.removeSource('flood-raster');
    }
  }, [mapRef]);

  const decodeFloodFrame = useCallback(async (frameUrl) => {
    const response = await fetch(frameUrl);
    const arrayBuffer = await response.arrayBuffer();
    const tiff = await fromArrayBuffer(arrayBuffer);
    const image = await tiff.getImage();
    const rasters = await image.readRasters({ interleave: true });
    const width = image.getWidth();
    const height = image.getHeight();
    const bbox = image.getBoundingBox();
    const samplesPerPixel = image.getSamplesPerPixel();
    const bitsPerSample = image.getBitsPerSample();
    const noDataValueRaw = image.getGDALNoData();
    const noDataValue = noDataValueRaw != null && noDataValueRaw !== '' ? Number(noDataValueRaw) : null;
    const totalPixels = width * height;
    const stride = samplesPerPixel || 1;

    const resolveBits = (sampleIndex = 0) => {
      if (Array.isArray(bitsPerSample)) {
        return bitsPerSample[sampleIndex] || bitsPerSample[0] || 8;
      }
      return bitsPerSample || 8;
    };

    const normalizeSample = (value, sampleIndex = 0) => {
      if (Number.isNaN(value) || value == null) return 0;
      if (noDataValue != null && value === noDataValue) return 0;
      if (value >= 0 && value <= 1) {
        return Math.round(value * 255);
      }
      const bits = resolveBits(sampleIndex);
      const maxSampleValue = Math.pow(2, bits) - 1;
      if (!maxSampleValue || !Number.isFinite(maxSampleValue)) {
        return Math.max(0, Math.min(255, Math.round(value)));
      }
      return Math.max(0, Math.min(255, Math.round((value / maxSampleValue) * 255)));
    };

    const computeChannelStats = (channelIndex = 0) => {
      let min = Infinity;
      let max = -Infinity;
      for (let pixel = 0; pixel < totalPixels; pixel += 1) {
        const sample = rasters[pixel * stride + channelIndex];
        if (sample == null || Number.isNaN(sample)) continue;
        if (noDataValue != null && sample === noDataValue) continue;
        if (sample < min) min = sample;
        if (sample > max) max = sample;
      }
      if (!Number.isFinite(min) || !Number.isFinite(max)) {
        return { min: 0, max: 0 };
      }
      return { min, max };
    };

    const scaleToAlpha = (value, stats) => {
      if (Number.isNaN(value) || value == null) return 0;
      if (noDataValue != null && value === noDataValue) return 0;
      const { min, max } = stats;
      if (max <= min) {
        return value > min ? 255 : 0;
      }
      const scaled = ((value - min) / (max - min)) * 255;
      return Math.max(0, Math.min(255, Math.round(scaled)));
    };

    const colorConfig = FLOOD_COLOR_PRESETS[FLOOD_COLOR_MODE] || FLOOD_COLOR_PRESETS.aqua;
    const {
      baseColor,
      highlightColor,
      alphaBoost = 255,
      alphaExponent = 1,
      minAlpha = 0,
    } = colorConfig;

    const interpolateColor = (normalized) => ({
      r: Math.round(baseColor.r + (highlightColor.r - baseColor.r) * normalized),
      g: Math.round(baseColor.g + (highlightColor.g - baseColor.g) * normalized),
      b: Math.round(baseColor.b + (highlightColor.b - baseColor.b) * normalized),
    });

    const computeVisibleAlpha = (normalized, alphaSample = 0) => {
      if (!Number.isFinite(normalized) || normalized <= 0) return 0;
      const normalizedAdjusted = Math.pow(normalized, alphaExponent);
      const boostAlpha = Math.round(normalizedAdjusted * alphaBoost);
      const combined = Math.max(alphaSample, boostAlpha);
      if (combined <= 0) return 0;
      return Math.min(255, Math.max(minAlpha, combined));
    };

    const applyColorRamp = (normalized, alphaSample = 0) => {
      const clampedNormalized = Math.max(0, Math.min(1, normalized));
      const visibleAlpha = computeVisibleAlpha(clampedNormalized, alphaSample);
      if (visibleAlpha === 0) {
        return { r: 0, g: 0, b: 0, a: 0 };
      }
      const { r, g, b } = interpolateColor(clampedNormalized);
      return { r, g, b, a: visibleAlpha };
    };

    const toRgbaArray = () => {
      const rgba = new Uint8ClampedArray(totalPixels * 4);

      if (samplesPerPixel === 4 && rasters.length === totalPixels * 4) {
        rgba.set(rasters instanceof Uint8ClampedArray ? rasters : new Uint8ClampedArray(rasters));
        return rgba;
      }

      if (samplesPerPixel === 3 && rasters.length >= totalPixels * 3) {
        for (let src = 0, dest = 0; src < totalPixels * 3; src += 3, dest += 4) {
          rgba[dest] = normalizeSample(rasters[src], 0);
          rgba[dest + 1] = normalizeSample(rasters[src + 1], 1);
          rgba[dest + 2] = normalizeSample(rasters[src + 2], 2);
          rgba[dest + 3] = 255;
        }
        return rgba;
      }

      if (samplesPerPixel === 2 && rasters.length >= totalPixels * 2) {
        const stats = computeChannelStats(0);
        for (let src = 0, dest = 0; src < totalPixels * 2; src += 2, dest += 4) {
          const rawValue = rasters[src];
          const normalized = scaleToAlpha(rawValue, stats) / 255;
          const alphaSample = normalizeSample(rasters[src + 1], 1);
          const { r, g, b, a } = applyColorRamp(normalized, alphaSample);
          rgba[dest] = r;
          rgba[dest + 1] = g;
          rgba[dest + 2] = b;
          rgba[dest + 3] = a;
        }
        return rgba;
      }

      const stats = computeChannelStats(0);
      for (let i = 0, dest = 0; i < totalPixels; i += 1, dest += 4) {
        const sampleIndex = i * stride;
        const rawValue = rasters[sampleIndex];
        const alpha = scaleToAlpha(rawValue, stats);
        const normalized = alpha / 255;
        const { r, g, b, a } = applyColorRamp(normalized, alpha);
        rgba[dest] = r;
        rgba[dest + 1] = g;
        rgba[dest + 2] = b;
        rgba[dest + 3] = a;
      }

      return rgba;
    };

    const rgbaData = toRgbaArray();
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Failed to obtain 2D context for flood raster');
    const imageData = ctx.createImageData(width, height);
    imageData.data.set(rgbaData);
    ctx.putImageData(imageData, 0, 0);

    return {
      url: frameUrl,
      dataUrl: canvas.toDataURL(),
      coordinates: [
        [bbox[0], bbox[3]],
        [bbox[2], bbox[3]],
        [bbox[2], bbox[1]],
        [bbox[0], bbox[1]],
      ],
    };
  }, []);

  const ensureSeriesLoaded = useCallback(async (series) => {
    if (!series) return [];
    if (floodCacheRef.current[series]) return floodCacheRef.current[series];
    const frameUrls = getFloodFrames(series);
    if (!frameUrls.length) return [];
    const frames = await Promise.all(
      frameUrls.map(async (url) => {
        try {
          return await decodeFloodFrame(url);
        } catch (error) {
          console.error(`Failed to decode flood frame ${url}:`, error);
          return null;
        }
      })
    );
    const filtered = frames.filter(Boolean);
    floodCacheRef.current[series] = filtered;
    return filtered;
  }, [decodeFloodFrame]);

  const renderFloodLayer = useCallback(
    (frameData) => {
      if (!mapRef.current || !frameData) return;
      const { dataUrl, coordinates } = frameData;
      const floodSource = mapRef.current.getSource('flood-raster');
      if (!floodSource) {
        mapRef.current.addSource('flood-raster', { type: 'image', url: dataUrl, coordinates });
        mapRef.current.addLayer({
          id: 'flood-raster',
          type: 'raster',
          source: 'flood-raster',
          paint: { 'raster-opacity': FLOOD_LAYER_OPACITY },
        });
      } else if (typeof floodSource.updateImage === 'function') {
        floodSource.updateImage({ url: dataUrl, coordinates });
      } else {
        clearFloodLayer();
        mapRef.current.addSource('flood-raster', { type: 'image', url: dataUrl, coordinates });
        mapRef.current.addLayer({
          id: 'flood-raster',
          type: 'raster',
          source: 'flood-raster',
          paint: { 'raster-opacity': FLOOD_LAYER_OPACITY },
        });
      }
    },
    [clearFloodLayer]
  );

  useEffect(() => {
    if (!floodEnabled || !isMapLoaded) {
      if (!floodEnabled) clearFloodLayer();
      return;
    }
    FLOOD_SERIES.forEach((series) => {
      ensureSeriesLoaded(series);
    });
  }, [clearFloodLayer, ensureSeriesLoaded, floodEnabled, isMapLoaded]);

  useEffect(() => {
    if (!isMapLoaded) return;
    if (!floodEnabled) {
      clearFloodLayer();
      return;
    }
    if (floodFrameIndex === null) return;
    let cancelled = false;
    const run = async () => {
      const frames = await ensureSeriesLoaded(floodSeries);
      if (cancelled) return;
      const frame = frames[floodFrameIndex];
      if (!frame) {
        clearFloodLayer();
        return;
      }
      console.debug(
        `[FloodOverlay] Rendering manual frame ${floodFrameIndex + 1} of ${frames.length} for series ${floodSeries}`,
        frame.url
      );
      renderFloodLayer(frame);
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [clearFloodLayer, ensureSeriesLoaded, floodEnabled, floodFrameIndex, floodSeries, isMapLoaded, renderFloodLayer]);

  useEffect(() => {
    if (!isMapLoaded || !floodEnabled || floodFrameIndex !== null) return;
    let frameIndex = 0;
    let timeoutId;
    let cancelled = false;
    const run = async () => {
      const frames = await ensureSeriesLoaded(floodSeries);
      if (!frames.length || cancelled) {
        clearFloodLayer();
        return;
      }
      const step = () => {
        if (cancelled) return;
        console.debug(
          `[FloodOverlay] Rendering auto frame ${frameIndex + 1} of ${frames.length} for series ${floodSeries}`,
          frames[frameIndex]?.url
        );
        renderFloodLayer(frames[frameIndex]);
        frameIndex = (frameIndex + 1) % frames.length;
        timeoutId = setTimeout(step, 1500);
      };
      step();
    };
    run();
    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [clearFloodLayer, ensureSeriesLoaded, floodEnabled, floodFrameIndex, floodSeries, isMapLoaded, renderFloodLayer]);

  return (
    <div
      ref={mapContainerRef}
      style={{ width: '100%', height: '100%', minHeight: '100vh' }}
    />
  );
}