import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Download, TrendingUp, Clock, AlertTriangle, CheckCircle,
  Users, Activity, Map, FileText, Loader2, ShieldAlert, Truck
} from 'lucide-react';

const API = 'http://localhost:8000';

const ALERT_BADGE: Record<string, string> = {
  red:    'bg-red-100 text-red-700 border-red-200',
  orange: 'bg-orange-100 text-orange-700 border-orange-200',
  low:    'bg-yellow-100 text-yellow-700 border-yellow-200',
  green:  'bg-emerald-100 text-emerald-700 border-emerald-200',
};
const STATUS_BADGE: Record<string, string> = {
  assigned:   'bg-blue-100 text-blue-700',
  in_transit: 'bg-indigo-100 text-indigo-700',
  delivered:  'bg-green-100 text-green-700',
  cancelled:  'bg-slate-100 text-slate-500',
  pending:    'bg-yellow-100 text-yellow-700',
};

export default function ReportsPage() {
  const [summary, setSummary]         = useState<any>(null);
  const [breakdown, setBreakdown]     = useState<any>(null);
  const [perf, setPerf]               = useState<any>(null);
  const [underserved, setUnderserved] = useState<any[]>([]);
  const [zones, setZones]             = useState<any[]>([]);
  const [missions, setMissions]       = useState<any[]>([]);
  const [coverage, setCoverage]       = useState<any>(null);
  const [volSummary, setVolSummary]   = useState<any>(null);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [sumRes, brkRes, perfRes, undRes, zoneRes, missRes, covRes, volRes] = await Promise.all([
          axios.get(`${API}/api/analytics/dashboard-summary`),
          axios.get(`${API}/api/analytics/incident-breakdown`),
          axios.get(`${API}/api/analytics/delivery-performance`),
          axios.get(`${API}/api/analytics/underserved-zones`),
          axios.get(`${API}/api/analytics/zone-priority-ranking`),
          axios.get(`${API}/api/analytics/missions-report`),
          axios.get(`${API}/api/analytics/coverage-summary`),
          axios.get(`${API}/api/volunteers/summary`),
        ]);
        setSummary(sumRes.data);
        setBreakdown(brkRes.data);
        setPerf(perfRes.data);
        setUnderserved(undRes.data);
        setZones(zoneRes.data);
        setMissions(missRes.data);
        setCoverage(covRes.data);
        setVolSummary(volRes.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load report data.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const fmtMin = (m: number | null) => {
    if (!m) return '—';
    if (m < 1) return `${Math.round(m * 60)}s`;
    if (m < 60) return `${m.toFixed(0)} min`;
    return `${(m / 60).toFixed(1)} hr`;
  };

  const handleExportPDF = async () => {
    // Dynamically import jsPDF to keep initial bundle small
    const { default: jsPDF } = await import('jspdf');
    const { default: autoTable } = await import('jspdf-autotable');

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pw = doc.internal.pageSize.getWidth();
    const ts = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

    // ── Header Banner ─────────────────────────────────────────────────────
    doc.setFillColor(15, 23, 42);           // slate-900
    doc.rect(0, 0, pw, 28, 'F');
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('DISASTER BRIDGE', 14, 12);
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(148, 163, 184);        // slate-400
    doc.text('Disaster Resource Allocation & Relief Coordination', 14, 19);
    doc.setTextColor(255, 255, 255);
    doc.text('SITUATION REPORT & ANALYTICS', pw - 14, 12, { align: 'right' });
    doc.setTextColor(148, 163, 184);
    doc.text(`Generated: ${ts}`, pw - 14, 19, { align: 'right' });

    let y = 36;

    // ── KPI Row ───────────────────────────────────────────────────────────
    const kpis = [
      { label: 'Active Incidents', val: (summary?.active_incidents ?? 0).toLocaleString(), color: [220, 38, 38] },
      { label: 'Pop. at Risk', val: (summary?.population_at_risk ?? 0).toLocaleString(), color: [147, 51, 234] },
      { label: 'Active Missions', val: (summary?.active_missions ?? 0).toString(), color: [37, 99, 235] },
      { label: 'Coverage', val: coverage?.average_coverage ? `${coverage.average_coverage}%` : 'N/A', color: [5, 150, 105] },
    ];
    const kw = (pw - 28) / 4;
    kpis.forEach((k, i) => {
      const x = 14 + i * (kw + 2);
      doc.setFillColor(248, 250, 252);
      doc.roundedRect(x, y, kw, 20, 2, 2, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.roundedRect(x, y, kw, 20, 2, 2, 'S');
      doc.setFontSize(16);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(k.color[0], k.color[1], k.color[2]);
      doc.text(k.val, x + kw / 2, y + 11, { align: 'center' });
      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(100, 116, 139);
      doc.text(k.label.toUpperCase(), x + kw / 2, y + 17, { align: 'center' });
    });
    y += 26;

    // ── Incident Breakdown ────────────────────────────────────────────────
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.text('INCIDENT BREAKDOWN BY ALERT LEVEL', 14, y);
    y += 4;
    const alertRows = Object.entries<any>(breakdown?.by_level ?? {}).map(([lvl, cnt]) => [
      lvl.charAt(0).toUpperCase() + lvl.slice(1),
      cnt.toString(),
      `${((cnt / (breakdown?.total ?? 1)) * 100).toFixed(1)}%`
    ]);
    autoTable(doc, {
      startY: y, head: [['Alert Level', 'Count', 'Percentage']], body: alertRows,
      margin: { left: 14, right: 14 },
      styles: { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [15, 23, 42], textColor: 255, fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [248, 250, 252] },
    });
    y = (doc as any).lastAutoTable.finalY + 8;

    // ── Mission Status ────────────────────────────────────────────────────
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.text('MISSION STATUS SUMMARY', 14, y);
    y += 4;
    const mByStatus: Record<string, number> = missions.reduce((acc: any, m: any) => {
      acc[m.status] = (acc[m.status] || 0) + 1; return acc;
    }, {});
    autoTable(doc, {
      startY: y,
      head: [['Assigned', 'In Transit', 'Delivered', 'Pending', 'Cancelled']],
      body: [[
        mByStatus['assigned'] ?? 0, mByStatus['in_transit'] ?? 0,
        mByStatus['delivered'] ?? 0, mByStatus['pending'] ?? 0, mByStatus['cancelled'] ?? 0
      ].map(String)],
      margin: { left: 14, right: 14 },
      styles: { fontSize: 10, cellPadding: 4, halign: 'center' },
      headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: 'bold' },
    });
    y = (doc as any).lastAutoTable.finalY + 8;

    // ── Delivery Performance ──────────────────────────────────────────────
    if (perf?.delivered_count > 0) {
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(15, 23, 42);
      doc.text('DELIVERY PERFORMANCE', 14, y);
      y += 4;
      autoTable(doc, {
        startY: y,
        head: [['Metric', 'Value']],
        body: [
          ['Delivered missions', perf.delivered_count.toString()],
          ['Avg total response time', fmtMin(perf.average_delivery_minutes)],
          ['Avg transit time (dispatch → delivery)', fmtMin(perf.average_transit_minutes)],
        ],
        margin: { left: 14, right: 14 },
        styles: { fontSize: 9, cellPadding: 3 },
        headStyles: { fillColor: [15, 23, 42], textColor: 255, fontStyle: 'bold' },
        alternateRowStyles: { fillColor: [248, 250, 252] },
      });
      y = (doc as any).lastAutoTable.finalY + 8;
    }

    // ── Supply Depots ─────────────────────────────────────────────────────
    if (summary?.allocation_chart?.length > 0) {
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(15, 42, 15);
      doc.text('RESOURCES DEPLOYED BY TYPE', 14, y);
      y += 4;
      autoTable(doc, {
        startY: y,
        head: [['Resource Type', 'Quantity Deployed', 'Unit']],
        body: summary.allocation_chart.map((r: any) => [r.name.replace('_', ' ').toUpperCase(), r.value.toLocaleString(), r.unit]),
        margin: { left: 14, right: 14 },
        styles: { fontSize: 9, cellPadding: 3 },
        headStyles: { fillColor: [5, 150, 105], textColor: 255, fontStyle: 'bold' },
        alternateRowStyles: { fillColor: [240, 253, 244] },
      });
      y = (doc as any).lastAutoTable.finalY + 8;
    }

    // ── Mission Log ───────────────────────────────────────────────────────
    if (missions.length > 0) {
      // Add page if needed
      if (y > 230) { doc.addPage(); y = 20; }
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(15, 23, 42);
      doc.text('MISSION LOG', 14, y);
      y += 4;
      const missionRows = missions.map(m => {
        const sup = Object.entries<any>(m.supplies || {}).map(([k, v]) => `${Math.round(Number(v))} ${k}`).join(', ');
        const disp = m.dispatched_at ? new Date(m.dispatched_at).toLocaleDateString('en-IN') : '—';
        return [m.team_name, m.event_type?.replace('_', ' ') ?? '—', m.alert_level?.toUpperCase() ?? '—',
                sup || 'None', m.status.replace('_', ' '), disp];
      });
      autoTable(doc, {
        startY: y,
        head: [['Team', 'Incident Type', 'Alert', 'Supplies', 'Status', 'Dispatched']],
        body: missionRows,
        margin: { left: 14, right: 14 },
        styles: { fontSize: 8, cellPadding: 2, overflow: 'ellipsize' },
        headStyles: { fillColor: [79, 70, 229], textColor: 255, fontStyle: 'bold' },
        alternateRowStyles: { fillColor: [248, 250, 252] },
        columnStyles: { 3: { cellWidth: 45 } },
      });
      y = (doc as any).lastAutoTable.finalY + 8;
    }

    // ── Classified Zones ──────────────────────────────────────────────────
    if (zones.length > 0) {
      if (y > 230) { doc.addPage(); y = 20; }
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(15, 23, 42);
      doc.text(`CLASSIFIED IMPACT ZONES (${zones.length} total)`, 14, y);
      y += 4;
      autoTable(doc, {
        startY: y,
        head: [['Zone ID (short)', 'Event Type', 'Alert', 'Severity', 'AI Priority']],
        body: zones.map(z => [
          z.zone_id.substring(0, 8) + '…', z.event_type, z.alert_level?.toUpperCase() ?? '—',
          z.severity?.toFixed(0) ?? '—', z.priority ?? '—'
        ]),
        margin: { left: 14, right: 14 },
        styles: { fontSize: 8, cellPadding: 2 },
        headStyles: { fillColor: [15, 23, 42], textColor: 255, fontStyle: 'bold' },
        alternateRowStyles: { fillColor: [248, 250, 252] },
      });
    }

    // ── Footer on every page ─────────────────────────────────────────────
    const totalPages = (doc as any).internal.getNumberOfPages();
    for (let p = 1; p <= totalPages; p++) {
      doc.setPage(p);
      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(148, 163, 184);
      doc.text('Disaster Bridge — Confidential Operational Report', 14, 292);
      doc.text(`Page ${p} of ${totalPages}`, pw - 14, 292, { align: 'right' });
    }

    doc.save(`DisasterBridge_Report_${new Date().toISOString().slice(0, 10)}.pdf`);
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-400">
      <Loader2 size={28} className="animate-spin" />
      <p className="text-sm font-medium">Loading operational report data...</p>
    </div>
  );

  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center text-red-700">
      <AlertTriangle size={28} className="mx-auto mb-2" />
      <p className="font-bold">Failed to load reports</p>
      <p className="text-sm mt-1">{error}</p>
    </div>
  );

  const alertOrder = ['red', 'orange', 'low', 'green'];
  const alertLabels: Record<string, string> = {
    red: 'Red — Critical', orange: 'Orange — High', low: 'Low — Monitor', green: 'Green — Stable'
  };
  const totalBreakdown = breakdown?.total ?? 1;
  const missionsByStatus = missions.reduce((acc: any, m: any) => {
    acc[m.status] = (acc[m.status] || 0) + 1; return acc;
  }, {});

  return (
    <div className="space-y-4">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
            <FileText size={20} className="text-indigo-500" /> Situation Reports & Analytics
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">Live data — all figures reflect current operational state</p>
        </div>
        <button
          onClick={handleExportPDF}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg shadow text-sm transition"
        >
          <Download size={15} /> Export PDF Report
        </button>
      </div>

      {/* ── KPI Row ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { icon: <ShieldAlert size={16}/>, label: 'Total Incidents', val: summary?.active_incidents?.toLocaleString() ?? '—', sub: 'all ingested events', color: 'text-red-600', bg: 'bg-red-50' },
          { icon: <Users size={16}/>, label: 'Pop. at Risk', val: summary?.population_at_risk?.toLocaleString() ?? '—', sub: 'orange + red events only', color: 'text-purple-600', bg: 'bg-purple-50' },
          { icon: <Truck size={16}/>, label: 'Active Missions', val: summary?.active_missions?.toString() ?? '—', sub: 'assigned + in transit', color: 'text-blue-600', bg: 'bg-blue-50' },
          { icon: <Activity size={16}/>, label: 'Coverage', val: coverage?.average_coverage != null ? `${coverage.average_coverage}%` : 'N/A', sub: coverage?.zone_count ? `across ${coverage.zone_count} zones` : 'run allocation first', color: coverage?.average_coverage != null ? 'text-emerald-600' : 'text-slate-400', bg: 'bg-emerald-50' },
        ].map(k => (
          <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4 flex items-center gap-3 shadow-sm">
            <div className={`p-2 rounded-lg ${k.bg} ${k.color}`}>{k.icon}</div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-slate-400 uppercase">{k.label}</p>
              <p className={`text-xl font-extrabold ${k.color} leading-tight`}>{k.val}</p>
              <p className="text-[10px] text-slate-400 truncate">{k.sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── 3-col analytics grid ────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">

        {/* Col 1 — Incident Breakdown */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-col gap-3">
          <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wide flex items-center gap-1.5">
            <AlertTriangle size={13} className="text-red-500" /> Incident Breakdown
          </h2>

          {/* Visual severity ring */}
          {breakdown && (() => {
            const red    = breakdown.by_level['red']    ?? 0;
            const orange = breakdown.by_level['orange'] ?? 0;
            const green  = breakdown.by_level['green']  ?? 0;
            const total  = breakdown.total ?? 1;
            const critPct = Math.round(((red + orange) / total) * 100);
            return (
              <div className="flex items-center gap-4 bg-slate-50 rounded-xl p-3">
                {/* Donut ring using conic-gradient */}
                <div className="relative shrink-0" style={{ width: 72, height: 72 }}>
                  <div style={{
                    width: 72, height: 72, borderRadius: '50%',
                    background: `conic-gradient(#ef4444 0% ${(red/total)*100}%, #fb923c ${(red/total)*100}% ${((red+orange)/total)*100}%, #22c55e ${((red+orange)/total)*100}% 100%)`
                  }} />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="bg-white rounded-full" style={{ width: 44, height: 44, display:'flex', alignItems:'center', justifyContent:'center', flexDirection:'column' }}>
                      <span className="text-sm font-extrabold text-slate-800 leading-none">{critPct}%</span>
                      <span className="text-[8px] text-slate-400 leading-none">risk</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500 shrink-0"/><span className="text-[11px] text-slate-600">Critical <span className="font-bold text-red-600">{red}</span></span></div>
                  <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange-400 shrink-0"/><span className="text-[11px] text-slate-600">High <span className="font-bold text-orange-600">{orange}</span></span></div>
                  <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0"/><span className="text-[11px] text-slate-600">Stable <span className="font-bold text-emerald-600">{green}</span></span></div>
                </div>
              </div>
            );
          })()}

          {/* Bar breakdown */}
          {breakdown ? (
            <div className="space-y-2">
              {alertOrder.filter(l => breakdown.by_level[l] !== undefined).map(level => {
                const cnt = breakdown.by_level[level] ?? 0;
                const pct = Math.round((cnt / totalBreakdown) * 100);
                const bar = level === 'red' ? 'bg-red-500' : level === 'orange' ? 'bg-orange-400' : level === 'low' ? 'bg-yellow-400' : 'bg-emerald-500';
                return (
                  <div key={level}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="font-medium text-slate-700">{alertLabels[level]}</span>
                      <span className="font-bold text-slate-800">{cnt.toLocaleString()} <span className="text-slate-400 font-normal">({pct}%)</span></span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${bar}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              <p className="text-[10px] text-slate-400 pt-1.5 border-t">Total: {breakdown.total.toLocaleString()} ingested events</p>
            </div>
          ) : <p className="text-slate-400 text-xs">No data</p>}

          {/* Classified zones status */}
          <div className="bg-indigo-50 rounded-xl p-3">
            <p className="text-[10px] font-bold text-indigo-500 uppercase mb-1.5">Classified Zones Status</p>
            <div className="grid grid-cols-2 gap-2">
              <div className="text-center">
                <p className="text-2xl font-extrabold text-indigo-700">{zones.length}</p>
                <p className="text-[9px] text-indigo-500">Zones Classified</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-extrabold text-emerald-600">
                  {coverage?.average_coverage != null ? `${coverage.average_coverage}%` : '—'}
                </p>
                <p className="text-[9px] text-emerald-600">Avg Coverage</p>
              </div>
            </div>
          </div>
        </div>

        {/* Col 2 — Mission Status + Volunteers */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
          <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <Truck size={13} className="text-blue-500" /> Mission Status
          </h2>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {(['assigned', 'in_transit', 'delivered', 'cancelled', 'pending'] as const).map(s => (
              <div key={s} className="text-center bg-slate-50 rounded-lg py-2 px-1">
                <p className="text-xl font-extrabold text-slate-800">{missionsByStatus[s] ?? 0}</p>
                <span className={`text-[9px] font-bold uppercase px-1 py-0.5 rounded-full ${STATUS_BADGE[s]}`}>
                  {s.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>

          {volSummary && (
            <>
              <div className="border-t pt-3">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase mb-2 flex items-center gap-1">
                  <Users size={11}/> Volunteers
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { l: 'Total', v: volSummary.total, c: 'text-slate-800' },
                    { l: 'Available', v: volSummary.by_status?.available ?? 0, c: 'text-green-600' },
                    { l: 'Deployed', v: volSummary.by_status?.deployed ?? 0, c: 'text-indigo-600' },
                    { l: 'Off Duty', v: volSummary.by_status?.off_duty ?? 0, c: 'text-slate-400' },
                  ].map(c => (
                    <div key={c.l} className="text-center bg-slate-50 rounded-lg py-1.5">
                      <p className={`text-lg font-extrabold ${c.c}`}>{c.v}</p>
                      <p className="text-[9px] font-semibold text-slate-400">{c.l}</p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Col 3 — Delivery Performance + Resources */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-col gap-3">
          <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wide flex items-center gap-1.5">
            <Clock size={13} className="text-indigo-500" /> Delivery Performance
          </h2>

          {(perf?.delivered_count ?? 0) > 0 ? (
            <div className="space-y-2">
              <div className="flex justify-between items-center bg-indigo-50 rounded-xl px-3 py-2.5">
                <span className="text-xs text-slate-600">Avg response time</span>
                <span className="text-xl font-bold text-indigo-700">{fmtMin(perf.average_delivery_minutes)}</span>
              </div>
              <div className="flex justify-between items-center px-3 py-2 border border-slate-100 rounded-xl">
                <span className="text-xs text-slate-600">Avg transit time</span>
                <span className="font-bold text-slate-700">{fmtMin(perf.average_transit_minutes)}</span>
              </div>
              <div className="flex justify-between items-center px-3 py-2 bg-emerald-50 rounded-xl">
                <span className="text-xs text-slate-600">Completed deliveries</span>
                <span className="font-bold text-emerald-700">{perf.delivered_count}</span>
              </div>
              {perf.breakdown?.length > 0 && (
                <div className="border-t pt-2 max-h-24 overflow-y-auto">
                  <p className="text-[9px] font-bold text-slate-400 uppercase mb-1.5">Per-mission breakdown</p>
                  <div className="space-y-1">
                    {perf.breakdown.map((b: any, i: number) => (
                      <div key={i} className="flex items-center justify-between text-[10px]">
                        <span className="text-slate-600 truncate pr-2">{b.team}</span>
                        <span className="font-semibold text-slate-700 shrink-0">{fmtMin(b.total_minutes)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-slate-400 text-xs bg-slate-50 rounded-lg p-3">
              <Clock size={13} /> No completed deliveries yet. Mark a mission as Delivered.
            </div>
          )}

          {/* Resource Deployment Breakdown — fills remaining space */}
          {summary?.allocation_chart?.length > 0 && (
            <div className="mt-auto">
              <p className="text-[10px] font-bold text-slate-500 uppercase mb-2 flex items-center gap-1.5">
                <TrendingUp size={11} /> Resources Deployed by Type
              </p>
              <div className="space-y-1.5">
                {summary.allocation_chart.map((r: any) => {
                  const COLORS: Record<string, string> = {
                    food: 'bg-amber-500', hygiene_kits: 'bg-cyan-500',
                    medical: 'bg-red-500', shelter: 'bg-violet-500',
                  };
                  const maxVal = Math.max(...summary.allocation_chart.map((x: any) => x.value));
                  const pct = maxVal > 0 ? Math.round((r.value / maxVal) * 100) : 0;
                  return (
                    <div key={r.name}>
                      <div className="flex justify-between text-[10px] mb-0.5">
                        <span className="font-medium text-slate-600 capitalize">{r.name.replace('_', ' ')}</span>
                        <span className="font-bold text-slate-700">{r.value.toLocaleString()} <span className="text-slate-400 font-normal">{r.unit}</span></span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full ${COLORS[r.name] || 'bg-slate-500'}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* If no allocation yet, show a helpful prompt */}
          {(!summary?.allocation_chart || summary.allocation_chart.length === 0) && (
            <div className="mt-auto bg-slate-50 rounded-xl p-3 text-center">
              <p className="text-xs text-slate-400">No resources deployed yet.</p>
              <p className="text-[10px] text-slate-400 mt-0.5">Generate a relief plan from Active Incidents to begin.</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Underserved Zones ───────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <AlertTriangle size={13} className="text-amber-500" /> Underserved Zones (&lt;50% Coverage)
        </h2>
        {underserved.length === 0 ? (
          <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 rounded-lg p-3 text-xs font-medium">
            <CheckCircle size={14} /> All allocated zones meet 50% coverage — or no allocation run yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase">Zone</th>
                  <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase">Resource</th>
                  <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase">Coverage</th>
                  <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase">Gap</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {underserved.slice(0, 15).map((u, i) => (
                  <tr key={i} className="hover:bg-red-50 transition">
                    <td className="px-3 py-1.5 font-mono text-slate-400">{u.zone_id.substring(0, 8)}…</td>
                    <td className="px-3 py-1.5 capitalize font-medium text-slate-700">{u.resource}</td>
                    <td className="px-3 py-1.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-200 rounded-full h-1.5">
                          <div className="h-1.5 rounded-full bg-red-500" style={{ width: `${Math.min(u.coverage_percent, 100)}%` }} />
                        </div>
                        <span className="font-bold text-red-700">{u.coverage_percent.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-3 py-1.5 font-semibold text-red-600">{(50 - u.coverage_percent).toFixed(1)}% below</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {underserved.length > 15 && <p className="text-[10px] text-slate-400 px-3 py-2">+{underserved.length - 15} more zones…</p>}
          </div>
        )}
      </div>

      {/* ── Mission Log ────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <Truck size={13} className="text-blue-500" /> Mission Log ({missions.length} missions)
        </h2>
        {missions.length === 0 ? (
          <p className="text-slate-400 text-xs">No missions dispatched yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  {['Team', 'Incident', 'Supplies', 'Status', 'Dispatched'].map(h => (
                    <th key={h} className="text-left px-3 py-2 font-bold text-slate-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {missions.map(m => (
                  <tr key={m.id} className="hover:bg-slate-50 transition">
                    <td className="px-3 py-2">
                      <p className="font-semibold text-slate-800">{m.team_name}</p>
                      <p className="text-slate-400">{m.vehicle_id}</p>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`font-bold border px-1.5 py-0.5 rounded-full uppercase ${ALERT_BADGE[m.alert_level] || 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                        {m.alert_level}
                      </span>
                      <p className="text-slate-500 mt-0.5 capitalize">{m.event_type?.replace('_', ' ')}</p>
                    </td>
                    <td className="px-3 py-2 text-slate-700 max-w-[180px] truncate">{m.supplies_display}</td>
                    <td className="px-3 py-2">
                      <span className={`font-bold px-1.5 py-0.5 rounded-full uppercase ${STATUS_BADGE[m.status] || 'bg-slate-100'}`}>
                        {m.status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-400">
                      {m.dispatched_at ? new Date(m.dispatched_at).toLocaleString('en-IN', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
