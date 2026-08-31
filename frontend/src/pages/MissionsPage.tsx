import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Truck, Loader2, AlertCircle, Package, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API = 'http://localhost:8000';

const ALERT_COLORS: Record<string, string> = {
  red:    'bg-red-100 text-red-700 border-red-300',
  orange: 'bg-orange-100 text-orange-700 border-orange-300',
  low:    'bg-yellow-100 text-yellow-700 border-yellow-300',
  green:  'bg-emerald-100 text-emerald-700 border-emerald-300',
};

const STATUS_COLORS: Record<string, string> = {
  pending:    'bg-slate-100 text-slate-600',
  assigned:   'bg-indigo-100 text-indigo-700',
  in_transit: 'bg-amber-100 text-amber-700',
  delivered:  'bg-green-100 text-green-700',
  cancelled:  'bg-red-100 text-red-500',
};

const SUPPLY_UNITS: Record<string, string> = {
  food: 'kg', water: 'liters', medical: 'kits', shelter: 'units',
};

const SUPPLY_COLORS: Record<string, string> = {
  food: 'bg-amber-500', water: 'bg-blue-500', medical: 'bg-red-500', shelter: 'bg-violet-500',
};

const STATUS_STEPS = ['pending', 'assigned', 'in_transit', 'delivered'];

function getNextStatus(current: string): string | null {
  if (current === 'pending')    return 'assigned';
  if (current === 'assigned')   return 'in_transit';
  if (current === 'in_transit') return 'delivered';
  return null;
}

function formatSupplies(supplies: Record<string, number>): string {
  return Object.entries(supplies)
    .map(([k, v]) => `${parseFloat(String(v)).toFixed(0)} ${SUPPLY_UNITS[k] || 'units'} ${k}`)
    .join(', ');
}

export default function MissionsPage() {
  const [missions, setMissions]       = useState<any[]>([]);
  const [loading, setLoading]         = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [filter, setFilter]           = useState<string>('all');
  const navigate = useNavigate();

  const fetchMissions = async () => {
    try {
      const res = await axios.get(`${API}/api/dashboard/missions`);
      setMissions(res.data);
    } catch (err) {
      console.error('Failed to fetch missions', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMissions(); }, []);

  const updateStatus = async (id: string, status: string) => {
    setActionLoading(id + status);
    try {
      await axios.patch(`${API}/api/missions/${id}/status`, { status });
      await fetchMissions();
    } catch (err: any) {
      alert('Failed to update status: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const displayed = filter === 'all'
    ? missions
    : missions.filter(m => m.status === filter);

  const counts = {
    all:        missions.length,
    assigned:   missions.filter(m => m.status === 'assigned').length,
    in_transit: missions.filter(m => m.status === 'in_transit').length,
    delivered:  missions.filter(m => m.status === 'delivered').length,
    cancelled:  missions.filter(m => m.status === 'cancelled').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Mission Tracking</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {missions.length === 0 ? 'No missions yet' : `${missions.length} total missions`}
          </p>
        </div>
        <button
          onClick={() => navigate('/incidents')}
          className="flex items-center gap-2 text-sm font-semibold text-indigo-600 hover:text-indigo-800 transition"
        >
          <AlertCircle size={14} /> Create from Incident <ChevronRight size={14} />
        </button>
      </div>

      {/* Filter tabs */}
      {missions.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {([
            { key: 'all', label: `All (${counts.all})` },
            { key: 'assigned', label: `Assigned (${counts.assigned})` },
            { key: 'in_transit', label: `In Transit (${counts.in_transit})` },
            { key: 'delivered', label: `Delivered (${counts.delivered})` },
            { key: 'cancelled', label: `Cancelled (${counts.cancelled})` },
          ] as {key: string, label: string}[]).map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 text-xs font-bold rounded-full border transition ${
                filter === f.key
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-slate-500 border-slate-200 hover:border-slate-400'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}

      {/* Mission list */}
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-16 text-center text-slate-400 flex items-center justify-center gap-2">
          <Loader2 size={18} className="animate-spin" /> Loading missions...
        </div>
      ) : displayed.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-16 text-center">
          <Truck size={36} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-semibold">
            {missions.length === 0
              ? 'No missions dispatched yet'
              : 'No missions match this filter'}
          </p>
          {missions.length === 0 && (
            <p className="text-sm text-slate-400 mt-1">
              Go to{' '}
              <button onClick={() => navigate('/incidents')} className="text-indigo-500 underline">
                Active Incidents
              </button>
              {' '}→ Generate Response Plan → Dispatch Missions
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {displayed.map(m => {
            const eventLabel = m.event_type
              ? m.event_type.replace('_', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
              : 'Unknown Event';
            const alertLevel = m.alert_level || 'green';
            const suppliesEntries = Object.entries(m.supplies || {}) as [string, number][];
            const nextStatus = getNextStatus(m.status);
            const isActing = actionLoading?.startsWith(m.id);

            return (
              <div key={m.id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                {/* Mission header */}
                <div className="flex items-start justify-between p-5 border-b border-slate-100">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 p-2 bg-indigo-50 rounded-lg">
                      <Truck size={18} className="text-indigo-600" />
                    </div>
                    <div>
                      {/* Incident context — this is the key info */}
                      <div className="flex items-center gap-2 flex-wrap mb-0.5">
                        <h3 className="font-bold text-slate-800 text-base">
                          {eventLabel} Response
                        </h3>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                          ALERT_COLORS[alertLevel] || ALERT_COLORS.green
                        }`}>
                          {alertLevel}
                        </span>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                          STATUS_COLORS[m.status] || 'bg-slate-100 text-slate-500'
                        }`}>
                          {m.status?.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">
                        Team <span className="font-mono font-semibold text-slate-600">{m.team}</span>
                        {' · '}
                        Vehicle <span className="font-mono font-semibold text-slate-600">{m.vehicle_id}</span>
                        {m.created_at && (
                          <> · Dispatched {new Date(m.created_at).toLocaleString('en-GB', {
                            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                          })}</>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-xs text-slate-500 flex-shrink-0 ml-4">
                    <p className="font-bold text-slate-700">{m.distance.toFixed(1)} km</p>
                    <p>Est. {m.duration.toFixed(0)} min</p>
                    {m.fallback && <p className="text-amber-500 mt-0.5">Straight-line route</p>}
                  </div>
                </div>

                {/* Supplies being carried */}
                {suppliesEntries.length > 0 && (
                  <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-3 flex-wrap">
                    <Package size={13} className="text-slate-400 flex-shrink-0" />
                    <span className="text-xs text-slate-500 font-semibold">Carrying:</span>
                    {suppliesEntries.map(([type, qty]) => (
                      <span key={type} className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                        <span className={`w-2 h-2 rounded-full ${SUPPLY_COLORS[type] || 'bg-slate-400'}`} />
                        {parseFloat(String(qty)).toFixed(0)} {SUPPLY_UNITS[type] || 'units'} {type}
                      </span>
                    ))}
                  </div>
                )}

                {/* Progress tracker + action buttons */}
                <div className="flex items-center justify-between px-5 py-4">
                  {/* Step tracker */}
                  <div className="flex items-center gap-1">
                    {STATUS_STEPS.map((step, i) => {
                      const idx = STATUS_STEPS.indexOf(m.status);
                      const isPast = idx >= i;
                      const isCurrent = m.status === step;
                      return (
                        <div key={step} className="flex items-center">
                          <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase transition ${
                            isCurrent
                              ? 'bg-indigo-600 text-white'
                              : isPast
                                ? 'bg-indigo-100 text-indigo-600'
                                : 'bg-slate-100 text-slate-400'
                          }`}>
                            {step.replace('_', ' ')}
                          </div>
                          {i < STATUS_STEPS.length - 1 && (
                            <div className={`w-6 h-0.5 ${isPast && idx > i ? 'bg-indigo-300' : 'bg-slate-200'}`} />
                          )}
                        </div>
                      );
                    })}
                    {m.status === 'cancelled' && (
                      <span className="ml-2 text-xs font-bold text-red-500 uppercase">Cancelled</span>
                    )}
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 ml-4">
                    {nextStatus && m.status !== 'cancelled' && (
                      <button
                        onClick={() => updateStatus(m.id, nextStatus)}
                        disabled={!!actionLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition disabled:opacity-60"
                      >
                        {isActing && actionLoading === m.id + nextStatus
                          ? <Loader2 size={12} className="animate-spin" />
                          : null
                        }
                        Progress to {nextStatus.replace('_', ' ').toUpperCase()}
                      </button>
                    )}
                    {!['delivered', 'cancelled'].includes(m.status) && (
                      <button
                        onClick={() => updateStatus(m.id, 'cancelled')}
                        disabled={!!actionLoading}
                        className="px-3 py-1.5 border border-red-200 text-red-600 hover:bg-red-50 text-xs font-bold rounded-lg transition disabled:opacity-60"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Resource shortage guidance */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <p className="font-bold mb-1">When resources run out for the next incident:</p>
        <ol className="list-decimal ml-4 space-y-1 text-xs">
          <li>Go to <strong>Resources</strong> → click <strong>"Add Depot"</strong> to add a new supply cache with fresh quantities</li>
          <li>OR cancel an in-progress mission — its inventory is automatically restored to the depot</li>
          <li>Then go back to the incident → <strong>Generate Response Plan</strong> → the optimizer will use the restored stock</li>
        </ol>
      </div>
    </div>
  );
}
