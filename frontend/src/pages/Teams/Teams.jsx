import { useEffect, useState } from 'react';
import { getTeams } from '../../services/api';
import { Users, MapPin, Phone, RefreshCw } from 'lucide-react';

const STATUS_COLORS = {
  deployed:   { color:'#10b981', bg:'rgba(16,185,129,0.1)' },
  standby:    { color:'#3b82f6', bg:'rgba(59,130,246,0.1)' },
  'in-transit': { color:'#f59e0b', bg:'rgba(245,158,11,0.1)' },
  transit:    { color:'#f59e0b', bg:'rgba(245,158,11,0.1)' },
  offline:    { color:'#64748b', bg:'rgba(100,116,139,0.1)' },
};

export default function Teams() {
  const [teams, setTeams]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  const load = () => {
    setLoading(true);
    getTeams().then(setTeams).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = filter === 'all' ? teams : teams.filter(t => t.status === filter);

  const counts = {};
  teams.forEach(t => { counts[t.status] = (counts[t.status] || 0) + 1; });

  return (
    <div>
      <div className="topbar">
        <div className="topbar-title">
          <h2>Field Teams</h2>
          <p>{teams.length} teams • {teams.reduce((a, t) => a + (t.members||0), 0)} total personnel</p>
        </div>
        <div className="topbar-actions">
          {['all','deployed','standby','transit','offline'].map(s => (
            <button key={s}
              className={`btn btn-sm ${filter === s ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setFilter(s)}>
              {s.charAt(0).toUpperCase()+s.slice(1)}
              {s !== 'all' && ` (${counts[s] || 0})`}
            </button>
          ))}
          <button className="btn btn-ghost btn-sm" onClick={load}><RefreshCw size={13} /></button>
        </div>
      </div>

      <div className="page-container">
        {loading ? (
          <div className="loading-screen"><div className="spinner" /></div>
        ) : (
          <div className="grid-auto">
            {filtered.map(team => {
              const s = STATUS_COLORS[team.status] || STATUS_COLORS.offline;
              return (
                <div key={team.id} className="card" style={{ borderTop:`2px solid ${s.color}` }}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:14 }}>
                    <div>
                      <div style={{ fontWeight:700, color:'#f1f5f9', fontSize:15 }}>{team.team_name}</div>
                      <div style={{ fontSize:11, color:'#64748b', marginTop:2, fontFamily:'monospace' }}>
                        {team.team_code}
                      </div>
                    </div>
                    <span style={{
                      display:'inline-flex', alignItems:'center', padding:'4px 10px',
                      borderRadius:20, fontSize:11, fontWeight:600, textTransform:'capitalize',
                      background: s.bg, color: s.color,
                      border:`1px solid ${s.color}30`
                    }}>
                      <span style={{ width:5, height:5, borderRadius:'50%', background:s.color,
                        marginRight:5, display:'inline-block' }} />
                      {team.status}
                    </span>
                  </div>

                  <div style={{ display:'flex', flexDirection:'column', gap:8, fontSize:12 }}>
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <Users size={13} color="#64748b" />
                      <span style={{ color:'#94a3b8' }}>
                        <strong style={{ color:'#f1f5f9' }}>{team.members}</strong> personnel
                      </span>
                    </div>

                    {team.location_txt && (
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <MapPin size={13} color="#64748b" />
                        <span style={{ color:'#94a3b8' }}>{team.location_txt}</span>
                      </div>
                    )}

                    {team.lead_name && (
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <Users size={13} color="#64748b" />
                        <span style={{ color:'#94a3b8' }}>Lead: <strong style={{ color:'#f1f5f9' }}>
                          {team.lead_name}
                        </strong></span>
                      </div>
                    )}

                    {team.lead_phone && (
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <Phone size={13} color="#64748b" />
                        <span style={{ color:'#94a3b8' }}>{team.lead_phone}</span>
                      </div>
                    )}

                    {team.zone_id && (
                      <div style={{ marginTop:4, padding:'6px 10px',
                        background:'rgba(59,130,246,0.08)', borderRadius:6,
                        fontSize:11, color:'#3b82f6', border:'1px solid rgba(59,130,246,0.2)' }}>
                        Assigned to Zone #{team.zone_id}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="empty-state" style={{ gridColumn:'1/-1' }}>
                <Users size={32} /><p>No teams found for filter: {filter}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
