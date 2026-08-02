import { useEffect, useState } from 'react';
import { getLiveFeed } from '../../services/api';
import { Radio, RefreshCw, Globe, Activity } from 'lucide-react';

const ALERT_COLORS = {
  Red:    { color:'#ef4444', bg:'rgba(239,68,68,0.12)', border:'rgba(239,68,68,0.3)' },
  Orange: { color:'#f97316', bg:'rgba(249,115,22,0.12)', border:'rgba(249,115,22,0.3)' },
  Green:  { color:'#10b981', bg:'rgba(16,185,129,0.12)', border:'rgba(16,185,129,0.3)' },
};

function EventCard({ event }) {
  const alertStyle = ALERT_COLORS[event.alertlevel] || ALERT_COLORS.Green;
  const isGdacs = event.source === 'GDACS';

  return (
    <div style={{
      background:'#111827', border:`1px solid ${alertStyle.border}`,
      borderRadius:10, padding:'14px 16px',
      borderLeft:`3px solid ${alertStyle.color}`
    }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:12 }}>
        <div style={{ flex:1 }}>
          <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
            <span style={{
              display:'inline-flex', padding:'2px 8px', borderRadius:4,
              background: isGdacs ? 'rgba(59,130,246,0.15)' : 'rgba(139,92,246,0.15)',
              color: isGdacs ? '#3b82f6' : '#8b5cf6', fontSize:10, fontWeight:700
            }}>
              {event.source || (isGdacs ? 'GDACS' : 'USGS')}
            </span>
            {event.eventtype && (
              <span className="tag" style={{ textTransform:'capitalize' }}>{event.eventtype}</span>
            )}
            {event.magnitude && (
              <span style={{ fontSize:12, color:'#f59e0b', fontWeight:700 }}>
                M {event.magnitude}
              </span>
            )}
          </div>
          <div style={{ fontWeight:600, color:'#f1f5f9', fontSize:14, marginBottom:4 }}>
            {event.title || event.place || event.name || 'Unknown Event'}
          </div>
          <div style={{ fontSize:12, color:'#64748b', display:'flex', gap:12, flexWrap:'wrap' }}>
            {event.country && <span>📍 {event.country}</span>}
            {event.fromdate && (
              <span>🕐 {new Date(event.fromdate).toLocaleDateString('en-IN', {
                day:'numeric', month:'short', year:'numeric'
              })}</span>
            )}
            {event.time && (
              <span>🕐 {new Date(event.time).toLocaleDateString('en-IN', {
                day:'numeric', month:'short', hour:'2-digit', minute:'2-digit'
              })}</span>
            )}
            {event.severity_category && (
              <span style={{ color:'#94a3b8' }}>Sev: {event.severity_category}</span>
            )}
          </div>
        </div>
        <div style={{
          display:'flex', flexDirection:'column', alignItems:'flex-end', gap:6, flexShrink:0
        }}>
          {event.alertlevel && (
            <span style={{
              padding:'4px 10px', borderRadius:20, fontSize:11, fontWeight:700,
              background: alertStyle.bg, color: alertStyle.color, border:`1px solid ${alertStyle.border}`
            }}>
              {event.alertlevel}
            </span>
          )}
          {(event.population_affected || event.affected_pop) && (
            <span style={{ fontSize:11, color:'#94a3b8' }}>
              👥 {Number(event.population_affected || event.affected_pop || 0).toLocaleString()} affected
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LiveFeed() {
  const [feed, setFeed]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState('all');
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = () => {
    setLoading(true);
    getLiveFeed()
      .then(d => { setFeed(d); setLastRefresh(new Date()); })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // Auto-refresh every 60 seconds
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  const gdacsEvents = feed?.gdacs?.events || [];
  const usgsEvents  = feed?.usgs?.events  || [];

  const allEvents = [
    ...gdacsEvents.map(e => ({ ...e, source:'GDACS' })),
    ...usgsEvents.map(e => ({ ...e, source:'USGS' })),
  ].sort((a, b) => {
    // Sort by date
    const da = new Date(a.fromdate || a.time || 0);
    const db = new Date(b.fromdate || b.time || 0);
    return db - da;
  });

  const displayed = source === 'all' ? allEvents
    : allEvents.filter(e => e.source === source);

  return (
    <div>
      <div className="topbar">
        <div className="topbar-title">
          <h2>Live Disaster Feed</h2>
          <p>
            GDACS ({gdacsEvents.length} events) + USGS ({usgsEvents.length} earthquakes)
            {lastRefresh && ` • Updated ${lastRefresh.toLocaleTimeString()}`}
          </p>
        </div>
        <div className="topbar-actions">
          {['all','GDACS','USGS'].map(s => (
            <button key={s}
              className={`btn btn-sm ${source === s ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setSource(s)}>
              {s === 'all' ? 'All' : s}
            </button>
          ))}
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="page-container">
        {/* Stats Row */}
        <div className="grid-4" style={{ marginBottom:20 }}>
          {[
            { label:'GDACS Events', value:gdacsEvents.length, icon:'🌍', color:'#3b82f6' },
            { label:'USGS Earthquakes', value:usgsEvents.length, icon:'🌋', color:'#8b5cf6' },
            {
              label:'Red Alerts',
              value: allEvents.filter(e => e.alertlevel === 'Red').length,
              icon:'🔴', color:'#ef4444'
            },
            {
              label:'Total Events',
              value: allEvents.length, icon:'📡', color:'#10b981'
            },
          ].map(({ label, value, icon, color }) => (
            <div key={label} className="stat-card" style={{ '--card-accent': color }}>
              <div style={{ fontSize:24, marginBottom:8 }}>{icon}</div>
              <div className="stat-card-value">{value}</div>
              <div className="stat-card-label">{label}</div>
            </div>
          ))}
        </div>

        {/* Events */}
        {loading ? (
          <div className="loading-screen">
            <div className="spinner" /><p>Fetching live data...</p>
          </div>
        ) : displayed.length === 0 ? (
          <div className="empty-state">
            <Radio size={40} />
            <p>No live events at this time</p>
            <p style={{ fontSize:11 }}>Live APIs may be unavailable. Try refreshing.</p>
          </div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
            {displayed.map((event, i) => (
              <EventCard key={`${event.source}-${i}`} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
