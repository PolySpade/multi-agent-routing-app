const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
const DEFAULT_ROUTING_ENDPOINT = process.env.NEXT_PUBLIC_ROUTING_ENDPOINT || 'http://127.0.0.1:8000/api/route';
const BACKEND_ROUTING_DISABLED = process.env.NEXT_PUBLIC_DISABLE_BACKEND_ROUTING === 'true';

/**
 * Fetches a route from Mapbox Directions API
 * @param {Object} start - Start point with lat and lng
 * @param {Object} end - End point with lat and lng
 * @returns {Promise<Object>} Route data with coordinates, distance, and duration
 */
export const fetchMapboxRoute = async (start, end) => {
  if (!MAPBOX_TOKEN) {
    throw new Error('Missing NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN environment variable');
  }

  const coords = `${start.lng},${start.lat};${end.lng},${end.lat}`;
  const params = new URLSearchParams({
    geometries: 'geojson',
    overview: 'full',
    steps: 'false',
    access_token: MAPBOX_TOKEN,
  });

  const response = await fetch(`https://api.mapbox.com/directions/v5/mapbox/driving/${coords}?${params.toString()}`);

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Mapbox Directions request failed: ${response.status} ${errorBody}`);
  }

  const data = await response.json();
  const route = data?.routes?.[0];
  if (!route?.geometry?.coordinates) {
    throw new Error('Mapbox Directions did not return a valid route');
  }

  return {
    coordinates: route.geometry.coordinates.map(([lng, lat]) => ({ lat, lng })),
    distance: route.distance,
    duration: route.duration,
  };
};

/**
 * Finds a route between two points with configurable risk preferences
 * Tries backend first, falls back to Mapbox if backend is unavailable
 * @param {Object} startPoint - Start point with lat and lng
 * @param {Object} endPoint - End point with lat and lng
 * @param {Function} setRoutePath - State setter for route path
 * @param {Function} setRouteMeta - State setter for route metadata
 * @param {Function} setMessage - State setter for status message
 * @param {Function} setLoading - State setter for loading state
 * @param {string} routingMode - Routing preference: 'safest', 'balanced', or 'fastest'
 * @returns {Promise<void>}
 */
export const findRoute = async (startPoint, endPoint, setRoutePath, setRouteMeta, setMessage, setLoading, routingMode = 'balanced') => {
  if (!startPoint || !endPoint) {
    setMessage('Please select both a start and end point on the map.');
    return;
  }

  setLoading(true);
  setRoutePath(null); // Clear previous route
  setRouteMeta(null);

  // Set message based on routing mode
  const modeMessages = {
    safest: 'Calculating safest route (avoiding floods)...',
    balanced: 'Calculating balanced route (safety + speed)...',
    fastest: 'Calculating fastest route (risk-tolerant)...',
  };
  setMessage(modeMessages[routingMode] || 'Calculating route...');

  try {
    let backendFailed = BACKEND_ROUTING_DISABLED;

    if (!BACKEND_ROUTING_DISABLED) {
      try {
        // Build preferences based on routing mode
        const preferences = {};
        if (routingMode === 'safest') {
          preferences.avoid_floods = true;
        } else if (routingMode === 'fastest') {
          preferences.fastest = true;
        }
        // 'balanced' mode sends no preferences (uses backend defaults)

        const requestBody = {
          start_location: [startPoint.lat, startPoint.lng],
          end_location: [endPoint.lat, endPoint.lng],
        };

        // Only add preferences if not balanced mode
        if (Object.keys(preferences).length > 0) {
          requestBody.preferences = preferences;
        }

        console.log('[Routing] Sending request to backend:', {
          endpoint: DEFAULT_ROUTING_ENDPOINT,
          mode: routingMode,
          requestBody
        });

        const response = await fetch(DEFAULT_ROUTING_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        });

        console.log('[Routing] Backend response status:', response.status);

        if (!response.ok) {
          const errorText = await response.text();
          console.error('[Routing] Backend error response:', errorText);
          console.error('[Routing] Failed coordinates:', {
            start: requestBody.start_location,
            end: requestBody.end_location
          });

          // Check if it's a "no route found" error
          if (errorText.includes('No safe route found')) {
            throw new Error(
              `Could not find route: The selected locations may be outside the Marikina City area. ` +
              `Please select points within Marikina City, Philippines. ` +
              `Coordinates used: Start [${requestBody.start_location}], End [${requestBody.end_location}]`
            );
          }

          throw new Error(`Backend responded with ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        console.log('[Routing] Backend response data:', data);

        // Handle impassable or no safe route status
        if (data.status === 'impassable') {
          setRoutePath(null);
          setRouteMeta({
            status: 'impassable',
            warnings: data.warnings || [],
            provider: 'backend',
            routingMode: routingMode,
          });
          setMessage('⛔ IMPASSABLE: No route exists - all roads are critically flooded.');
          setLoading(false);
          return;
        }

        if (data.status === 'no_safe_route') {
          setRoutePath(null);
          setRouteMeta({
            status: 'no_safe_route',
            warnings: data.warnings || [],
            provider: 'backend',
            routingMode: routingMode,
          });
          setMessage('⚠️ No safe route found. Try "Fastest" mode or choose different locations.');
          setLoading(false);
          return;
        }

        // Handle successful route
        if (!data?.path || !Array.isArray(data.path) || data.path.length === 0) {
          throw new Error('Backend response did not contain a valid path');
        }

        setRoutePath(data.path);
        setRouteMeta({
          status: data.status || 'success',
          distance: data.distance || data.summary?.distance,
          duration: data.estimated_time || data.summary?.duration,
          riskLevel: data.risk_level !== undefined ? data.risk_level : null,
          maxRisk: data.max_risk !== undefined ? data.max_risk : null,
          warnings: data.warnings || [],
          provider: 'backend',
          routingMode: routingMode,
        });

        const modeLabels = {
          safest: 'Safest route',
          balanced: 'Balanced route',
          fastest: 'Fastest route',
        };
        setMessage(`${modeLabels[routingMode] || 'Route'} found via MAS-FRO backend.`);
      } catch (backendError) {
        backendFailed = true;
        console.warn('Backend routing unavailable, falling back to Mapbox placeholder.', backendError);
      }
    }

    if (backendFailed) {
      const mapboxRoute = await fetchMapboxRoute(startPoint, endPoint);
      setRoutePath(mapboxRoute.coordinates);
      setRouteMeta({
        distance: mapboxRoute.distance,
        duration: mapboxRoute.duration,
        provider: 'mapbox',
      });
      setMessage('Route Successfully Generated');
    }
  } catch (error) {
    console.error('Failed to calculate route:', error);
    setMessage('Error: Could not calculate route via backend or Mapbox fallback. Check your server and tokens.');
  } finally {
    setLoading(false);
  }
};
