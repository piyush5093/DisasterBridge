import { useEffect, useState } from 'react';
import { getZones, optimizeZone, optimizeAll } from '../../services/api';
import { Zap, AlertTriangle, CheckCircle, Clock, Navigation, Package } from 'lucide-react';

const SEVERITY_COLORS = {
  critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#10b981'
};

function AllocationPlan({ plan, zone }) {
  if (!plan) return null;

  const isFeasible = plan.feasible !== false;

  return (
    <div style={{
      background: isFeasible ? 'rgba(16,185,129,0.05)' : 'rgba(239,68,68,0.05)',
      border: `1px solid ${isFeasible ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
      borderRadius: 12, padding: 20, marginTop: 16
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
        {isFeasible
          ? <CheckCircle size={20} color="#10b981" />
          : <AlertTriangle size={20} color="#ef4444" />}
        <div>
          <div style={{ fontWeight:700, color:'#f1f5f9' }}>
            {isFeasible ? 'Allocation Plan Ready' : 'Infeasible — No Depots/Resources'}
          </div>
          {zone && <div style={{ fontSize:12, color:'#64748b' }}>Zone: {zone.name}</div>}
        </div>
      </div>

      {isFeasible && (
        <>
          <div className="grid-3" style={{ marginBottom:16 }}>
            {[
              { label:'Nearest Depot', value:`#${plan.depot_id}`, icon:<Navigation size={14} /> },
              { label:'Distance', value:`${plan.distance_km?.toFixed(0)} km`, icon:<Navigation size={14} /> },
              { label:'ETA', value:`${plan.estimated_hours?.toFixed(1)} hrs`, icon:<Clock size={14} /> },
            ].map(({ label, value, icon }) => (
              <div key={label} style={{
                background:'rgba(255,255,255,0.04)', borderRadius:8, padding:'12px 14px'
              }}>
                <div style={{ display:'flex', alignItems:'center', gap:6, color:'#64748b', fontSize:11, marginBottom:6 }}>
                  {icon}{label}
                </div>
                <div style={{ fontWeight:700, color:'#f1f5f9', fontSize:18 }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Dispatched Resources */}
          {(plan.resources || plan.dispatched) && (
            <div>
              <div style={{ fontSize:12, color:'#94a3b8', fontWeight:600, marginBottom:10,
                textTransform:'uppercase', letterSpacing:'0.5px' }}>
                <Package size={12} style={{ verticalAlign:'middle', marginRight:4 }} />
                Dispatching Resources
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
                {/* Handle both list format and dict format */}
                {(plan.resources || []).map((r, i) => (
                  <div key={i} style={{
                    background:'rgba(59,130,246,0.1)', border:'1px solid rgba(59,130,246,0.2)',
                    borderRadius:8, padding:'8px 14px', fontSize:12
                  }}>
                    <div style={{ color:'#64748b', textTransform:'capitalize' }}>{r.category || r.name}</div>
                    <div style={{ color:'#3b82f6', fontWeight:700, fontSize:16 }}>
                      {(r.quantity || r.dispatched || 0).toLocaleString()}
                      <span style={{ fontSize:11, fontWeight:400, marginLeft:3 }}>{r.unit || 'units'}</span>
                    </div>
                    {r.fulfillment_pct !== undefined && (
                      <div style={{ fontSize:10, color:'#64748b', marginTop:2 }}>
                        {r.fulfillment_pct.toFixed(0)}% fulfilled
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {plan.warnings?.length > 0 && (
            <div style={{ marginTop:12 }}>
              {plan.warnings.map((w, i) => (
                <div key={i} style={{
                  display:'flex', alignItems:'center', gap:8, fontSize:12,
                  color:'#f59e0b', padding:'6px 0', borderBottom:'1px solid rgba(255,255,255,0.04)'
                }}>
                  <AlertTriangle size={12} />
                  {w}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function Allocation() {
  const [zones, setZones]       = useState([]);
  const [selected, setSelected] = useState('');
  const [plan, setPlan]         = useState(null);
  const [allPlans, setAllPlans] = useState(null);
  const [loading, setLoading]   = useState(false);
  const [loadingAll, setLoadingAll] = useState(false);
  const [error, setError]       = useState('');

  useEffect(() => {
    getZones().then(z => {
      setZones(z);
      if (z.length > 0) setSelected(String(z[0].id));
    }).catch(console.error);
  }, []);

  const handleOptimize = async () => {
    if (!selected) return;
    setLoading(true); setError(''); setPlan(null);
    try {
      const result = await optimizeZone(Number(selected));
      setPlan(result.allocation_plan);
    } catch (e) {
      setError(e.response?.data?.detail || 'Optimization failed — no depots or resources available');
    } finally {
      setLoading(false);
    }
  };

  const handleOptimizeAll = async () => {
    setLoadingAll(true); setError(''); setAllPlans(null);
    try {
      const result = await optimizeAll('critical');
      setAllPlans(result);
    } catch (e) {
      setError(e.response?.data?.detail || 'Batch optimization failed');
    } finally {
      setLoadingAll(false);
    }
  };

  const selectedZone = zones.find(z => String(z.id) === selected);
  const criticalZones = zones.filter(z => z.severity === 'critical');

  return (
    <div>
      <div className="topbar">
        <div className="topbar-title">
          <h2>Resource Allocation Optimizer</h2>
          <p>AI-powered greedy allocation using Haversine routing</p>
        </div>
        <div className="topbar-actions">
          <button
            className="btn btn-danger btn-sm"
            onClick={handleOptimizeAll}
            disabled={loadingAll || criticalZones.length === 0}>
            <Zap size={13} />
            {loadingAll ? 'Optimizing...' : `Optimize All Critical (${criticalZones.length})`}
          </button>
        </div>
      </div>

      <div className="page-container">
        <div className="grid-2" style={{ alignItems:'start' }}>
          {/* Left — Single Zone Optimizer */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><Zap size={14} /> Single Zone Optimization</span>
            </div>

            <div style={{ marginBottom:16 }}>
              <label style={{ fontSize:12, color:'#64748b', display:'block', marginBottom:6 }}>
                Select Disaster Zone
              </label>
              <select value={selected} onChange={e => { setSelected(e.target.value); setPlan(null); }}
                style={{
                  width:'100%', padding:'10px 12px',
                  background:'#1a2235', border:'1px solid rgba(255,255,255,0.1)',
                  borderRadius:8, color:'#f1f5f9', fontSize:13, outline:'none'
                }}>
                {zones.map(z => (
                  <option key={z.id} value={String(z.id)}>
                    [{z.severity?.toUpperCase()}] {z.name} — {z.state}
                  </option>
                ))}
              </select>
            </div>

            {/* Selected Zone Info */}
            {selectedZone && (
              <div style={{
                background:'rgba(255,255,255,0.03)', borderRadius:8, padding:14,
                marginBottom:16, border:'1px solid var(--border)'
              }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <div>
                    <div style={{ fontWeight:600, color:'#f1f5f9' }}>{selectedZone.name}</div>
                    <div style={{ fontSize:12, color:'#64748b', marginTop:2 }}>
                      {selectedZone.disaster_type} • {selectedZone.state}
                    </div>
                  </div>
                  <div style={{ textAlign:'right' }}>
                    <span className={`badge badge-${selectedZone.severity}`}>{selectedZone.severity}</span>
                    <div style={{ fontSize:11, color:'#64748b', marginTop:4 }}>
                      👥 {(selectedZone.population_affected||0).toLocaleString()} affected
                    </div>
                  </div>
                </div>
              </div>
            )}

            <button className="btn btn-primary" style={{ width:'100%' }}
              onClick={handleOptimize} disabled={loading || !selected}>
              <Zap size={14} />
              {loading ? 'Running Optimizer...' : 'Optimize Resource Allocation'}
            </button>

            {error && (
              <div style={{
                marginTop:12, padding:'10px 14px', background:'rgba(239,68,68,0.1)',
                border:'1px solid rgba(239,68,68,0.3)', borderRadius:8,
                fontSize:12, color:'#ef4444', display:'flex', gap:8, alignItems:'center'
              }}>
                <AlertTriangle size={13} />{error}
              </div>
            )}

            {plan && <AllocationPlan plan={plan} zone={selectedZone} />}
          </div>

          {/* Right — All Critical Batch */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><AlertTriangle size={14} /> Batch — Critical Zones</span>
              <span className="badge badge-critical">{criticalZones.length} zones</span>
            </div>

            {!allPlans ? (
              <div style={{ textAlign:'center', padding:'40px 0', color:'#475569' }}>
                <Zap size={40} style={{ marginBottom:12, opacity:0.3 }} />
                <p style={{ fontSize:13 }}>Click "Optimize All Critical" to generate batch allocation plans</p>
                <p style={{ fontSize:11, marginTop:8 }}>
                  Processes all critical zones in priority order
                </p>
              </div>
            ) : (
              <div>
                <div style={{ fontSize:12, color:'#64748b', marginBottom:16 }}>
                  {allPlans.total_zones} zones processed
                  • {allPlans.plans?.filter(p => p.feasible !== false).length} feasible
                </div>
                <div style={{ display:'flex', flexDirection:'column', gap:10, maxHeight:500, overflowY:'auto' }}>
                  {(allPlans.plans || []).map((p, i) => (
                    <div key={i} style={{
                      padding:'12px 14px',
                      background: p.feasible !== false ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)',
                      border: `1px solid ${p.feasible !== false ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                      borderRadius:8
                    }}>
                      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
                        <div style={{ fontWeight:600, color:'#f1f5f9', fontSize:13 }}>
                          Zone #{p.zone_id}
                        </div>
                        <div style={{ display:'flex', gap:8, fontSize:12 }}>
                          {p.feasible !== false ? (
                            <>
                              <span style={{ color:'#06b6d4' }}>
                                <Navigation size={11} style={{ verticalAlign:'middle', marginRight:3 }} />
                                {p.distance_km?.toFixed(0)} km
                              </span>
                              <span style={{ color:'#f59e0b' }}>
                                <Clock size={11} style={{ verticalAlign:'middle', marginRight:3 }} />
                                {p.estimated_hours?.toFixed(1)}h
                              </span>
                            </>
                          ) : (
                            <span style={{ color:'#ef4444', fontSize:11 }}>Infeasible</span>
                          )}
                        </div>
                      </div>
                      {p.warnings?.length > 0 && (
                        <div style={{ fontSize:11, color:'#f59e0b' }}>
                          ⚠ {p.warnings[0]}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Algorithm Info */}
        <div className="card" style={{ marginTop:20 }}>
          <div className="card-header">
            <span className="card-title">About the Optimizer</span>
          </div>
          <div className="grid-3">
            {[
              { title:'Algorithm', desc:'Greedy heuristic — selects nearest depot first, allocates available resources to meet predicted demand', icon:'⚙️' },
              { title:'Routing', desc:'Haversine formula for great-circle distance calculation between zone and depot coordinates', icon:'📐' },
              { title:'Priority', desc:'Critical zones processed first, then High → Medium → Low. ETA = distance ÷ 60 km/h', icon:'🎯' },
            ].map(({ title, desc, icon }) => (
              <div key={title} style={{
                padding:'14px 16px', background:'rgba(255,255,255,0.03)',
                borderRadius:8, border:'1px solid var(--border)'
              }}>
                <div style={{ fontSize:20, marginBottom:8 }}>{icon}</div>
                <div style={{ fontWeight:600, color:'#f1f5f9', marginBottom:4 }}>{title}</div>
                <div style={{ fontSize:12, color:'#64748b', lineHeight:1.6 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
