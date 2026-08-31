import React, { useEffect, useState } from 'react';
import { CheckCircle, Clock, Download, ShieldAlert, Truck, Users, Activity, AlertTriangle, Droplets } from 'lucide-react';
import EmbeddedMap from './Map';
import axios from 'axios';

const API = 'http://localhost:8000';

const TYPE_COLORS: Record<string, { bar: string; bg: string; text: string }> = {
  food:         { bar: '#3b82f6', bg: '#eff6ff', text: '#1d4ed8' },
  hygiene_kits: { bar: '#06b6d4', bg: '#ecfeff', text: '#0e7490' },
  medical:      { bar: '#f59e0b', bg: '#fffbeb', text: '#b45309' },
  shelter:      { bar: '#8b5cf6', bg: '#f5f3ff', text: '#6d28d9' },
  water:        { bar: '#10b981', bg: '#f0fdf4', text: '#047857' },
  other:        { bar: '#6b7280', bg: '#f9fafb', text: '#374151' },
};

export default function Dashboard() {
  const [stats, setStats]               = useState<any>(null);
  const [incidentBreakdown, setBreakdown] = useState<any>(null);
  const [performance, setPerformance]   = useState<any>(null);
  const [coverage, setCoverage]         = useState<any>(null);
  const [recentMissions, setRecentMissions] = useState<any[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        const [sumRes, brkRes, perfRes, covRes, missRes] = await Promise.all([
          axios.get(`${API}/api/analytics/dashboard-summary`),
          axios.get(`${API}/api/analytics/incident-breakdown`),
          axios.get(`${API}/api/analytics/delivery-performance`),
          axios.get(`${API}/api/analytics/coverage-summary`),
          axios.get(`${API}/api/analytics/missions-report`),
        ]);
        setStats(sumRes.data);
        setBreakdown(brkRes.data);
        setPerformance(perfRes.data);
        setCoverage(covRes.data);
        setRecentMissions(missRes.data.slice(0, 4)); // Show top 4 recent missions
      } catch (err) {
        console.error('Dashboard fetch error', err);
      }
    }
    fetchData();
  }, []);

  const chartData = (stats?.allocation_chart || []).map((d: any) => ({
    ...d,
    label: d.name.replace('_', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
    style: TYPE_COLORS[d.name.toLowerCase()] || TYPE_COLORS.other,
  }));
  const maxVal = chartData.length > 0 ? Math.max(...chartData.map((d: any) => d.value)) : 1;

  const fmtMin = (m: number) => m < 1 ? `${Math.round(m * 60)}s` : m < 60 ? `${m.toFixed(0)} min` : `${(m / 60).toFixed(1)} hr`;

  const handleExport = async () => {
    try {
      const { default: jsPDF }     = await import('jspdf');
      const { default: autoTable } = await import('jspdf-autotable');
      const [sumRes, brkRes, perfRes, missRes] = await Promise.all([
        axios.get(`${API}/api/analytics/dashboard-summary`),
        axios.get(`${API}/api/analytics/incident-breakdown`),
        axios.get(`${API}/api/analytics/delivery-performance`),
        axios.get(`${API}/api/analytics/missions-report`),
      ]);
      const s = sumRes.data, b = brkRes.data, missions = missRes.data;
      const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      const pw = doc.internal.pageSize.getWidth();
      const ts = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
      doc.setFillColor(15, 23, 42); doc.rect(0, 0, pw, 28, 'F');
      doc.setFontSize(18); doc.setFont('helvetica', 'bold'); doc.setTextColor(255, 255, 255);
      doc.text('DISASTER BRIDGE', 14, 12);
      doc.setFontSize(9); doc.setFont('helvetica', 'normal'); doc.setTextColor(148, 163, 184);
      doc.text('Disaster Resource Allocation & Relief Coordination', 14, 19);
      doc.setTextColor(255, 255, 255); doc.text('POST-EVENT REPORT', pw - 14, 12, { align: 'right' });
      doc.setTextColor(148, 163, 184); doc.text(`Generated: ${ts}`, pw - 14, 19, { align: 'right' });
      let y = 36;
      autoTable(doc, { startY: y, head: [['Metric', 'Value']],
        body: [['Active Incidents', s.active_incidents?.toLocaleString()],
               ['Population at Risk', s.population_at_risk?.toLocaleString()],
               ['Resources Deployed', `${s.resources_deployed?.toLocaleString()} units`],
               ['Active Missions', s.active_missions?.toString()]],
        margin: { left: 14, right: 14 }, styles: { fontSize: 10, cellPadding: 3 },
        headStyles: { fillColor: [15, 23, 42], textColor: 255, fontStyle: 'bold' },
        alternateRowStyles: { fillColor: [248, 250, 252] } });
      y = (doc as any).lastAutoTable.finalY + 8;
      doc.setFontSize(10); doc.setFont('helvetica', 'bold'); doc.setTextColor(15, 23, 42);
      doc.text('INCIDENT BREAKDOWN BY ALERT LEVEL', 14, y); y += 4;
      autoTable(doc, { startY: y, head: [['Alert Level', 'Count', 'Percentage']],
        body: Object.entries(b?.by_level ?? {}).map(([lvl, cnt]: any) => [lvl.toUpperCase(), cnt.toString(), `${((cnt / (b?.total ?? 1)) * 100).toFixed(1)}%`]),
        margin: { left: 14, right: 14 }, styles: { fontSize: 9, cellPadding: 3 },
        headStyles: { fillColor: [15, 23, 42], textColor: 255, fontStyle: 'bold' },
        alternateRowStyles: { fillColor: [248, 250, 252] } });
      y = (doc as any).lastAutoTable.finalY + 8;
      if (missions.length > 0) {
        doc.text('MISSION LOG', 14, y); y += 4;
        autoTable(doc, { startY: y, head: [['Team', 'Incident Type', 'Alert', 'Supplies', 'Status', 'Dispatched']],
          body: missions.map((m: any) => {
            const sup = Object.entries<any>(m.supplies || {}).map(([k, v]) => `${Math.round(Number(v))} ${k}`).join(', ');
            return [m.team_name, m.event_type ?? '—', m.alert_level?.toUpperCase() ?? '—', sup || 'None', m.status, m.dispatched_at ? new Date(m.dispatched_at).toLocaleDateString('en-IN') : '—'];
          }),
          margin: { left: 14, right: 14 }, styles: { fontSize: 8, cellPadding: 2 },
          headStyles: { fillColor: [79, 70, 229], textColor: 255, fontStyle: 'bold' },
          alternateRowStyles: { fillColor: [248, 250, 252] } });
      }
      const tp = (doc as any).internal.getNumberOfPages();
      for (let pg = 1; pg <= tp; pg++) {
        doc.setPage(pg); doc.setFontSize(7); doc.setFont('helvetica', 'normal'); doc.setTextColor(148, 163, 184);
        doc.text('Disaster Bridge — Confidential Operational Report', 14, 292);
        doc.text(`Page ${pg} of ${tp}`, pw - 14, 292, { align: 'right' });
      }
      doc.save(`DisasterBridge_PostEvent_${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (err) { console.error('PDF error:', err); }
  };

  const ALERT_CFG: Record<string, { bar: string; dot: string; label: string }> = {
    red:    { bar: 'bg-red-500',     dot: 'bg-red-500',     label: 'Red — Critical' },
    orange: { bar: 'bg-orange-400',  dot: 'bg-orange-400',  label: 'Orange — High'  },
    low:    { bar: 'bg-yellow-400',  dot: 'bg-yellow-400',  label: 'Low — Monitor'  },
    green:  { bar: 'bg-emerald-500', dot: 'bg-emerald-500', label: 'Green — Stable' },
  };

  return (
    <div className="space-y-4">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">System Overview</h1>
        <div className="flex items-center text-xs font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
          <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
          Live Sync Active
        </div>
      </div>

      {/* Nepal Crisis Spotlight Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-900 via-blue-800 to-indigo-900 p-4 shadow-lg border border-blue-700/50">
        {/* Animated wave background */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute bottom-0 left-0 right-0 h-16 bg-blue-400 rounded-t-full animate-pulse" />
        </div>
        <div className="relative flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="shrink-0 bg-red-500/20 border border-red-400/40 rounded-xl p-2.5">
              <AlertTriangle size={22} className="text-red-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-[10px] font-bold bg-red-500 text-white px-2 py-0.5 rounded-full uppercase tracking-wider">Active Emergency</span>
                <span className="text-[10px] text-blue-300 font-medium">Aug 2026</span>
              </div>
              <h2 className="text-white font-extrabold text-base leading-tight">🇳🇵 Nepal Monsoon Floods 2026 — Crisis Response Active</h2>
              <p className="text-blue-200 text-xs mt-0.5 font-medium">
                8 districts affected · 1.6M+ people exposed · Bagmati, Koshi, Narayani & Karnali rivers in severe overflow
              </p>
            </div>
          </div>
          <div className="shrink-0 hidden md:flex flex-col items-end gap-1">
            <div className="flex items-center gap-2">
              <Droplets size={14} className="text-blue-300" />
              <span className="text-blue-200 text-xs font-semibold">3 RED · 5 ORANGE zones</span>
            </div>
            <div className="flex items-center gap-2">
              <Truck size={14} className="text-emerald-300" />
              <span className="text-emerald-300 text-xs font-semibold">6 depots on standby</span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { icon: <ShieldAlert size={18}/>, label: 'Active Incidents',   val: stats?.active_incidents?.toLocaleString() ?? '—',              sub: 'incl. Nepal floods',      accent: 'border-red-400',    valColor: 'text-red-500',    bg: 'from-red-50'    },
          { icon: <Activity size={18}/>,    label: 'Resources Deployed', val: stats?.resources_deployed?.toLocaleString() ?? '—',            sub: 'units in the field',      accent: 'border-blue-400',   valColor: 'text-blue-600',   bg: 'from-blue-50'   },
          { icon: <Truck size={18}/>,       label: 'Active Missions',    val: stats?.active_missions?.toString() ?? '—',                     sub: 'assigned + in transit',   accent: 'border-amber-400',  valColor: 'text-amber-600',  bg: 'from-amber-50'  },
          { icon: <Users size={18}/>,       label: 'Population at Risk', val: stats?.population_at_risk?.toLocaleString() ?? '—',            sub: 'orange + red events',     accent: 'border-purple-400', valColor: 'text-purple-600', bg: 'from-purple-50' },
        ].map(k => (
          <div key={k.label} className={`bg-gradient-to-br ${k.bg} to-white rounded-xl border-l-4 ${k.accent} border border-slate-200 shadow-sm p-4 flex items-center gap-3`}>
            <div className={`${k.valColor} opacity-60`}>{k.icon}</div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">{k.label}</p>
              <p className={`text-2xl font-extrabold ${k.valColor} leading-tight`}>{k.val}</p>
              <p className="text-[10px] text-slate-400">{k.sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Map + Analytics Panel */}
      <div className="grid grid-cols-3 gap-4" style={{ height: 480 }}>

        {/* Map */}
        <div className="col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 relative overflow-hidden z-0">
          <EmbeddedMap />
        </div>

        {/* Analytics & Performance card */}
        <div className="col-span-1 bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col gap-3 overflow-y-auto">
          <h2 className="text-xs font-bold text-slate-700 tracking-widest uppercase border-b border-slate-100 pb-2 shrink-0">
            Analytics & Performance
          </h2>

          {/* Key Metrics — expanded to fill space elegantly */}
          <div className="flex flex-col gap-4 flex-1 justify-center">
            
            {/* Coverage */}
            <div className="bg-emerald-50 rounded-2xl p-5 border border-emerald-100 shadow-sm flex flex-col justify-center flex-1">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle size={18} className={coverage?.average_coverage != null ? 'text-emerald-500' : 'text-slate-300'} />
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Coverage Achieved</p>
              </div>
              {coverage?.average_coverage != null ? (
                <>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold text-emerald-700 tracking-tight">{coverage.average_coverage}%</span>
                    <span className="text-xs font-semibold text-emerald-600/80 uppercase">{coverage.zone_count} zone{coverage.zone_count !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="w-full bg-emerald-200 rounded-full h-2 mt-3 shadow-inner">
                    <div className="h-2 rounded-full bg-emerald-500 transition-all" style={{ width: `${coverage.average_coverage}%` }} />
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-400 italic">No allocation data yet</p>
              )}
            </div>

            {/* Response Time */}
            <div className="bg-indigo-50 rounded-2xl p-5 border border-indigo-100 shadow-sm flex flex-col justify-center flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Clock size={18} className={performance?.average_delivery_minutes != null ? 'text-indigo-500' : 'text-slate-300'} />
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Avg Response Time</p>
              </div>
              {performance?.average_delivery_minutes != null ? (
                <>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold text-indigo-700 tracking-tight">{fmtMin(performance.average_delivery_minutes)}</span>
                    <span className="text-xs font-semibold text-indigo-500/80 uppercase">{performance.delivered_count} delivered</span>
                  </div>
                  <p className="text-xs font-medium text-indigo-900/40 mt-1">Transit time: {fmtMin(performance.average_transit_minutes || 0)}</p>
                </>
              ) : (
                <p className="text-sm text-slate-400 italic">No completed deliveries yet</p>
              )}
            </div>

            {/* Volunteers */}
            {stats?.volunteers != null && (
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-2">
                  <Users size={16} className="text-slate-400" />
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Active Volunteers</p>
                </div>
                <span className="text-2xl font-extrabold text-slate-700">{stats.volunteers}</span>
              </div>
            )}
          </div>

          {/* Export button pinned to bottom */}
          <button
            onClick={handleExport}
            className="shrink-0 w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-xl text-xs font-bold transition flex justify-center items-center gap-2 shadow-sm"
          >
            <Download size={14} /> Export Post-Event Report (PDF)
          </button>
        </div>
      </div>

      {/* ── Bottom Charts ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4">

        {/* Resources Deployed — Premium horizontal bars */}
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col">
          <div className="mb-3">
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Resources Currently Deployed</h2>
            <p className="text-xs text-slate-400 mt-0.5">Active missions only — assigned + in transit + delivered</p>
          </div>
          {chartData.length > 0 ? (
            <div className="flex-1 flex flex-col justify-center gap-3">
              {chartData.map((r: any) => {
                const pct = maxVal > 0 ? Math.round((r.value / maxVal) * 100) : 0;
                return (
                  <div key={r.name} className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-slate-600 w-24 shrink-0 capitalize">{r.label}</span>
                    <div className="flex-1 bg-slate-100 rounded-full h-5 relative overflow-hidden">
                      <div
                        className="h-full rounded-full flex items-center justify-end pr-2 transition-all"
                        style={{ width: `${Math.max(pct, 8)}%`, background: `linear-gradient(90deg, ${r.style.bar}cc, ${r.style.bar})` }}
                      >
                        <span className="text-[10px] font-bold text-white drop-shadow">{Math.round(r.value).toLocaleString()}</span>
                      </div>
                    </div>
                    <span className="text-[10px] text-slate-400 w-12 shrink-0 text-right">{r.unit}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-2">
              <div className="text-slate-200 text-5xl">📊</div>
              <p className="text-sm font-semibold text-slate-400">No active deployments yet</p>
              <p className="text-xs text-slate-400">Dispatch missions from <span className="text-indigo-500 font-semibold">Active Incidents</span></p>
            </div>
          )}
        </div>

        {/* Alert Level Breakdown — compact, no gaps */}
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col">
          <div className="mb-3">
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Alert Level Breakdown</h2>
            <p className="text-xs text-slate-400 mt-0.5">Source: all {incidentBreakdown?.total?.toLocaleString() ?? '…'} ingested events</p>
          </div>
          <div className="flex-1 flex flex-col justify-center gap-3">
            {incidentBreakdown ? (
              Object.entries<any>(incidentBreakdown.by_level)
                .sort((a, b) => b[1] - a[1])
                .map(([level, count]) => {
                  const cfg = ALERT_CFG[level] || { bar: 'bg-slate-400', dot: 'bg-slate-400', label: level };
                  const pct = Math.round((count / incidentBreakdown.total) * 100);
                  return (
                    <div key={level} className="flex items-center gap-3">
                      <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${cfg.dot}`} />
                      <span className="text-xs font-semibold text-slate-600 w-28 shrink-0">{cfg.label}</span>
                      <div className="flex-1 bg-slate-100 rounded-full h-5 relative overflow-hidden">
                        <div
                          className={`h-full rounded-full flex items-center justify-end pr-2 ${cfg.bar} opacity-90`}
                          style={{ width: `${Math.max(pct, 3)}%` }}
                        >
                          {pct > 10 && <span className="text-[10px] font-bold text-white drop-shadow">{count.toLocaleString()}</span>}
                        </div>
                      </div>
                      <span className="text-xs font-bold text-slate-700 w-12 text-right shrink-0">{count.toLocaleString()}</span>
                      <span className="text-[10px] text-slate-400 w-8 shrink-0">({pct}%)</span>
                    </div>
                  );
                })
            ) : (
              <div className="text-slate-400 text-sm text-center">Loading...</div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
