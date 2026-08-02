import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip as MapTooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { getZones, getDepots } from '../../services/api';
import { AlertTriangle, Building2 } from 'lucide-react';

const SEVERITY_COLORS = {
  critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#10b981'
};

const SEVERITY_RADIUS = {
  critical: 18, high: 14, medium: 10, low: 7
};

// Dark map tiles
const MAP_TILE = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org">OSM</a> &copy; <a href="https://carto.com">CARTO</a>';

export default function MapView() {
  const [zones,  setZones]  = useState([]);
  const [depots, setDepots] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getZones(), getDepots()])
      .then(([z, d]) => { setZones(z); setDepots(d); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === 'all' ? zones : zones.filter(z => z.severity === filter);

  const counts = {
    critical: zones.filter(z => z.severity === 'critical').length,
    high:     zones.filter(z => z.severity === 'high').length,
    medium:   zones.filter(z => z.severity === 'medium').length,
    low:      zones.filter(z => z.severity === 'low').length,
  };

  return (
    <div>
      <div className="topbar">
        <div className="topbar-title">
          <h2>Live Disaster Map</h2>
          <p>India — Real-time disaster zone visualization</p>
        </div>
        <div className="topbar-actions">
          {/* Severity filter buttons */}
          {['all','critical','high','medium','low'].map(s => (
            <button key={s}
              className={`btn btn-sm ${filter === s ? 'btn-primary' : 'btn-ghost'}`}
              style={filter !== s && s !== 'all' ? { color: SEVERITY_COLORS[s] } : {}}
              onClick={() => setFilter(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
              {s !== 'all' && ` (${counts[s] || 0})`}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: '16px 24px', position: 'relative' }}>
        {/* Legend */}
        <div style={{
          position:'absolute', top:28, right:36, zIndex:1000,
          background:'rgba(17,24,39,0.95)', border:'1px solid rgba(255,255,255,0.1)',
          borderRadius:10, padding:'12px 16px', fontSize:12, display:'flex', flexDirection:'column', gap:8
        }}>
          <div style={{ color:'#94a3b8', fontWeight:600, marginBottom:4, fontSize:11, textTransform:'uppercase' }}>
            Legend
          </div>
          {Object.entries(SEVERITY_COLORS).map(([sev, color]) => (
            <div key={sev} style={{ display:'flex', alignItems:'center', gap:8 }}>
              <div style={{ width:12, height:12, borderRadius:'50%', background:color, opacity:0.85 }} />
              <span style={{ color:'#94a3b8', textTransform:'capitalize' }}>{sev} ({counts[sev] || 0})</span>
            </div>
          ))}
          <div className="divider" />
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <div style={{ width:12, height:12, borderRadius:'50%', background:'#3b82f6',
              border:'2px dashed #3b82f6', opacity:0.6 }} />
            <span style={{ color:'#94a3b8' }}>Depots ({depots.length})</span>
          </div>
        </div>

        {loading ? (
          <div className="loading-screen"><div className="spinner" /><p>Loading map data...</p></div>
        ) : (
          <div className="map-container">
            <MapContainer
              center={[22.5, 82.0]}
              zoom={5}
              style={{ height: '100%', width: '100%' }}
              zoomControl={true}
            >
              <TileLayer url={MAP_TILE} attribution={MAP_ATTRIBUTION} />

              {/* Disaster Zones */}
              {filtered.map((zone) => (
                <CircleMarker
                  key={zone.id}
                  center={[zone.latitude, zone.longitude]}
                  radius={SEVERITY_RADIUS[zone.severity] || 10}
                  pathOptions={{
                    color: SEVERITY_COLORS[zone.severity],
                    fillColor: SEVERITY_COLORS[zone.severity],
                    fillOpacity: 0.65,
                    weight: 2,
                  }}
                >
                  <MapTooltip permanent={false} direction="top">
                    <div style={{ fontSize: 12, fontWeight: 600 }}>
                      {zone.name}
                    </div>
                  </MapTooltip>
                  <Popup>
                    <div className="zone-popup">
                      <h4>{zone.name}</h4>
                      <p>📍 {zone.state}{zone.district ? `, ${zone.district}` : ''}</p>
                      <p>🌊 Type: <strong>{zone.disaster_type}</strong></p>
                      <p>🔴 Severity: <strong style={{ color: SEVERITY_COLORS[zone.severity] }}>
                        {zone.severity?.toUpperCase()} ({zone.severity_score})
                      </strong></p>
                      <p>👥 Affected: <strong>{(zone.population_affected||0).toLocaleString()}</strong></p>
                      <p>📊 Vulnerability: {((zone.vulnerability_index||0)*100).toFixed(0)}%</p>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}

              {/* Depots */}
              {depots.map((depot) => (
                <CircleMarker
                  key={`depot-${depot.id}`}
                  center={[depot.latitude, depot.longitude]}
                  radius={8}
                  pathOptions={{
                    color: '#3b82f6',
                    fillColor: '#3b82f6',
                    fillOpacity: 0.4,
                    weight: 2,
                    dashArray: '4 2',
                  }}
                >
                  <Popup>
                    <div className="zone-popup">
                      <h4>🏭 {depot.name}</h4>
                      <p>📍 {depot.city}, {depot.state}</p>
                      <p>📦 Capacity: {(depot.capacity_units||0).toLocaleString()} units</p>
                      {depot.contact_name && <p>👤 {depot.contact_name}</p>}
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        )}
      </div>
    </div>
  );
}
