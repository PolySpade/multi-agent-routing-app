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
 * Finds the safest route between two points
 * Tries backend first, falls back to Mapbox if backend is unavailable
 * @param {Object} startPoint - Start point with lat and lng
 * @param {Object} endPoint - End point with lat and lng
 * @param {Function} setRoutePath - State setter for route path
 * @param {Function} setRouteMeta - State setter for route metadata
 * @param {Function} setMessage - State setter for status message
 * @param {Function} setLoading - State setter for loading state
 * @returns {Promise<void>}
 */
export const findRoute = async (startPoint, endPoint, setRoutePath, setRouteMeta, setMessage, setLoading) => {
  if (!startPoint || !endPoint) {
    setMessage('Please select both a start and end point on the map.');
    return;
  }
  
  setLoading(true);
  setRoutePath(null); // Clear previous route
  setRouteMeta(null);
  setMessage('Calculating safest route...');

  try {
    let backendFailed = BACKEND_ROUTING_DISABLED;

    if (!BACKEND_ROUTING_DISABLED) {
      try {
        const response = await fetch(DEFAULT_ROUTING_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            start_location: [startPoint.lat, startPoint.lng],
            end_location: [endPoint.lat, endPoint.lng],
          }),
        });

        if (!response.ok) {
          throw new Error(`Backend responded with ${response.status}`);
        }

        const data = await response.json();

        if (!data?.path || !Array.isArray(data.path) || data.path.length === 0) {
          throw new Error('Backend response did not contain a valid path');
        }

        setRoutePath(data.path);
        if (data.summary) {
          setRouteMeta({
            distance: data.summary.distance,
            duration: data.summary.duration,
            provider: 'backend',
          });
        }
        setMessage('Route found via MAS-FRO backend. Press Reset to try again.');
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
