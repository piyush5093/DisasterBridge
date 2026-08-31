import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Users, Plus, Loader2, CheckCircle, Clock, AlertCircle, X, Briefcase } from 'lucide-react';

const API = 'http://localhost:8000';

const ROLE_COLORS: Record<string, string> = {
  medic:     'bg-red-100 text-red-700',
  rescue:    'bg-orange-100 text-orange-700',
  logistics: 'bg-blue-100 text-blue-700',
  general:   'bg-slate-100 text-slate-600',
};

const STATUS_CFG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  available: { color: 'bg-green-100 text-green-700',  icon: <CheckCircle size={12} />, label: 'Available' },
  deployed:  { color: 'bg-indigo-100 text-indigo-700', icon: <Briefcase size={12} />,   label: 'Deployed'  },
  off_duty:  { color: 'bg-slate-100 text-slate-500',  icon: <Clock size={12} />,        label: 'Off Duty'  },
};

const SKILLS_ALL = ['medical', 'first_aid', 'nursing', 'triage', 'counseling',
  'rescue', 'swimming', 'climbing', 'fire',
  'logistics', 'driving', 'warehouse', 'coordination', 'communication', 'cooking'];

export default function VolunteersPage() {
  const [volunteers, setVolunteers] = useState<any[]>([]);
  const [summary, setSummary]       = useState<any>(null);
  const [loading, setLoading]       = useState(true);
  const [filter, setFilter]         = useState('all');
  const [showAdd, setShowAdd]       = useState(false);
  const [saving, setSaving]         = useState(false);
  const [formError, setFormError]   = useState('');

  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', role: 'general', skills: [] as string[], notes: '',
  });

  const load = async () => {
    try {
      const [vol, sum] = await Promise.all([
        axios.get(`${API}/api/volunteers`),
        axios.get(`${API}/api/volunteers/summary`),
      ]);
      setVolunteers(vol.data);
      setSummary(sum.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const updateStatus = async (id: string, status: string) => {
    try {
      await axios.patch(`${API}/api/volunteers/${id}/status`, { status });
      setVolunteers(prev => prev.map(v => v.id === id ? { ...v, status } : v));
      const newSummary = await axios.get(`${API}/api/volunteers/summary`);
      setSummary(newSummary.data);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to update status');
    }
  };

  const deleteVolunteer = async (id: string, name: string) => {
    if (!window.confirm(`Remove ${name} from the volunteer roster?`)) return;
    try {
      await axios.delete(`${API}/api/volunteers/${id}`);
      await load();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to remove volunteer');
    }
  };

  const handleAdd = async () => {
    if (!form.full_name.trim() || !form.email.trim()) {
      setFormError('Name and email are required.'); return;
    }
    setSaving(true); setFormError('');
    try {
      await axios.post(`${API}/api/volunteers`, form);
      setShowAdd(false);
      setForm({ full_name: '', email: '', phone: '', role: 'general', skills: [], notes: '' });
      await load();
    } catch (e: any) {
      setFormError(e.response?.data?.detail || 'Failed to add volunteer');
    } finally {
      setSaving(false);
    }
  };

  const toggleSkill = (skill: string) => {
    setForm(f => ({
      ...f,
      skills: f.skills.includes(skill)
        ? f.skills.filter(s => s !== skill)
        : [...f.skills, skill],
    }));
  };

  const displayed = filter === 'all' ? volunteers : volunteers.filter(v => v.status === filter);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Volunteers</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {loading ? 'Loading...' : `${summary?.total ?? 0} registered volunteers`}
          </p>
        </div>
        <button
          onClick={() => { setShowAdd(true); setFormError(''); }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg shadow-sm transition"
        >
          <Plus size={16} /> Add Volunteer
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { key: 'all',      label: 'Total',     value: summary.total,                    color: 'text-slate-800'  },
            { key: 'available',label: 'Available',  value: summary.by_status?.available ?? 0, color: 'text-green-600' },
            { key: 'deployed', label: 'Deployed',   value: summary.by_status?.deployed ?? 0,  color: 'text-indigo-600'},
            { key: 'off_duty', label: 'Off Duty',   value: summary.by_status?.off_duty ?? 0,  color: 'text-slate-500' },
          ].map(c => (
            <button
              key={c.key}
              onClick={() => setFilter(c.key)}
              className={`bg-white p-4 rounded-xl border shadow-sm text-center transition ${
                filter === c.key ? 'border-indigo-400 ring-2 ring-indigo-100' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">{c.label}</p>
              <p className={`text-3xl font-extrabold ${c.color}`}>{c.value}</p>
            </button>
          ))}
        </div>
      )}

      {/* Volunteer table */}
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-16 flex items-center justify-center gap-2 text-slate-400">
          <Loader2 size={18} className="animate-spin" /> Loading volunteers...
        </div>
      ) : displayed.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-16 text-center">
          <Users size={36} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-semibold">No volunteers {filter !== 'all' ? `with status "${filter}"` : ''}</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Role</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Skills</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Contact</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Assigned Zone</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {displayed.map(v => {
                const statusCfg = STATUS_CFG[v.status] || STATUS_CFG.off_duty;
                return (
                  <tr key={v.id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center flex-shrink-0">
                          {v.full_name.split(' ').map((n: string) => n[0]).join('').substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-800">{v.full_name}</p>
                          <p className="text-xs text-slate-400">{v.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full capitalize ${ROLE_COLORS[v.role] || 'bg-slate-100 text-slate-600'}`}>
                        {v.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1 max-w-[180px]">
                        {v.skills.slice(0, 3).map((s: string) => (
                          <span key={s} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded capitalize">{s}</span>
                        ))}
                        {v.skills.length > 3 && (
                          <span className="text-[10px] text-slate-400">+{v.skills.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">{v.phone || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`flex items-center gap-1 w-fit text-xs font-bold px-2 py-0.5 rounded-full ${statusCfg.color}`}>
                        {statusCfg.icon} {statusCfg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {v.assigned_label || <span className="text-slate-300">Unassigned</span>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {/* Status cycle buttons */}
                        {v.status !== 'available' && (
                          <button
                            onClick={() => updateStatus(v.id, 'available')}
                            className="text-xs text-green-600 hover:text-green-800 font-semibold transition"
                            title="Mark Available"
                          >Available</button>
                        )}
                        {v.status !== 'deployed' && (
                          <button
                            onClick={() => updateStatus(v.id, 'deployed')}
                            className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold transition"
                            title="Mark Deployed"
                          >Deploy</button>
                        )}
                        {v.status !== 'off_duty' && (
                          <button
                            onClick={() => updateStatus(v.id, 'off_duty')}
                            className="text-xs text-slate-500 hover:text-slate-700 font-semibold transition"
                            title="Mark Off Duty"
                          >Off Duty</button>
                        )}
                        <button
                          onClick={() => deleteVolunteer(v.id, v.full_name)}
                          className="text-xs text-red-400 hover:text-red-600 transition ml-1"
                          title="Remove"
                        ><X size={13} /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Volunteer Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h2 className="font-bold text-slate-800 text-lg">Add Volunteer</h2>
              <button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-slate-700">
                <X size={20} />
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              {formError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg flex items-center gap-2">
                  <AlertCircle size={14} /> {formError}
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Full Name *</label>
                  <input
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                    value={form.full_name} onChange={e => setForm(f => ({...f, full_name: e.target.value}))}
                    placeholder="Arjun Mehta"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Email *</label>
                  <input
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                    value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))}
                    placeholder="arjun@example.com"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Phone</label>
                  <input
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                    value={form.phone} onChange={e => setForm(f => ({...f, phone: e.target.value}))}
                    placeholder="+91-9821001234"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Role</label>
                  <select
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none"
                    value={form.role} onChange={e => setForm(f => ({...f, role: e.target.value}))}
                  >
                    <option value="general">General</option>
                    <option value="medic">Medic</option>
                    <option value="rescue">Rescue</option>
                    <option value="logistics">Logistics</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-2">Skills (select all that apply)</label>
                <div className="flex flex-wrap gap-2">
                  {SKILLS_ALL.map(s => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => toggleSkill(s)}
                      className={`px-2.5 py-1 text-xs rounded-full border font-medium transition capitalize ${
                        form.skills.includes(s)
                          ? 'bg-indigo-600 text-white border-indigo-600'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-slate-400'
                      }`}
                    >{s}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Notes</label>
                <textarea
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-400 outline-none resize-none"
                  rows={2}
                  value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))}
                  placeholder="Any additional info..."
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
              <button
                onClick={() => setShowAdd(false)}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800 transition"
              >Cancel</button>
              <button
                onClick={handleAdd}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg transition disabled:opacity-60"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                Add Volunteer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
