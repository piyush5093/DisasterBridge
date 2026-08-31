import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { RefreshCw, Layers, Truck, CheckCircle, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API = 'http://localhost:8000';

const RESOURCE_UNITS: Record<string, string> = {
  food: 'kg', water: 'liters', medical: 'kits', shelter: 'units',
};
const RESOURCE_COLORS: Record<string, string> = {
  food: 'bg-amber-500', water: 'bg-blue-500', medical: 'bg-red-500', shelter: 'bg-violet-500',
};
const ALERT_BADGE: Record<string, string> = {
  red:    'bg-red-100 text-red-700',
  orange: 'bg-orange-100 text-orange-700',
  low:    'bg-yellow-100 text-yellow-700',
  green:  'bg-emerald-100 text-emerald-700',
};
const PRIORITY_BADGE: Record<string, string> = {
  high:   'bg-red-100 text-red-800',
  medium: 'bg-amber-100 text-amber-800',
  low:    'bg-green-100 text-green-800',
};

export default function LogisticsPage() {
  const navigate = useNavigate();
  const [zones, setZones]               = useState<any[]>([]);
  const [loading, setLoading]           = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [allocations, setAllocations]   = useState<any[] | null>(null);
  const [statusMap, setStatusMap]       = useState<Record<string, string>>({});
  const [dispatchDone, setDispatchDone] = useState(false);
  const [allocError, setAllocError]     = useState('');

  const fetchZones = async () => {
    try {
      const res = await axios.get(`${API}/api/analytics/zone-priority-ranking`);
      setZones(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchZones(); }, []);

  const handleOverride = async (zoneId: string, val: string) => {
    setStatusMap(prev => ({ ...prev, [zoneId]: 'loading' }));
    try {
      await axios.patch(`${API}/api/zones/${zoneId}/priority-override`, { priority_override: val });
      setStatusMap(prev => ({ ...prev, [zoneId]: 'success' }));
      await fetchZones();
      setTimeout(() => setStatusMap(prev => ({ ...prev, [zoneId]: '' })), 2000);
    } catch {
      setStatusMap(prev => ({ ...prev, [zoneId]: 'error' }));
    }
  };

  const handleRecalculate = async () => {
    setRecalculating(true);
    setAllocError('');
    setAllocations(null);
    try {
      const zoneIds = zones.map(z => z.zone_id);
      const res = await axios.post(`${API}/api/relief-plan/generate-batch`, {
        zone_ids: zoneIds,
        create_missions: false,
      });
      // De-duplicate: keep only highest allocation per zone+resource_type
      const seen = new Map<string, any>();
      for (const a of (res.data.allocations || [])) {
        const key = `${a.zone_id}__${a.resource_type}`;
        if (!seen.has(key) || a.quantity > seen.get(key).quantity) {
          seen.set(key, a);
        }
      }
      const deduped = Array.from(seen.values()).filter(a => a.quantity > 0);
      setAllocations(deduped);
      if (deduped.length === 0) setAllocError('No resources available to allocate. Add stock via the Resources page.');
    } catch (err: any) {
      setAllocError(err.response?.data?.detail || 'Allocation failed. Check backend logs.');
    } finally {
      setRecalculating(false);
    }
  };

  const handleDispatch = async () => {
    setRecalculating(true);
    setDispatchDone(false);
    try {
      const zoneIds = zones.map(z => z.zone_id);
      await axios.post(`${API}/api/relief-plan/generate-batch`, {
        zone_ids: zoneIds,
        create_missions: true,
      });
      setDispatchDone(true);
    } catch (e: any) {
      alert('Dispatch failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setRecalculating(false);
    }
  };

  // Build zone label lookup
  const zoneLabelMap: Record<string, string> = {};
  zones.forEach(z => { zoneLabelMap[z.zone_id] = z.label; });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Logistics & Resource Allocation</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage zone priorities and run the allocation optimizer across all classified zones.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRecalculate}
            disabled={recalculating || zones.length === 0}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg shadow-sm disabled:opacity-50 transition text-sm"
          >
            <RefreshCw size={16} className={recalculating ? 'animate-spin' : ''} />
            {recalculating ? 'Optimizing...' : 'Recalculate Allocation'}
          </button>
          <button
            onClick={handleDispatch}
            disabled={recalculating || zones.length === 0}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 px-4 rounded-lg shadow-sm disabled:opacity-50 transition text-sm"
          >
            <Truck size={16} /> Dispatch All Zones
          </button>
        </div>
      </div>

      {/* Tip */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-xs text-blue-800">
        <strong>How this page works:</strong> The table below shows all classified impact zones.
        You can override the AI-assigned priority for any zone. Click <em>Recalculate Allocation</em> to
        run the optimizer and see what resources would be allocated. Click <em>Dispatch All Zones</em> to
        create missions for all zones at once. For a guided per-incident workflow, use{' '}
        <button onClick={() => navigate('/incidents')} className="font-bold underline">Active Incidents</button>
        {' '}→ Generate Response Plan.
      </div>

      {/* Zone table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="py-3 px-5 text-xs font-bold text-slate-500 uppercase">Zone / Incident</th>
              <th className="py-3 px-5 text-xs font-bold text-slate-500 uppercase">Alert</th>
              <th className="py-3 px-5 text-xs font-bold text-slate-500 uppercase">Severity</th>
              <th className="py-3 px-5 text-xs font-bold text-slate-500 uppercase">AI Priority</th>
              <th className="py-3 px-5 text-xs font-bold text-slate-500 uppercase">Priority Override</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="p-8 text-center text-slate-400">Loading zones...</td></tr>
            ) : zones.length === 0 ? (
              <tr><td colSpan={5} className="p-8 text-center text-slate-400">
                No classified zones yet. Go to Active Incidents and generate a response plan first.
              </td></tr>
            ) : zones.map(z => (
              <tr key={z.zone_id} className="border-b border-slate-100 hover:bg-slate-50 transition">
                <td className="py-3 px-5">
                  <p className="font-semibold text-slate-800">{z.label}</p>
                  <p className="font-mono text-[10px] text-slate-400">{z.zone_id}</p>
                </td>
                <td className="py-3 px-5">
                  <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${ALERT_BADGE[z.alert_level] || 'bg-slate-100 text-slate-500'}`}>
                    {z.alert_level}
                  </span>
                </td>
                <td className="py-3 px-5 font-bold text-slate-700">{z.severity?.toFixed(0) ?? '—'}</td>
                <td className="py-3 px-5">
                  <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${PRIORITY_BADGE[z.priority] || 'bg-slate-100 text-slate-500'}`}>
                    {z.priority || '—'}
                  </span>
                </td>
                <td className="py-3 px-5">
                  <div className="flex items-center gap-2">
                    <select
                      className="border border-slate-300 rounded-lg text-sm p-1.5 focus:ring-2 focus:ring-indigo-400 outline-none"
                      value={z.priority_override || ''}
                      onChange={e => handleOverride(z.zone_id, e.target.value)}
                    >
                      <option value="">-- No Override --</option>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                    {statusMap[z.zone_id] === 'loading' && <RefreshCw size={14} className="animate-spin text-slate-400" />}
                    {statusMap[z.zone_id] === 'success' && <span className="text-xs text-green-600 font-semibold">Saved</span>}
                    {statusMap[z.zone_id] === 'error'   && <span className="text-xs text-red-600 font-semibold">Error</span>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Dispatch done banner */}
      {dispatchDone && (
        <div className="bg-green-50 border border-green-300 rounded-xl px-5 py-4 flex items-center gap-3">
          <CheckCircle size={20} className="text-green-600 flex-shrink-0" />
          <div>
            <p className="font-bold text-green-800">Missions Dispatched Successfully!</p>
            <p className="text-sm text-green-700">
              Go to{' '}
              <button onClick={() => navigate('/missions')} className="font-bold underline">Mission Tracking</button>
              {' '}to manage and update mission status.
            </p>
          </div>
        </div>
      )}

      {/* Allocation error */}
      {allocError && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl px-5 py-4 flex items-center gap-3">
          <AlertCircle size={20} className="text-amber-600 flex-shrink-0" />
          <div>
            <p className="font-bold text-amber-800">Allocation Notice</p>
            <p className="text-sm text-amber-700">{allocError}</p>
          </div>
        </div>
      )}

      {/* Allocation Results */}
      {allocations && allocations.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Layers size={18} className="text-indigo-500" />
            Allocation Results
            <span className="text-xs font-normal text-slate-400 ml-1">— what the optimizer would deploy right now</span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {allocations.map((a, idx) => {
              const unit = RESOURCE_UNITS[a.resource_type] || 'units';
              const zoneLabel = zoneLabelMap[a.zone_id] || a.zone_id.substring(0, 8);
              const pct = Math.min(a.coverage_percent || 0, 100);
              return (
                <div key={idx} className="border border-slate-200 rounded-xl p-4 bg-slate-50">
                  <p className="text-[10px] text-slate-500 font-medium mb-1">{zoneLabel}</p>
                  <div className="flex items-center gap-1.5 mb-1">
                    <div className={`w-2 h-2 rounded-full ${RESOURCE_COLORS[a.resource_type] || 'bg-slate-400'}`} />
                    <p className="font-bold text-slate-800 capitalize text-sm">
                      {a.resource_type}
                      <span className="text-xs font-normal text-slate-500 ml-1">({unit})</span>
                    </p>
                  </div>
                  <p className="text-2xl font-extrabold text-slate-800">
                    {parseFloat(a.quantity).toFixed(0)}
                    <span className="text-xs font-normal text-slate-400 ml-1">{unit}</span>
                  </p>
                  <div className="mt-2 w-full bg-slate-200 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full ${pct > 80 ? 'bg-green-500' : pct > 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="text-xs text-right mt-1 font-semibold text-slate-600">{pct.toFixed(1)}% Coverage</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
