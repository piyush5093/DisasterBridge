import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import { AlertCircle, MapPin, Activity, Loader2, Filter } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const ALERT_ORDER = { red: 0, orange: 1, low: 2, green: 3 };

const ALERT_BADGE = {
  red:    'bg-red-100 text-red-700 border border-red-300',
  orange: 'bg-orange-100 text-orange-700 border border-orange-300',
  low:    'bg-yellow-100 text-yellow-700 border border-yellow-300',
  green:  'bg-emerald-100 text-emerald-700 border border-emerald-300',
};

const ALERT_ICON_BG = {
  red:    'bg-red-100 text-red-600',
  orange: 'bg-orange-100 text-orange-600',
  low:    'bg-yellow-100 text-yellow-600',
  green:  'bg-emerald-100 text-emerald-600',
};

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);
  const [filterLevel, setFilterLevel] = useState('all');
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchIncidents() {
      try {
        const res = await axios.get('http://localhost:8000/api/dashboard/events');
        setIncidents(res.data);
      } catch (err) {
        console.error("Failed to fetch incidents", err);
      } finally {
        setLoading(false);
      }
    }
    fetchIncidents();
  }, []);

  const handleGeneratePlan = async (eventId) => {
    setProcessingId(eventId);
    try {
      const res = await axios.post(`http://localhost:8000/api/zones/classify?event_id=${eventId}`);
      // classify returns grid_cell_id — pass it so predictions page auto-selects it
      const zoneId = res.data?.grid_cell_id;
      navigate(zoneId ? `/predictions?zone_id=${zoneId}` : '/predictions');
    } catch (err) {
      alert("Failed to generate plan: " + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingId(null);
    }
  };

  // Sort by alert severity (red first), then filter
  const displayed = useMemo(() => {
    const sorted = [...incidents].sort(
      (a, b) => (ALERT_ORDER[a.alert_level] ?? 9) - (ALERT_ORDER[b.alert_level] ?? 9)
    );
    if (filterLevel === 'all') return sorted;
    return sorted.filter(i => i.alert_level === filterLevel);
  }, [incidents, filterLevel]);

  const counts = useMemo(() => {
    const c = { red: 0, orange: 0, low: 0, green: 0 };
    incidents.forEach(i => { if (c[i.alert_level] !== undefined) c[i.alert_level]++; });
    return c;
  }, [incidents]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Incident Feed</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {loading ? 'Loading...' : `${incidents.length} total events — sorted by severity`}
          </p>
        </div>

        {/* Alert level filter */}
        <div className="flex items-center space-x-2">
          <Filter size={14} className="text-slate-400" />
          <span className="text-xs font-semibold text-slate-500 mr-1">Filter:</span>
          {['all', 'red', 'orange', 'low', 'green'].map(level => (
            <button
              key={level}
              onClick={() => setFilterLevel(level)}
              className={`px-3 py-1 rounded-full text-xs font-bold transition border ${
                filterLevel === level
                  ? (level === 'all' ? 'bg-slate-800 text-white border-slate-800' : ALERT_BADGE[level] + ' opacity-100')
                  : 'bg-white text-slate-500 border-slate-200 hover:border-slate-400'
              }`}
            >
              {level === 'all' ? `All (${incidents.length})` :
               level === 'red' ? `🔴 Red (${counts.red})` :
               level === 'orange' ? `🟠 Orange (${counts.orange})` :
               level === 'low' ? `🟡 Low (${counts.low})` :
               `🟢 Green (${counts.green})`}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading incidents...</div>
        ) : displayed.length === 0 ? (
          <div className="p-8 text-center text-slate-400">No incidents match this filter.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {displayed.map((incident) => (
              <div key={incident.id} className="p-5 hover:bg-slate-50 transition flex items-start">
                <div className={`mt-0.5 p-2 rounded-full mr-4 flex-shrink-0 ${ALERT_ICON_BG[incident.alert_level] || 'bg-slate-100 text-slate-600'}`}>
                  <AlertCircle size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-bold text-slate-800 leading-snug">
                      {incident.title || `Incident ${incident.id.substring(0, 8)}`}
                    </h3>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${ALERT_BADGE[incident.alert_level] || 'bg-slate-100 text-slate-600 border border-slate-200'}`}>
                      {incident.alert_level}
                    </span>
                  </div>
                  <div className="flex items-center text-xs text-slate-500 mt-1.5 space-x-4 flex-wrap gap-y-1">
                    <span className="flex items-center"><MapPin size={12} className="mr-1"/> {incident.lat.toFixed(3)}, {incident.lng.toFixed(3)}</span>
                    <span className="flex items-center"><Activity size={12} className="mr-1"/> <span className="uppercase font-medium">{incident.source}</span></span>
                  </div>
                </div>
                <button
                  onClick={() => handleGeneratePlan(incident.id)}
                  disabled={processingId === incident.id}
                  className="ml-4 flex-shrink-0 px-3 py-1.5 bg-white border border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-50 font-bold text-xs transition flex items-center disabled:opacity-50"
                >
                  {processingId === incident.id
                    ? <><Loader2 className="animate-spin mr-1.5" size={12}/> Processing...</>
                    : 'Generate Response Plan'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
