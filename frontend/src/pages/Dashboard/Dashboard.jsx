import { useEffect, useState } from 'react';
import { getDashboard, getSeverityTrend, getUtilization } from '../../services/api';
import {
  AlertTriangle, Package, Users, Building2,
  Activity, TrendingUp, Radio, Zap
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadialBarChart, RadialBar, Legend
} from 'recharts';

const SEVERITY_COLORS = {
  critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#10b981'
};

const CAT_COLORS = ['#3b82f6','#06b6d4','#10b981','#f59e0b','#8b5cf6','#f97316'];

function StatCard({ icon: Icon, label, value, sub, color, accent }) {
  return (
    <div className="stat-card" style={{ '--card-accent': accent }}>
      <div className="stat-card-icon" style={{ background: `${accent}20` }}>
        <Icon size={20} color={accent} />
      </div>
      <div className="stat-card-value">{value ?? '—'}</div>
      <div className="stat-card-label">{label}</div>
      {sub && <div className="stat-card-sub">{sub}</div>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#111827', border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8, padding: '8px 12px', fontSize: 12
    }}>
      <p style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.fill || p.color }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const [data, setData]   = useState(null);
  const [trend, setTrend] = useState(null);
  const [util, setUtil]   = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getDashboard(), getSeverityTrend(), getUtilization()])
      .then(([d, t, u]) => { setData(d); setTrend(t); setUtil(u); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="loading-screen">
      <div className="spinner" />
      <p>Loading dashboard...</p>
    </div>
  );

  const zones     = data?.zones     || {};
  const resources = data?.resources || {};
  const teams     = data?.teams     || {};
  const depots    = data?.depots    || {};

  // Severity pie data
  const severityPie = Object.entries(zones.severity || {})
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value, fill: SEVERITY_COLORS[name] }));

  // Disaster type bar data
  const typeBar = Object.entries(trend?.by_disaster_type || {})
    .map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value }))
    .sort((a, b) => b.value - a.value);

  // Resource utilization bars
  const utilBars = (util?.categories || []).map((c, i) => ({
    name: c.category.charAt(0).toUpperCase() + c.category.slice(1),
    available: c.availability_pct,
    deployed: c.utilization_pct,
    fill: CAT_COLORS[i % CAT_COLORS.length]
  }));

  // Top zones
  const topZones = zones.top_zones || [];

  return (
    <div>
      {/* Topbar */}
      <div className="topbar">
        <div className="topbar-title">
          <h2>Command Dashboard</h2>
          <p>Real-time disaster response overview — India</p>
        </div>
        <div className="topbar-actions">
          <div style={{ display:'flex', alignItems:'center', gap:6,
            fontSize:12, color:'#10b981', background:'rgba(16,185,129,0.1)',
            padding:'6px 12px', borderRadius:20, border:'1px solid rgba(16,185,129,0.2)' }}>
            <span style={{ width:6, height:6, borderRadius:'50%',
              background:'#10b981', display:'inline-block',
              boxShadow:'0 0 6px #10b981' }} />
            Live
          </div>
        </div>
      </div>

      <div className="page-container">
        {/* Stat Cards */}
        <div className="stat-grid">
          <StatCard icon={AlertTriangle} label="Active Zones"
            value={zones.active} accent="#ef4444"
            sub={`${zones.severity?.critical || 0} critical`} />
          <StatCard icon={Activity} label="People Affected"
            value={(zones.total_affected || 0).toLocaleString()} accent="#f97316"
            sub="Across all active zones" />
          <StatCard icon={Package} label="Resource Alerts"
            value={resources.critical_alerts} accent="#f59e0b"
            sub={`${resources.total_items} items tracked`} />
          <StatCard icon={Users} label="Field Teams"
            value={teams.total} accent="#3b82f6"
            sub={`${teams.deployed || 0} deployed • ${teams.standby || 0} standby`} />
          <StatCard icon={Building2} label="Active Depots"
            value={depots.active} accent="#10b981"
            sub="Resource supply points" />
          <StatCard icon={Radio} label="Live Events"
            value={data?.events?.total_ingested || 0} accent="#8b5cf6"
            sub="GDACS + USGS ingested" />
        </div>

        {/* Charts Row */}
        <div className="grid-2" style={{ marginBottom: 24 }}>
          {/* Severity Pie */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><AlertTriangle size={14} /> Severity Breakdown</span>
            </div>
            {severityPie.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={severityPie} cx="50%" cy="50%" innerRadius={55}
                    outerRadius={90} paddingAngle={3} dataKey="value">
                    {severityPie.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} stroke="transparent" />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    iconType="circle"
                    formatter={(v) => <span style={{ color:'#94a3b8', fontSize:12 }}>{v}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state"><p>No active zones</p></div>
            )}
          </div>

          {/* Disaster Type Bar */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><Activity size={14} /> Zones by Disaster Type</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={typeBar} barSize={28}>
                <XAxis dataKey="name" tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill:'rgba(255,255,255,0.04)' }} />
                <Bar dataKey="value" name="Zones" radius={[4,4,0,0]}>
                  {typeBar.map((_, i) => (
                    <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Resource Utilization */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <span className="card-title"><Package size={14} /> Resource Availability by Category</span>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={utilBars} barGap={4}>
              <XAxis dataKey="name" tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#64748b', fontSize:11 }} axisLine={false} tickLine={false} domain={[0,100]}
                tickFormatter={v => `${v}%`} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill:'rgba(255,255,255,0.04)' }} />
              <Bar dataKey="available" name="Available %" radius={[4,4,0,0]} fill="#10b981" />
              <Bar dataKey="deployed"  name="Deployed %"  radius={[4,4,0,0]} fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top Zones + Teams */}
        <div className="grid-2">
          {/* Top Zones */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><AlertTriangle size={14} /> Top Priority Zones</span>
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
              {topZones.length === 0 && <div className="empty-state"><p>No zones found</p></div>}
              {topZones.map((z) => (
                <div key={z.id} style={{
                  display:'flex', alignItems:'center', justifyContent:'space-between',
                  padding:'10px 12px', background:'rgba(255,255,255,0.03)',
                  borderRadius:8, border:'1px solid var(--border)'
                }}>
                  <div>
                    <div style={{ fontSize:13, fontWeight:600, color:'#f1f5f9' }}>{z.name}</div>
                    <div style={{ fontSize:11, color:'#64748b' }}>
                      {z.state} • {(z.population_affected||0).toLocaleString()} affected
                    </div>
                  </div>
                  <div style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', gap:4 }}>
                    <span className={`badge badge-${z.severity}`}>{z.severity}</span>
                    <span style={{ fontSize:11, color:'#64748b' }}>Score: {z.severity_score}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Teams Summary */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><Users size={14} /> Team Deployment Status</span>
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
              {[
                { label:'Deployed', key:'deployed', color:'#10b981' },
                { label:'In Transit', key:'transit', color:'#f59e0b' },
                { label:'Standby', key:'standby', color:'#3b82f6' },
                { label:'Offline', key:'offline', color:'#64748b' },
              ].map(({ label, key, color }) => {
                const val = teams[key] || 0;
                const total = teams.total || 1;
                const pct = Math.round(val / total * 100);
                return (
                  <div key={key}>
                    <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
                      <span style={{ fontSize:12, color:'#94a3b8' }}>{label}</span>
                      <span style={{ fontSize:12, color:'#f1f5f9', fontWeight:600 }}>
                        {val} <span style={{ color:'#64748b' }}>({pct}%)</span>
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill"
                        style={{ width:`${pct}%`, background:color }} />
                    </div>
                  </div>
                );
              })}
              <div style={{ marginTop:4, paddingTop:12, borderTop:'1px solid var(--border)',
                fontSize:12, color:'#94a3b8' }}>
                Total personnel: <strong style={{ color:'#f1f5f9' }}>
                  {(teams.total_members||0).toLocaleString()}
                </strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
