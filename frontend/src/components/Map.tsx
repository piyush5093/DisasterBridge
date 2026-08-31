import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker, Tooltip } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import axios from 'axios';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const ALERT_COLORS: Record<string, string> = {
  red: '#ef4444', orange: '#f97316', low: '#eab308', green: '#22c55e'
};

interface EmbeddedMapProps {
  showSidePanel?: boolean;
}

export default function EmbeddedMap({ showSidePanel = false }: EmbeddedMapProps) {
  const center: [number, number] = [20.5937, 78.9629]; // India geographic centre
  const [events, setEvents]     = useState<any[]>([]);
  const [missions, setMissions] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [evRes, mRes] = await Promise.all([
          axios.get('http://localhost:8000/api/dashboard/events'),
          axios.get('http://localhost:8000/api/dashboard/missions'),
        ]);
        setEvents(evRes.data);
        setMissions(mRes.data);
      } catch (err) {
        console.error('Failed to fetch map data', err);
      }
    }
    fetchData();
  }, []);

  // Geometry helpers
  const getLeafletPositions = (geometry: any): [number, number][] => {
    if (!geometry || geometry.type !== 'LineString') return [];
    return geometry.coordinates.map((c: number[]) => [c[1], c[0]] as [number, number]);
  };

  // Only active (non-cancelled, non-pending) missions
  const activeMissions = missions.filter(m => !['cancelled', 'pending'].includes(m.status));

  const STATUS_COLOR: Record<string, string> = {
    assigned:   '#3b82f6',   // blue
    in_transit: '#6366f1',   // indigo
    delivered:  '#10b981',   // green
  };

  const mapEl = (
    <div className="h-full w-full rounded-lg overflow-hidden border shadow-sm z-0 relative">
      <MapContainer center={center} zoom={5} style={{ height: '100%', width: '100%', zIndex: 0 }}>
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Disaster event markers */}
        <MarkerClusterGroup chunkedLoading>
          {events.map((ev, idx) => (
            <CircleMarker
              key={idx}
              center={[ev.lat, ev.lng]}
              radius={5}
              pathOptions={{
                color: ALERT_COLORS[ev.alert_level] || '#94a3b8',
                fillColor: ALERT_COLORS[ev.alert_level] || '#94a3b8',
                fillOpacity: 0.7,
                weight: 1,
              }}
            >
              <Popup>
                <div className="text-xs">
                  <p className="font-bold text-slate-800">{ev.title || 'Disaster Event'}</p>
                  <p className="text-slate-500 mt-0.5">Alert: <span className="font-semibold uppercase">{ev.alert_level}</span></p>
                  <p className="text-slate-400">Source: {ev.source}</p>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MarkerClusterGroup>

        {/* Active Mission Routes with start/end markers */}
        {activeMissions.map((m, idx) => {
          if (!m.geometry) return null;
          const positions = getLeafletPositions(m.geometry);
          if (positions.length < 2) return null;

          const routeColor = STATUS_COLOR[m.status] || '#3b82f6';
          const isSelected = selected === m.id;
          const alertColor = ALERT_COLORS[m.alert_level] || '#94a3b8';

          const depotPos  = positions[0];
          const zonePos   = positions[positions.length - 1];
          const eventName = (m.event_type || 'unknown').replace('_', ' ');
          const alertName = (m.alert_level || '').toUpperCase();

          return (
            <React.Fragment key={`mission-${idx}`}>
              {/* Route polyline */}
              <Polyline
                positions={positions}
                pathOptions={{
                  color: isSelected ? '#f59e0b' : routeColor,
                  weight: isSelected ? 6 : 4,
                  opacity: 0.9,
                  dashArray: m.fallback ? '6, 6' : undefined,
                }}
                eventHandlers={{ click: () => setSelected(m.id === selected ? null : m.id) }}
              >
                <Tooltip sticky>
                  <div className="text-xs">
                    <p className="font-bold text-slate-800">{m.team} → {eventName} ({alertName})</p>
                    <p className="text-slate-600">Carrying: <strong>{m.supplies_display}</strong></p>
                    <p className="text-slate-500">Distance: {m.distance?.toFixed(1)} km · Est. {m.duration?.toFixed(0)} min</p>
                    <p className="text-slate-400 mt-0.5">Click route for details</p>
                  </div>
                </Tooltip>
                <Popup>
                  <div className="text-xs min-w-[180px]">
                    <p className="font-bold text-slate-800 text-sm mb-1">{m.team}</p>
                    <p className="text-slate-600">Vehicle: {m.vehicle_id}</p>
                    <p className="text-slate-600 mt-1">
                      <span className="font-semibold">Incident:</span> {eventName}
                      <span className="ml-1 px-1 py-0.5 rounded text-white text-[10px]" style={{ backgroundColor: alertColor }}>{alertName}</span>
                    </p>
                    <p className="text-slate-600"><span className="font-semibold">Carrying:</span> {m.supplies_display}</p>
                    <p className="text-slate-600"><span className="font-semibold">Distance:</span> {m.distance?.toFixed(1)} km</p>
                    <p className="text-slate-600"><span className="font-semibold">Est. time:</span> {m.duration?.toFixed(0)} min</p>
                    <p className="text-slate-600 capitalize"><span className="font-semibold">Status:</span> {m.status?.replace('_', ' ')}</p>
                    {m.fallback && <p className="text-amber-600 mt-1">⚠ Using straight-line fallback route</p>}
                  </div>
                </Popup>
              </Polyline>

              {/* Depot start marker (blue square) */}
              <CircleMarker
                center={depotPos}
                radius={8}
                pathOptions={{ color: '#1e40af', fillColor: '#3b82f6', fillOpacity: 1, weight: 2 }}
              >
                <Tooltip permanent={false}>
                  <span className="text-xs font-semibold">🏭 {m.depot_name || 'Supply Depot'}</span>
                </Tooltip>
                <Popup>
                  <div className="text-xs">
                    <p className="font-bold text-blue-800">🏭 Supply Depot</p>
                    <p className="text-slate-600">{m.depot_name}</p>
                    <p className="text-slate-500 mt-1">Dispatching: {m.supplies_display}</p>
                    <p className="text-slate-500">Team: {m.team}</p>
                  </div>
                </Popup>
              </CircleMarker>

              {/* Disaster zone end marker (red) */}
              <CircleMarker
                center={zonePos}
                radius={10}
                pathOptions={{
                  color: alertColor,
                  fillColor: alertColor,
                  fillOpacity: 0.8,
                  weight: 2,
                }}
              >
                <Tooltip permanent={false}>
                  <span className="text-xs font-semibold">⚠ {eventName} {alertName} Zone</span>
                </Tooltip>
                <Popup>
                  <div className="text-xs">
                    <p className="font-bold" style={{ color: alertColor }}>⚠ {eventName} Zone</p>
                    <p className="text-slate-600">Alert: <strong>{alertName}</strong></p>
                    <p className="text-slate-600">Severity: {m.severity?.toFixed(0)}</p>
                    <p className="text-slate-500 mt-1">Team en route: {m.team}</p>
                    <p className="text-slate-500">Carrying: {m.supplies_display}</p>
                  </div>
                </Popup>
              </CircleMarker>
            </React.Fragment>
          );
        })}
      </MapContainer>

      {/* Legend */}
      {activeMissions.length > 0 ? (
        <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur p-3 rounded-lg shadow-md border border-slate-200 z-[1000] text-xs">
          <h4 className="font-bold text-slate-800 mb-2">Map Legend</h4>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2"><div className="w-6 h-1 bg-blue-500 rounded" /> Active route (assigned)</div>
            <div className="flex items-center gap-2"><div className="w-6 h-1 bg-indigo-500 rounded" /> In transit</div>
            <div className="flex items-center gap-2"><div className="w-6 h-1 bg-green-500 rounded" /> Delivered</div>
            <div className="flex items-center gap-2"><div className="w-6 h-1 bg-amber-400 rounded" /> Selected route</div>
            <div className="flex items-center gap-2"><div className="w-4 h-4 rounded-full bg-blue-500 border-2 border-blue-800 flex-shrink-0" /> Supply depot (start)</div>
            <div className="flex items-center gap-2"><div className="w-4 h-4 rounded-full bg-red-500 flex-shrink-0" /> Disaster zone (destination)</div>
            <div className="flex items-center gap-2"><div className="w-4 h-4 rounded-full bg-slate-300 flex-shrink-0" /> Disaster events (clustered)</div>
          </div>
          <p className="text-slate-400 mt-2 border-t pt-1.5">Click any route or marker for details</p>
        </div>
      ) : (
        <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur px-3 py-2 rounded-lg shadow-sm border border-slate-200 z-[1000] text-xs text-slate-400 font-medium">
          No active delivery routes — dispatch missions from Active Incidents
        </div>
      )}
    </div>
  );

  return mapEl;
}
