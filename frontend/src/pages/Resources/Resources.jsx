import { useEffect, useState } from 'react';
import { getResources, getResourceSummary, getResourceAlerts } from '../../services/api';
import { Package, AlertTriangle, RefreshCw, Search } from 'lucide-react';

const CAT_COLORS = {
  food:'#10b981', water:'#06b6d4', medical:'#ef4444',
  shelter:'#8b5cf6', transport:'#f97316', equipment:'#f59e0b'
};

function UtilBar({ available, total, threshold }) {
  const pct = total > 0 ? ((available / total) * 100).toFixed(0) : 0;
  const isCritical = pct < threshold * 100;
  const color = isCritical ? '#ef4444' : pct < 50 ? '#f59e0b' : '#10b981';
  return (
    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
      <div className="progress-bar" style={{ flex:1 }}>
        <div className="progress-fill" style={{ width:`${pct}%`, background:color }} />
      </div>
      <span style={{ fontSize:11, color, fontWeight:600, minWidth:32 }}>{pct}%</span>
    </div>
  );
}

export default function Resources() {
  const [resources, setResources] = useState([]);
  const [summary,   setSummary]   = useState(null);
  const [alerts,    setAlerts]    = useState(null);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState('');
  const [catFilter, setCatFilter] = useState('all');

  const load = () => {
    setLoading(true);
    Promise.all([getResources(), getResourceSummary(), getResourceAlerts()])
      .then(([r, s, a]) => { setResources(r); setSummary(s); setAlerts(a); })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const categories = [...new Set(resources.map(r => r.category))];

  const filtered = resources.filter(r => {
    const matchSearch = r.name.toLowerCase().includes(search.toLowerCase());
    const matchCat    = catFilter === 'all' || r.category === catFilter;
    return matchSearch && matchCat;
  });

  return (
    <div>
      <div className="topbar">
        <div className="topbar-title">
          <h2>Resource Inventory</h2>
          <p>{resources.length} items tracked across {summary?.total_categories || 0} categories</p>
        </div>
        <div className="topbar-actions">
          {alerts?.count > 0 && (
            <div style={{ display:'flex', alignItems:'center', gap:6, fontSize:12,
              color:'#ef4444', background:'rgba(239,68,68,0.1)',
              padding:'6px 12px', borderRadius:20, border:'1px solid rgba(239,68,68,0.3)',
              animation:'alert-pulse 2s infinite' }}>
              <AlertTriangle size={13} /> {alerts.count} Critical Alerts
            </div>
          )}
          <button className="btn btn-ghost btn-sm" onClick={load}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      <div className="page-container">
        {/* Summary Cards by Category */}
        {summary && (
          <div className="grid-auto" style={{ marginBottom:20 }}>
            {(summary.categories || []).map((cat) => {
              const color = CAT_COLORS[cat.category] || '#3b82f6';
              const pct = cat.total > 0 ? Math.round(cat.available / cat.total * 100) : 0;
              return (
                <div key={cat.category} className="stat-card"
                  style={{ '--card-accent': color, cursor:'pointer' }}
                  onClick={() => setCatFilter(catFilter === cat.category ? 'all' : cat.category)}>
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                    <div>
                      <div style={{ fontSize:11, color:'#64748b', textTransform:'capitalize',
                        marginBottom:8, fontWeight:600, letterSpacing:'0.5px' }}>
                        {cat.category}
                      </div>
                      <div style={{ fontSize:26, fontWeight:800, color:'#f1f5f9' }}>
                        {(cat.available||0).toLocaleString()}
                        <span style={{ fontSize:12, color:'#64748b', marginLeft:4 }}>{cat.unit || 'units'}</span>
                      </div>
                      <div style={{ fontSize:11, color:'#475569', marginTop:2 }}>
                        of {(cat.total||0).toLocaleString()} total
                      </div>
                    </div>
                    <div style={{ fontSize:22, fontWeight:800, color,
                      background:`${color}15`, padding:'8px 12px', borderRadius:10 }}>
                      {pct}%
                    </div>
                  </div>
                  <div className="progress-bar" style={{ marginTop:12 }}>
                    <div className="progress-fill" style={{ width:`${pct}%`, background:color }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Critical Alerts */}
        {alerts?.count > 0 && (
          <div className="card" style={{
            marginBottom:20, borderColor:'rgba(239,68,68,0.3)',
            background:'rgba(239,68,68,0.05)'
          }}>
            <div className="card-header">
              <span className="card-title" style={{ color:'#ef4444' }}>
                <AlertTriangle size={14} /> Critical Resources — Low Stock
              </span>
            </div>
            <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
              {(alerts.resources || []).map(r => (
                <div key={r.id} style={{
                  background:'rgba(239,68,68,0.1)', border:'1px solid rgba(239,68,68,0.25)',
                  borderRadius:8, padding:'8px 14px', fontSize:12
                }}>
                  <div style={{ color:'#f1f5f9', fontWeight:600 }}>{r.name}</div>
                  <div style={{ color:'#ef4444', marginTop:2 }}>
                    {(r.available_pct||0).toFixed(0)}% remaining
                    ({(r.quantity_available||0).toLocaleString()} {r.unit})
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Search & Filter */}
        <div style={{ display:'flex', gap:10, marginBottom:16, alignItems:'center' }}>
          <div style={{ position:'relative', flex:1, maxWidth:340 }}>
            <Search size={14} style={{ position:'absolute', left:10, top:'50%',
              transform:'translateY(-50%)', color:'#64748b' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search resources..."
              style={{
                width:'100%', padding:'8px 12px 8px 32px',
                background:'#1a2235', border:'1px solid rgba(255,255,255,0.07)',
                borderRadius:8, color:'#f1f5f9', fontSize:13, outline:'none'
              }} />
          </div>
          <select value={catFilter} onChange={e => setCatFilter(e.target.value)}
            style={{
              padding:'8px 12px', background:'#1a2235', border:'1px solid rgba(255,255,255,0.07)',
              borderRadius:8, color:'#94a3b8', fontSize:13, outline:'none'
            }}>
            <option value="all">All Categories</option>
            {categories.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase()+c.slice(1)}</option>)}
          </select>
        </div>

        {/* Table */}
        {loading ? (
          <div className="loading-screen"><div className="spinner" /></div>
        ) : (
          <div className="card" style={{ padding:0 }}>
            <div className="table-wrapper" style={{ border:'none' }}>
              <table>
                <thead>
                  <tr>
                    <th>Resource Name</th>
                    <th>Category</th>
                    <th>Unit</th>
                    <th>Available</th>
                    <th>Deployed</th>
                    <th>Total</th>
                    <th>Availability</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr><td colSpan={8}>
                      <div className="empty-state"><Package size={24} /><p>No resources found</p></div>
                    </td></tr>
                  ) : filtered.map(r => {
                    const color = CAT_COLORS[r.category] || '#3b82f6';
                    const pct = r.quantity_total > 0
                      ? (r.quantity_available / r.quantity_total * 100)
                      : 0;
                    const isCrit = pct < (r.critical_threshold || 0.2) * 100;
                    return (
                      <tr key={r.id}>
                        <td>
                          <div style={{ fontWeight:600, color:'#f1f5f9' }}>{r.name}</div>
                          {r.depot_id && <div style={{ fontSize:11, color:'#475569' }}>Depot #{r.depot_id}</div>}
                        </td>
                        <td>
                          <span style={{
                            display:'inline-flex', alignItems:'center',
                            padding:'2px 8px', borderRadius:4,
                            background:`${color}15`, color, fontSize:11, fontWeight:600,
                            textTransform:'capitalize', border:`1px solid ${color}30`
                          }}>{r.category}</span>
                        </td>
                        <td style={{ color:'#64748b' }}>{r.unit}</td>
                        <td style={{ color:'#f1f5f9', fontWeight:600 }}>
                          {(r.quantity_available||0).toLocaleString()}
                        </td>
                        <td style={{ color:'#94a3b8' }}>
                          {(r.quantity_deployed||0).toLocaleString()}
                        </td>
                        <td style={{ color:'#94a3b8' }}>
                          {(r.quantity_total||0).toLocaleString()}
                        </td>
                        <td style={{ minWidth:160 }}>
                          <UtilBar available={r.quantity_available}
                            total={r.quantity_total} threshold={r.critical_threshold||0.2} />
                        </td>
                        <td>
                          {isCrit
                            ? <span className="badge badge-critical">Critical</span>
                            : pct < 50
                              ? <span className="badge badge-medium">Low</span>
                              : <span className="badge badge-low">OK</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
