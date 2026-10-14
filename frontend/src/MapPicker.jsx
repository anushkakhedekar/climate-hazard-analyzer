import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import icon from "leaflet/dist/images/marker-icon.png";
import shadow from "leaflet/dist/images/marker-shadow.png";

L.Marker.prototype.options.icon = L.icon({ iconUrl: icon, shadowUrl: shadow, iconAnchor: [12, 41] });

function Clicker({ onPick }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) });
  return null;
}
function Fly({ pos }) {
  const map = useMap();
  useEffect(() => { map.flyTo(pos, Math.max(map.getZoom(), 5)); }, [pos[0], pos[1]]);
  return null;
}

export default function MapPicker({ lat, lon, onPick }) {
  return (
    <MapContainer center={[lat, lon]} zoom={5} style={{ height: 320, borderRadius: 8 }}>
      <TileLayer attribution="© OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <Marker position={[lat, lon]} />
      <Clicker onPick={onPick} />
      <Fly pos={[lat, lon]} />
    </MapContainer>
  );
}