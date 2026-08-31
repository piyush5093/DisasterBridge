import React, { useEffect, useState } from 'react';
import axios from 'axios';
import EmbeddedMap from '../components/Map';
import { Truck, Package, Clock, AlertTriangle, CheckCircle, Navigation } from 'lucide-react';

const API = 'http://localhost:8000';

const STATUS_CFG: Record<string, { color: string; label: string }> = {
  assigned:   { color: 'bg-blue-100 text-blue-700',    label: 'Assigned'   },
  in_transit: { color: 'bg-indigo-100 text-indigo-700', label: 'In Transit' },
  delivered:  { color: 'bg-green-100 text-green-700',   label: 'Delivered'  },
  cancelled:  { color: 'bg-slate-100 text-slate-500',   label: 'Cancelled'  },
  pending:    { color: 'bg-yellow-100 text-yellow-700', label: 'Pending'    },
};
const ALERT_COLOR: Record<string, string> = {
  red: 'text-red-600 bg-red-50 border-red-200',
  orange: 'text-orange-600 bg-orange-50 border-orange-200',
  low: 'text-yellow-600 bg-yellow-50 border-yellow-200',
  green: 'text-emerald-600 bg-emerald-50 border-emerald-200',
};

export default function ReliefMapPage() {
  const [missions, setMissions] = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    axios.get(`${API}/api/dashboard/missions`)
      .then(r => setMissions(r.data))
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const active    = missions.filter(m => !['cancelled'].includes(m.status));
  const cancelled = missions.filter(m => m.status === 'cancelled');

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex justify-between items-center flex-shrink-0">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Relief Map</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Live route tracking from supply depots to disaster zones. Hover or click routes for details.
          </p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-semibold">
            {active.length} Active Route{active.length !== 1 ? 's' : ''}
          </span>
          {cancelled.length > 0 && (
            <span className="bg-slate-100 text-slate-500 px-2 py-1 rounded-full font-semibold">
              {cancelled.length} Cancelled
            </span>
          )}
        </div>
      </div>

      {/* Map explanation banner */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-2.5 text-xs text-indigo-800 flex-shrink-0">
        <strong>How to read this map:</strong> 🔵 Blue circles = supply depots (route start). 🔴 Red/orange circles = disaster zones (route destination). 
        Blue lines = active delivery routes. <strong>Hover over a route</strong> to see what it's carrying. <strong>Click</strong> for full details.
        Coloured dots = all 495 ingested disaster events (clustered by proximity).
      </div>

      {/* Main layout: Map + Side Panel */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Map */}
        <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden relative min-h-[400px]">
          <EmbeddedMap />
        </div>

        {/* Side panel */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-3 overflow-y-auto">
          {loading ? (
            <div className="bg-white rounded-xl border border-slate-200 p-6 text-center text-slate-400 text-sm">Loading routes...</div>
          ) : active.length === 0 ? (
            <div className="bg-white rounded-xl border border-dashed border-slate-300 p-6 text-center">
              <Navigation size={28} className="mx-auto text-slate-300 mb-2" />
              <p className="text-sm font-semibold text-slate-500">No active routes</p>
              <p className="text-xs text-slate-400 mt-1">Generate a response plan from Active Incidents to dispatch missions and see routes here.</p>
            </div>
          ) : (
            active.map(m => {
              const statusCfg = STATUS_CFG[m.status] || STATUS_CFG.pending;
              const alertCfg  = ALERT_COLOR[m.alert_level] || 'text-slate-600 bg-slate-50 border-slate-200';
              const eventName = (m.event_type || 'unknown').replace('_', ' ');
              return (
                <div key={m.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-bold text-slate-800 text-sm">{m.team}</p>
                      <p className="text-xs text-slate-400">{m.vehicle_id}</p>
                    </div>
                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${statusCfg.color}`}>
                      {statusCfg.label}
                    </span>
                  </div>

                  {/* Incident */}
                  <div className={`border rounded-lg px-3 py-2 mb-3 text-xs ${alertCfg}`}>
                    <p className="font-bold capitalize">{eventName} — {m.alert_level?.toUpperCase()}</p>
                    <p className="opacity-75">Severity: {m.severity?.toFixed(0)}</p>
                  </div>

                  {/* Route info */}
                  <div className="space-y-1.5 text-xs text-slate-600">
                    <div className="flex items-start gap-2">
                      <div className="w-3 h-3 rounded-full bg-blue-500 border-2 border-blue-800 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-slate-700">FROM: {m.depot_name || 'Supply Depot'}</p>
                        {m.depot_lat && <p className="text-slate-400">{m.depot_lat?.toFixed(3)}, {m.depot_lng?.toFixed(3)}</p>}
                      </div>
                    </div>
                    <div className="ml-1.5 border-l-2 border-dashed border-slate-300 pl-2 py-0.5 text-slate-400">
                      {m.distance?.toFixed(1)} km · {m.duration?.toFixed(0)} min
                      {m.fallback && <span className="ml-2 text-amber-600">⚠ fallback route</span>}
                    </div>
                    <div className="flex items-start gap-2">
                      <AlertTriangle size={12} className="text-red-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-slate-700">TO: Disaster Zone</p>
                        {m.zone_lat && <p className="text-slate-400">{m.zone_lat?.toFixed(3)}, {m.zone_lng?.toFixed(3)}</p>}
                      </div>
                    </div>
                  </div>

                  {/* Supplies */}
                  <div className="mt-3 bg-slate-50 rounded-lg px-3 py-2 text-xs">
                    <div className="flex items-center gap-1 text-slate-500 mb-1">
                      <Package size={11} /> <span className="font-semibold">CARRYING</span>
                    </div>
                    <p className="font-bold text-slate-800">{m.supplies_display}</p>
                  </div>

                  {/* Dispatched time */}
                  {m.created_at && (
                    <div className="mt-2 flex items-center gap-1 text-[10px] text-slate-400">
                      <Clock size={10} />
                      Dispatched: {new Date(m.created_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Cancelled missions summary */}
          {cancelled.length > 0 && (
            <div className="bg-slate-50 rounded-xl border border-dashed border-slate-200 p-3">
              <p className="text-xs font-semibold text-slate-500">{cancelled.length} cancelled mission{cancelled.length > 1 ? 's' : ''} (not shown on map)</p>
              {cancelled.map(m => (
                <p key={m.id} className="text-[10px] text-slate-400 mt-0.5">{m.team} · {m.supplies_display}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
