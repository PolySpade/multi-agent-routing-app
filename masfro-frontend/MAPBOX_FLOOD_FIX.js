// FLOOD MAP ALIGNMENT FIX for MapboxMap.js
// Replace lines 386-531 with this improved version

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

    const tiffUrl = `${BACKEND_API_URL}/data/timed_floodmaps/rr01/rr01-${floodTimeStep}.tif`;
    console.log('Fetching TIFF from:', tiffUrl);

    const response = await fetch(tiffUrl);

    if (!response.ok) {
      console.error(`Failed to fetch flood map: ${response.status}`);
      return;
    }

    const arrayBuffer = await response.arrayBuffer();
    const tiff = await fromBlob(new Blob([arrayBuffer]));
    const image = await tiff.getImage();
    const width = image.getWidth();
    const height = image.getHeight();

    // =================================================================
    // MANUAL MARIKINA CITY BOUNDING BOX (EPSG:4326)
    // =================================================================
    // This fixes the alignment issue by using known Marikina boundaries
    // instead of relying on potentially incorrect TIFF metadata

    const MARIKINA_BOUNDS = {
      // Main flood-prone area of Marikina City
      west:  121.0850,  // Western boundary (longitude)
      east:  121.1150,  // Eastern boundary (longitude)
      south:  14.6400,  // Southern boundary (latitude)
      north:  14.7300   // Northern boundary (latitude)
    };

    console.log('Using MANUAL Marikina bounds:', MARIKINA_BOUNDS);

    // Create coordinate array for Mapbox (clockwise from top-left)
    const reprojectedCoords = [
      [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.north],  // top-left
      [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.north],  // top-right
      [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.south],  // bottom-right
      [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.south]   // bottom-left
    ];

    console.log('Flood map coordinates:', reprojectedCoords);

    // =================================================================
    // Process raster data (same as before)
    // =================================================================

    const rasters = await image.readRasters();
    if (isCancelled) return;

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(width, height);

    const data = rasters[0];
    let minVal = Infinity;
    let maxVal = -Infinity;

    for (let i = 0; i < data.length; i++) {
      const value = data[i];
      if (value > 0) {
        minVal = Math.min(minVal, value);
        maxVal = Math.max(maxVal, value);
      }
    }

    console.log('Flood depth range:', minVal, 'to', maxVal, 'meters');

    // Create blue flood visualization
    for (let i = 0; i < data.length; i++) {
      const value = data[i];
      const pixelIndex = i * 4;

      if (value > 0) {
        const normalized = maxVal > minVal ? (value - minVal) / (maxVal - minVal) : 0;
        const grayValue = Math.floor((1 - normalized) * 255);
        const blueMultiplier = 0.7;

        imageData.data[pixelIndex] = Math.floor(grayValue * 0.3 * blueMultiplier);
        imageData.data[pixelIndex + 1] = Math.floor(grayValue * 0.5 * blueMultiplier);
        imageData.data[pixelIndex + 2] = Math.floor(grayValue * blueMultiplier);
        imageData.data[pixelIndex + 3] = Math.floor(200 * (0.3 + normalized * 0.7));
      } else {
        imageData.data[pixelIndex + 3] = 0;
      }
    }

    ctx.putImageData(imageData, 0, 0);

    if (isCancelled || !mapRef.current) return;

    // Add flood layer to map
    mapRef.current.addSource(floodLayerId, {
      type: 'image',
      url: canvas.toDataURL(),
      coordinates: reprojectedCoords
    });

    const layers = mapRef.current.getStyle().layers;
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
    }, firstSymbolId);

    if (mapRef.current.getLayer('route')) {
      mapRef.current.moveLayer('route');
    }

    console.log('FLOOD MAP LOADED SUCCESSFULLY with manual Marikina bounds');

  } catch (error) {
    console.warn('Flood map loading failed:', error.message);
  }
};
