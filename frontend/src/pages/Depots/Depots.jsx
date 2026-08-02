import { useEffect, useState } from 'react';
import { getDepots } from '../../services/api';
import { Building2, MapPin, Phone, Package } from 'lucide-react';

export default function Depots() {
  const [depots, setDepots] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDepots().then(setDepots).catch(console.error).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="topbar">
        <div className="topbar-title">
          <h2>Resource Depots</h2>
          <p>{depots.length} active supply depots across India</p>
        </div>
      </div>
      <div className="page-container">
        {loading ? (
          <div className="loading-screen"><div className="spinner" /></div>
        ) : (
          <div className="grid-auto">
            {depots.map(depot => (
              <div key={depot.id} className="card" style={{
                borderTop: '2px solid #3b82f6', transition: 'all 0.2s'
              }}>
                <div style={{ display:'flex', alignItems:'flex-start', gap:12, marginBottom:16 }}>
                  <div style={{
                    width:44, height:44, borderRadius:12,
                    background:'rgba(59,130,246,0.15)', display:'flex',
                    alignItems:'center', justifyContent:'center', flexShrink:0
                  }}>
                    <Building2 size={20} color="#3b82f6" />
                  </div>
                  <div>
                    <div style={{ fontWeight:700, color:'#f1f5f9', fontSize:15 }}>{depot.name}</div>
                    <div style={{ display:'flex', alignItems:'center', gap:4,
                      fontSize:12, color:'#64748b', marginTop:2 }}>
                      <MapPin size={11} />{depot.city}, {depot.state}
                    </div>
                  </div>
                </div>

                <div style={{ display:'flex', flexDirection:'column', gap:8, fontSize:13 }}>
                  <div style={{ display:'flex', justifyContent:'space-between' }}>
                    <span style={{ color:'#64748b' }}>Capacity</span>
                    <span style={{ color:'#f1f5f9', fontWeight:600 }}>
                      <Package size={12} style={{ verticalAlign:'middle', marginRight:4 }} />
                      {(depot.capacity_units||0).toLocaleString()} units
                    </span>
                  </div>
                  {depot.contact_name && (
                    <div style={{ display:'flex', justifyContent:'space-between' }}>
                      <span style={{ color:'#64748b' }}>Contact</span>
                      <span style={{ color:'#94a3b8' }}>{depot.contact_name}</span>
                    </div>
                  )}
                  {depot.contact_phone && (
                    <div style={{ display:'flex', justifyContent:'space-between' }}>
                      <span style={{ color:'#64748b' }}>Phone</span>
                      <span style={{ color:'#94a3b8', display:'flex', alignItems:'center', gap:4 }}>
                        <Phone size={11} />{depot.contact_phone}
                      </span>
                    </div>
                  )}
                  <div style={{ display:'flex', justifyContent:'space-between' }}>
                    <span style={{ color:'#64748b' }}>Coordinates</span>
                    <span style={{ color:'#475569', fontSize:11, fontFamily:'monospace' }}>
                      {depot.latitude?.toFixed(3)}, {depot.longitude?.toFixed(3)}
                    </span>
                  </div>
                </div>

                <div style={{ marginTop:16, paddingTop:12, borderTop:'1px solid var(--border)' }}>
                  <span className={`badge ${depot.is_active ? 'badge-low' : 'badge-critical'}`}>
                    {depot.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
