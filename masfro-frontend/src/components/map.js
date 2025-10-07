// filename: components/Map.js
'use-client'; // This directive is necessary for React hooks

import { MapContainer, TileLayer, Marker, Polyline, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon issue with webpack
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// A helper component to handle map clicks
function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng);
    },
  });
  return null;
}

export default function Map({ startPoint, endPoint, routePath, onMapClick }) {
  const marikinaPosition = [14.6507, 121.1029]; // Center of Marikina City

  return (
    <MapContainer center={marikinaPosition} zoom={14} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      <MapClickHandler onMapClick={onMapClick} />
      
      {/* Display marker for the start point */}
      {startPoint && <Marker position={[startPoint.lat, startPoint.lng]} />}
      
      {/* Display marker for the end point */}
      {endPoint && <Marker position={[endPoint.lat, endPoint.lng]} />}

      {/* Display the calculated route path */}
      {routePath && <Polyline positions={routePath} color="blue" />}
    </MapContainer>
  );
}