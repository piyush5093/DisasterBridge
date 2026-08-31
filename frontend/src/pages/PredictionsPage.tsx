import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Activity, RefreshCcw, Zap, ArrowLeft, Layers,
  Truck, CheckCircle, Loader2, ChevronRight
} from 'lucide-react';

const API = 'http://localhost:8000';

const ALERT_BANNER: Record<string, string> = {
  red:    'bg-red-50 border-red-300 text-red-800',
  orange: 'bg-orange-50 border-orange-300 text-orange-800',
  low:    'bg-yellow-50 border-yellow-300 text-yellow-800',
  green:  'bg-emerald-50 border-emerald-300 text-emerald-800',
};

const PRIORITY_COLOR: Record<string, string> = {
  high:   'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low:    'bg-green-100 text-green-700',
};

const RESOURCE_COLORS: Record<string, string> = {
  food:         'bg-amber-500',
  hygiene_kits: 'bg-teal-500',
  medical:      'bg-red-500',
  shelter:      'bg-violet-500',
};

const RESOURCE_UNITS: Record<string, string> = {
  food: 'packages', hygiene_kits: 'kits', medical: 'kits', shelter: 'units',
};

const RESOURCE_LABELS: Record<string, string> = {
  food: 'Food Packages', hygiene_kits: 'Hygiene Kits', medical: 'Medical Kits', shelter: 'Shelter Units',
};

interface Zone {
  id: string; severity: number; priority: string;
  alert_level: string; event_type: string; event_id: string; label: string;
}

// Aggregates available stock by resource type across all depots
function buildStockMap(resources: any[]): Record<string, number> {
  const map: Record<string, number> = { food: 0, hygiene_kits: 0, medical: 0, shelter: 0 };
  for (const r of resources) {
    const t = (r.resource_type || '').toLowerCase();
    if (t in map) map[t] += r.quantity || 0;
  }
  return map;
}

export default function PredictionsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [zones, setZones]               = useState<Zone[]>([]);
  const [selectedZone, setSelectedZone] = useState('');
  const [selectedMeta, setSelectedMeta] = useState<Zone | null>(null);
  const [fromIncident, setFromIncident] = useState(false);

  // Available stock from resource depots (summed by type)
  const [stock, setStock] = useState<Record<string, number>>({});

  // Prediction state
  const [prediction, setPrediction]   = useState<any>(null);
  const [predLoading, setPredLoading] = useState(false);
  const [predError, setPredError]     = useState('');

  // Allocation state
  const [allocations, setAllocations]     = useState<any[]>([]);
  const [allocLoading, setAllocLoading]   = useState(false);
  const [allocError, setAllocError]       = useState('');
  const [allocDone, setAllocDone]         = useState(false);

  // Dispatch state
  const [dispatching, setDispatching]   = useState(false);
  const [dispatched, setDispatched]     = useState(false);

  // Recalibrate / simulate
  const [recalibrateVal, setRecalibrateVal] = useState('');
  const [simulated, setSimulated]           = useState<any>(null);

  // ── Load zones + current stock on mount ───────────────────────────────────
  useEffect(() => {
    // Load zones
    axios.get(`${API}/api/zones/list`).then(res => {
      setZones(res.data);
      const urlZoneId = searchParams.get('zone_id');
      if (urlZoneId) {
        setSelectedZone(urlZoneId);
        setFromIncident(true);
        const matched = res.data.find((z: Zone) => z.id === urlZoneId);
        if (matched) setSelectedMeta(matched);
      }
    }).catch(console.error);
    // Load current depot stock totals for demand comparison
    axios.get(`${API}/api/resources`).then(res => {
      const map: Record<string, number> = { food: 0, hygiene_kits: 0, medical: 0, shelter: 0 };
      for (const r of res.data) {
        const t = (r.resource_type || '').toLowerCase();
        if (t in map) map[t] += r.quantity || 0;
      }
      setStock(map);
    }).catch(console.error);
  }, []);

  // ── Auto-load prediction when zone changes ─────────────────────────────────
  useEffect(() => {
    if (!selectedZone) return;
    const matched = zones.find(z => z.id === selectedZone);
    if (matched) setSelectedMeta(matched);
    loadPrediction(selectedZone);
    // Reset allocation when zone changes
    setAllocations([]);
    setAllocDone(false);
    setDispatched(false);
  }, [selectedZone]);

  const loadPrediction = async (zoneId: string) => {
    setPredLoading(true);
    setPredError('');
    setPrediction(null);
    try {
      // Prediction and history fetched INDEPENDENTLY — history 500 won't block prediction
      const predRes = await axios.post(`${API}/predict/demand/${zoneId}`, {
        vulnerability_demographics: {}
      });
      setPrediction(predRes.data);
    } catch (err: any) {
      setPredError(err?.response?.data?.detail || 'Failed to load predictions.');
    } finally {
      setPredLoading(false);
    }
  };

  const handleRunAllocation = async () => {
    setAllocLoading(true);
    setAllocError('');
    setAllocations([]);
    try {
      const res = await axios.post(`${API}/api/relief-plan/generate-batch`, {
        zone_ids: [selectedZone],
        create_missions: false,
      });
      setAllocations(res.data.allocations || []);
      setAllocDone(true);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.response?.data?.error || 'Allocation failed.';
      setAllocError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setAllocLoading(false);
    }
  };

  const handleDispatch = async () => {
    setDispatching(true);
    try {
      await axios.post(`${API}/api/relief-plan/generate-batch`, {
        zone_ids: [selectedZone],
        create_missions: true,
      });
      setDispatched(true);
    } catch (err: any) {
      alert('Dispatch failed: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setDispatching(false);
    }
  };

  const handleRecalibrate = async () => {
    if (!recalibrateVal) return;
    setPredLoading(true);
    try {
      await axios.post(`${API}/api/predictions/${selectedZone}/recalibrate`, {
        new_severity: parseFloat(recalibrateVal),
        reason: 'Manual adjustment',
      });
      await loadPrediction(selectedZone);
      setRecalibrateVal('');
    } catch { alert('Recalibration failed'); }
    finally { setPredLoading(false); }
  };

  const handleSimulate = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (!val) return;
    const deltas: Record<string, number> = {
      delay_3_days: 10, delay_7_days: 25, worsening_alert: 15, supply_shortage_60pct: 5,
    };
    try {
      const res = await axios.post(
        `${API}/api/predictions/simulate?zone_id=${selectedZone}&severity_delta=${deltas[val] || 0}`
      );
      setSimulated(res.data);
    } catch { alert('Simulation failed'); }
  };

  const handleZoneChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFromIncident(false);
    setSelectedZone(e.target.value);
    setPrediction(null);
    setSimulated(null);
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  const pageTitle = fromIncident ? 'Response Plan' : 'Demand Predictions';
  const pageSubtitle = fromIncident
    ? 'Demand forecast, resource allocation, and mission dispatch for this incident'
    : 'AI-powered resource demand forecast per impact zone';

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">{pageTitle}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{pageSubtitle}</p>
        </div>
        {fromIncident && (
          <button
            onClick={() => navigate('/incidents')}
            className="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 font-semibold transition"
          >
            <ArrowLeft size={14} /> Back to Incidents
          </button>
        )}
      </div>

      {/* Context banner when arriving from incident */}
      {fromIncident && selectedMeta && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-sm font-medium ${
          ALERT_BANNER[selectedMeta.alert_level] || 'bg-slate-50 border-slate-200 text-slate-700'
        }`}>
          <span className="font-bold uppercase text-xs px-2 py-0.5 rounded-full bg-white/60 border border-current">
            {(selectedMeta.alert_level || '').toUpperCase()}
          </span>
          <span>
            Incident:{' '}
            <strong>
              {(selectedMeta.event_type || 'Event').replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </strong>
            {' '}— Severity <strong>{selectedMeta.severity}</strong> · AI Priority{' '}
            <span className={`inline-block ml-1 px-2 py-0.5 rounded text-xs font-bold uppercase ${
              PRIORITY_COLOR[selectedMeta.priority] || ''
            }`}>
              {selectedMeta.priority}
            </span>
          </span>
        </div>
      )}

      {/* Zone selector (only shown when NOT coming from incident) */}
      {!fromIncident && (
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <label className="block text-sm font-bold text-slate-700 mb-2">Select Impact Zone</label>
          <select
            className="w-full max-w-xl border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 bg-white"
            value={selectedZone}
            onChange={handleZoneChange}
          >
            <option value="">-- Choose a Zone --</option>
            {zones.map(z => (
              <option key={z.id} value={z.id}>{z.label}</option>
            ))}
          </select>
          {zones.length === 0 && (
            <p className="text-xs text-slate-400 mt-2">
              No zones classified yet. Go to Active Incidents and click "Generate Response Plan" first.
            </p>
          )}
        </div>
      )}

      {/* ── STEP 1: Demand Prediction ───────────────────────────────────────── */}
      {selectedZone && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="text-base font-bold text-slate-800 flex items-center gap-2 mb-4">
            <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center font-bold">1</span>
            Demand Forecast
            {predLoading && <Loader2 size={14} className="animate-spin text-slate-400 ml-1" />}
          </h2>

          {predError && (
            <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
              {predError}
            </div>
          )}

          {predLoading && (
            <div className="text-slate-400 text-sm animate-pulse">Running ML model...</div>
          )}

          {prediction && !predLoading && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {(['food', 'hygiene_kits', 'medical', 'shelter'] as const).map(res => {
                  const demanded  = prediction[res]?.predicted ?? 0;
                  const available = stock[res] ?? 0;
                  const covered   = available >= demanded;
                  const pct       = available > 0 ? Math.min((demanded / available) * 100, 100) : 100;
                  const unit      = RESOURCE_UNITS[res];
                  return (
                    <div key={res} className={`p-4 rounded-lg border ${covered ? 'bg-slate-50 border-slate-100' : 'bg-red-50 border-red-200'}`}>
                      <div className="flex items-center justify-between mb-1">
                        <div className={`w-2 h-2 rounded-full ${RESOURCE_COLORS[res] || 'bg-slate-400'}`} />
                        <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-full ${
                          covered ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        }`}>
                          {covered ? 'Covered' : 'Shortage'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 font-bold uppercase mb-1">{RESOURCE_LABELS[res] || res}</p>
                      <p className="text-2xl font-extrabold text-slate-800">
                        {demanded.toFixed(0)}
                        <span className="text-xs font-normal text-slate-400 ml-1">{unit}</span>
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        CI: {prediction[res]?.ci_lower?.toFixed(0)} – {prediction[res]?.ci_upper?.toFixed(0)} {unit}
                      </p>
                      {/* Demand vs available bar */}
                      <div className="mt-2">
                        <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
                          <span>Needed</span>
                          <span>Available: {available.toFixed(0)} {unit}</span>
                        </div>
                        <div className="w-full bg-slate-200 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${covered ? 'bg-green-500' : 'bg-red-500'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        {!covered && (
                          <p className="text-[10px] text-red-600 font-semibold mt-0.5">
                            Short by {(demanded - available).toFixed(0)} {unit}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Recalibrate + Simulate inline */}
              <div className="grid grid-cols-2 gap-4 mt-5">
                <div className="border border-slate-200 rounded-lg p-4">
                  <p className="text-xs font-bold text-slate-600 uppercase mb-2 flex items-center gap-1">
                    <RefreshCcw size={12} /> Recalibrate Severity
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="number" placeholder="0–100"
                      className="flex-1 border border-slate-300 rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      value={recalibrateVal}
                      onChange={e => setRecalibrateVal(e.target.value)}
                    />
                    <button
                      onClick={handleRecalibrate}
                      className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded transition"
                    >Apply</button>
                  </div>
                </div>
                <div className="border border-slate-200 rounded-lg p-4">
                  <p className="text-xs font-bold text-slate-600 uppercase mb-2 flex items-center gap-1">
                    <Zap size={12} /> Simulate Scenario
                  </p>
                  <select
                    className="w-full border border-slate-300 rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"
                    onChange={handleSimulate}
                  >
                    <option value="">-- Select --</option>
                    <option value="delay_3_days">3-Day Rescue Delay</option>
                    <option value="delay_7_days">7-Day Rescue Delay</option>
                    <option value="worsening_alert">Worsening Weather Alert</option>
                    <option value="supply_shortage_60pct">60% Supply Line Cut</option>
                  </select>
                  {simulated && (
                    <p className="text-xs text-amber-700 bg-amber-50 rounded mt-2 px-2 py-1 border border-amber-200">
                      Preview: Food {simulated.predicted_food?.toFixed(0)} pkg | Hygiene {simulated.predicted_hygiene_kits?.toFixed(0)} kits
                    </p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── STEP 2: Resource Allocation ─────────────────────────────────────── */}
      {prediction && !predLoading && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="text-base font-bold text-slate-800 flex items-center gap-2 mb-4">
            <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center font-bold">2</span>
            Resource Allocation
          </h2>

          {!allocDone && !allocLoading && (
            <div className="flex flex-col items-start gap-3">
              <p className="text-sm text-slate-500">
                Run the OR-Tools optimizer to calculate which depots send what resources to this zone.
              </p>
              <button
                onClick={handleRunAllocation}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-sm transition shadow"
              >
                <Layers size={15} /> Calculate Allocation
              </button>
              {allocError && (
                <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                  {allocError}
                </p>
              )}
            </div>
          )}

          {allocLoading && (
            <div className="flex items-center gap-2 text-slate-400 text-sm animate-pulse">
              <Loader2 size={16} className="animate-spin" /> Optimizing allocation with OR-Tools...
            </div>
          )}

          {allocDone && allocations.length > 0 && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {allocations.map((a, idx) => (
                  <div key={idx} className="border border-slate-200 p-4 rounded-lg bg-slate-50">
                    <div className={`w-2 h-2 rounded-full ${RESOURCE_COLORS[a.resource_type] || 'bg-slate-400'} mb-2`} />
                    <p className="text-xs text-slate-500 font-bold uppercase mb-1">{a.resource_type}</p>
                    <p className="text-xl font-extrabold text-slate-800">{a.quantity?.toFixed(0)} units</p>
                    <div className="mt-2 w-full bg-slate-200 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${a.coverage_percent > 80 ? 'bg-green-500' : a.coverage_percent > 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(a.coverage_percent, 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-right mt-1 text-slate-500 font-semibold">
                      {a.coverage_percent?.toFixed(1)}% coverage
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}

          {allocDone && allocations.length === 0 && !allocError && (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
              No resources available to allocate. Check depot inventory in Resources.
            </p>
          )}
        </div>
      )}

      {/* ── STEP 3: Dispatch Missions ────────────────────────────────────────── */}
      {allocDone && allocations.length > 0 && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="text-base font-bold text-slate-800 flex items-center gap-2 mb-4">
            <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center font-bold">3</span>
            Dispatch Missions
          </h2>

          {!dispatched ? (
            <div className="flex flex-col items-start gap-3">
              <p className="text-sm text-slate-500">
                Create and dispatch missions based on the allocation above. Teams and vehicles will be assigned and routes calculated.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleDispatch}
                  disabled={dispatching}
                  className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white font-bold rounded-lg text-sm transition shadow"
                >
                  {dispatching
                    ? <><Loader2 size={14} className="animate-spin" /> Dispatching...</>
                    : <><Truck size={15} /> Dispatch Missions</>
                  }
                </button>
                <button
                  onClick={() => navigate('/missions')}
                  className="flex items-center gap-2 px-4 py-2.5 border border-slate-300 text-slate-600 hover:bg-slate-50 font-semibold rounded-lg text-sm transition"
                >
                  View Missions <ChevronRight size={14} />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <CheckCircle size={20} className="text-green-600" />
              <div>
                <p className="font-bold text-green-700">Missions dispatched successfully!</p>
                <button
                  onClick={() => navigate('/missions')}
                  className="text-sm text-indigo-600 underline hover:text-indigo-800 transition mt-0.5"
                >
                  View all missions →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state — no zone selected, not from incident */}
      {!selectedZone && !fromIncident && (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-400">
          <Activity size={32} className="mx-auto mb-3 text-slate-300" />
          <p className="font-semibold text-slate-500">Select a zone above to view demand predictions</p>
          <p className="text-sm mt-1">
            Or go to{' '}
            <button
              onClick={() => navigate('/incidents')}
              className="text-indigo-500 underline hover:text-indigo-700"
            >
              Active Incidents
            </button>{' '}
            and click "Generate Response Plan" to run the full response workflow.
          </p>
        </div>
      )}
    </div>
  );
}
