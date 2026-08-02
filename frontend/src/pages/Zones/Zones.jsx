import { useEffect, useState } from 'react';
import { getZones, getZoneDemand } from '../../services/api';
import { AlertTriangle, Search, RefreshCw, ChevronDown, Activity } from 'lucide-react';

const SEVERITY_COLORS = {
  critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#10b981'
};

function DemandModal({ zone, onClose }) {
  const [demand, setDemand] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getZoneDemand(zone.id)
      .then(d => setDemand(d.demand))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [zone.id]);

  const items = demand ? [
    { label: 'Food Packets',     value: demand.food_packets,    unit: 'pkts', icon: '🍱' },
    { label: 'Water',            value: demand.water_liters,    unit: 'L',    icon: '💧' },
    { label: 'Medical Kits',     value: demand.medical_kits,    unit: 'kits', icon: '🏥' },
    { label: 'Shelter Capacity', value: demand.shelter_capacity,unit: 'ppl',  icon: '🏕️' },
    { label: 'Rescue Vehicles',  value: demand.rescue_vehicles, unit: 'veh',  icon: '🚑' },
    { label: 'Personnel Needed', value: demand.personnel_needed,unit: 'ppl',  icon: '👷' },
  ] : [];

  return (
    <div style={{
      position:'fixed', inset:0, background:'rgba(0,0,0,0.7)',
      display:'flex', alignItems:'center', justifyContent:'center', zIndex:9999
    }}>
      <div style={{
        background:'#111827', border:'1px solid rgba(255,255,255,0.1)',
        borderRadius:16, padding:28, width:480, maxWidth:'90vw'
      }}>
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:20 }}>
          <div>
            <h3 style={{ color:'#f1f5f9', fontWeight:700 }}>ML Demand Prediction</h3>
            <p style={{ color:'#64748b', fontSize:12, marginTop:2 }}>{zone.name}</p>
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-sm">✕ Close</button>
        </div>

        {loading ? (
          <div className="loading-screen" style={{ minHeight:120 }}>
            <div className="spinner" /><p>Predicting demand...</p>
          </div>
        ) : (
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
            {items.map(({ label, value, unit, icon }) => (
              <div key={label} style={{
                background:'rgba(255,255,255,0.04)', borderRadius:10,
                padding:'14px 16px', border:'1px solid rgba(255,255,255,0.07)'
              }}>
                <div style={{ fontSize:20, marginBottom:8 }}>{icon}</div>
                <div style={{ fontSize:22, fontWeight:800, color:'#f1f5f9' }}>
                  {(value||0).toLocaleString()}
                  <span style={{ fontSize:12, color:'#64748b', marginLeft:4 }}>{unit}</span>
                </div>
                <div style={{ fontSize:11, color:'#64748b' }}>{label}</div>
              </div>
            ))}
          </div>
        )}
        <div style={{ marginTop:16, fontSize:11, color:'#475569', textAlign:'center' }}>
          Predicted by RandomForest ML model • Based on population & severity
        </div>
      </div>
    </div>
  );
}

export default function Zones() {
  const [zones, setZones]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]   = useState('');
  const [filter, setFilter]   = useState('all');
  const [selected, setSelected] = useState(null);

  const fetchZones = () => {
    setLoading(true);
    getZones().then(setZones).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { fetchZones(); }, []);

  const filtered = zones.filter(z => {
    const matchSearch = z.name.toLowerCase().includes(search.toLowerCase()) ||
      z.state?.toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === 'all' || z.severity === filter;
    return matchSearch && matchFilter;
  });

  const counts = { critical:0, high:0, medium:0, low:0 };
  zones.forEach(z => { if (counts[z.severity] !== undefined) counts[z.severity]++; });

  return (
    <div>
      <div className="topbar">
        <div className="topbar-title">
          <h2>Disaster Zones</h2>
          <p>{zones.length} zones tracked • {zones.filter(z=>z.is_active).length} active</p>
        </div>
        <div className="topbar-actions">
          <button className="btn btn-ghost btn-sm" onClick={fetchZones}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      <div className="page-container">
        {/* Severity Summary Cards */}
        <div className="grid-4" style={{ marginBottom:20 }}>
          {Object.entries(counts).map(([sev, count]) => (
            <div key={sev} onClick={() => setFilter(filter === sev ? 'all' : sev)}
              style={{
                background:'#111827', border:`1px solid ${filter===sev ? SEVERITY_COLORS[sev]+'44' : 'rgba(255,255,255,0.07)'}`,
                borderRadius:10, padding:'14px 18px', cursor:'pointer',
                borderTop:`2px solid ${SEVERITY_COLORS[sev]}`, transition:'all 0.2s'
              }}>
              <div style={{ fontSize:24, fontWeight:800, color: SEVERITY_COLORS[sev] }}>{count}</div>
              <div style={{ fontSize:12, color:'#64748b', textTransform:'capitalize', marginTop:2 }}>{sev}</div>
            </div>
          ))}
        </div>

        {/* Search & Filter */}
        <div style={{ display:'flex', gap:10, marginBottom:16, alignItems:'center' }}>
          <div style={{ position:'relative', flex:1, maxWidth:340 }}>
            <Search size={14} style={{ position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'#64748b' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search zones, states..."
              style={{
                width:'100%', padding:'8px 12px 8px 32px',
                background:'#1a2235', border:'1px solid rgba(255,255,255,0.07)',
                borderRadius:8, color:'#f1f5f9', fontSize:13, outline:'none'
              }} />
          </div>
          <select value={filter} onChange={e => setFilter(e.target.value)}
            style={{
              padding:'8px 12px', background:'#1a2235', border:'1px solid rgba(255,255,255,0.07)',
              borderRadius:8, color:'#94a3b8', fontSize:13, outline:'none'
            }}>
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Table */}
        {loading ? (
          <div className="loading-screen"><div className="spinner" /><p>Loading zones...</p></div>
        ) : (
          <div className="card" style={{ padding:0 }}>
            <div className="table-wrapper" style={{ border:'none' }}>
              <table>
                <thead>
                  <tr>
                    <th>Zone Name</th>
                    <th>State / District</th>
                    <th>Disaster</th>
                    <th>Severity</th>
                    <th>Score</th>
                    <th>Affected</th>
                    <th>Vulnerability</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr><td colSpan={8}>
                      <div className="empty-state"><AlertTriangle size={24} /><p>No zones found</p></div>
                    </td></tr>
                  ) : filtered.map(zone => (
                    <tr key={zone.id}>
                      <td>
                        <div style={{ fontWeight:600, color:'#f1f5f9', fontSize:13 }}>{zone.name}</div>
                        <div style={{ fontSize:11, color:'#475569' }}>ID #{zone.id}</div>
                      </td>
                      <td>{zone.state}{zone.district ? ` › ${zone.district}` : ''}</td>
                      <td>
                        <span className="tag" style={{ textTransform:'capitalize' }}>
                          {zone.disaster_type}
                        </span>
                      </td>
                      <td>
                        <span className={`badge badge-${zone.severity}`}>{zone.severity}</span>
                      </td>
                      <td>
                        <span style={{ fontFamily:'JetBrains Mono, monospace',
                          color: SEVERITY_COLORS[zone.severity], fontWeight:600 }}>
                          {zone.severity_score?.toFixed(1)}
                        </span>
                      </td>
                      <td style={{ color:'#f1f5f9' }}>
                        {(zone.population_affected||0).toLocaleString()}
                      </td>
                      <td>
                        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                          <div className="progress-bar" style={{ width:60 }}>
                            <div className="progress-fill" style={{
                              width:`${((zone.vulnerability_index||0)*100).toFixed(0)}%`,
                              background: zone.vulnerability_index > 0.6 ? '#ef4444' : '#f59e0b'
                            }} />
                          </div>
                          <span style={{ fontSize:11, color:'#64748b' }}>
                            {((zone.vulnerability_index||0)*100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td>
                        <button className="btn btn-ghost btn-sm"
                          onClick={() => setSelected(zone)}
                          style={{ color:'#3b82f6', fontSize:11 }}>
                          <Activity size={12} /> Demand
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {selected && <DemandModal zone={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
