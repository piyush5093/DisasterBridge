import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Package, Plus, Trash2, Edit, X, Loader2, CheckCircle } from 'lucide-react';

const API = 'http://localhost:8000';

const RESOURCE_TYPES = ['food', 'water', 'medical', 'shelter', 'vehicle', 'other'];
const UNITS: Record<string, string> = {
  food: 'kg', water: 'liters', medical: 'kits',
  shelter: 'units', vehicle: 'units', other: 'units',
};

interface Resource {
  id: string; depot_name: string; resource_type: string;
  quantity: number; unit: string; status: string;
}

interface FormState {
  depot_name: string; resource_type: string;
  quantity: string; unit: string;
  lat: string; lng: string;
}

const EMPTY_FORM: FormState = {
  depot_name: '', resource_type: 'food', quantity: '',
  unit: 'kg', lat: '35.6762', lng: '139.6503',
};

export default function ResourcesPage() {
  const [resources, setResources]   = useState<Resource[]>([]);
  const [loading, setLoading]       = useState(true);

  // Add modal
  const [showAdd, setShowAdd]       = useState(false);
  const [addForm, setAddForm]       = useState<FormState>(EMPTY_FORM);
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError]     = useState('');

  // Edit modal
  const [editTarget, setEditTarget]   = useState<Resource | null>(null);
  const [editQty, setEditQty]         = useState('');
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError]     = useState('');

  // Delete error banner
  const [deleteError, setDeleteError] = useState('');

  const fetchResources = async () => {
    try {
      const res = await axios.get(`${API}/api/resources`);
      setResources(res.data);
    } catch (err) {
      console.error('Failed to fetch resources', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchResources(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddLoading(true); setAddError('');
    try {
      await axios.post(`${API}/api/resources`, {
        depot_name:    addForm.depot_name,
        resource_type: addForm.resource_type,
        quantity:      parseFloat(addForm.quantity),
        unit:          addForm.unit,
        lat:           parseFloat(addForm.lat),
        lng:           parseFloat(addForm.lng),
        status:        'available',
      });
      setShowAdd(false);
      setAddForm(EMPTY_FORM);
      await fetchResources();
    } catch (err: any) {
      setAddError(err?.response?.data?.detail || 'Failed to add resource.');
    } finally {
      setAddLoading(false);
    }
  };

  const handleEditSave = async () => {
    if (!editTarget) return;
    setEditLoading(true); setEditError('');
    try {
      await axios.put(`${API}/api/resources/${editTarget.id}`, {
        quantity: parseFloat(editQty),
      });
      setEditTarget(null);
      await fetchResources();
    } catch (err: any) {
      setEditError(err?.response?.data?.detail || 'Failed to update.');
    } finally {
      setEditLoading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Delete depot "${name}"? This cannot be undone.`)) return;
    setDeleteError('');
    try {
      await axios.delete(`${API}/api/resources/${id}`);
      fetchResources();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Delete failed. Please try again.';
      setDeleteError(msg);
      // auto-clear after 10 seconds
      setTimeout(() => setDeleteError(''), 10000);
    }
  };

  const statusStyle = (s: string) =>
    s === 'available' ? 'bg-green-100 text-green-700' :
    s === 'depleted'  ? 'bg-red-100 text-red-700' :
    'bg-amber-100 text-amber-700';

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Resource Depots</h1>
          <p className="text-sm text-slate-500 mt-1">
            Live inventory — quantities reflect real allocations and depletions
          </p>
        </div>
        <button
          onClick={() => { setShowAdd(true); setAddError(''); setAddForm(EMPTY_FORM); }}
          className="flex items-center bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg shadow-sm transition gap-2"
        >
          <Plus size={16} /> Add Depot
        </button>
      </div>

      {/* Delete error banner */}
      {deleteError && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 flex items-start gap-3">
          <span className="text-red-500 flex-shrink-0 mt-0.5">⚠</span>
          <div className="flex-1">
            <p className="text-sm font-bold text-red-700">Cannot delete depot</p>
            <p className="text-sm text-red-600 mt-0.5">{deleteError}</p>
          </div>
          <button onClick={() => setDeleteError('')} className="text-red-400 hover:text-red-600 flex-shrink-0">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Resource table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-x-auto">
        {loading ? (
          <div className="p-10 text-center text-slate-500 flex items-center justify-center gap-2">
            <Loader2 size={16} className="animate-spin" /> Loading...
          </div>
        ) : resources.length === 0 ? (
          <div className="p-10 text-center text-slate-500">
            No resource depots found. Add one to begin.
          </div>
        ) : (
          <table className="min-w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase">Depot Name</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase">Type</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase">Quantity</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase">Status</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {resources.map(r => (
                <tr key={r.id} className="hover:bg-slate-50 transition">
                  <td className="py-4 px-6 font-semibold text-slate-800 flex items-center gap-2">
                    <Package className="text-indigo-400 flex-shrink-0" size={16} />
                    {r.depot_name || `Depot ${r.id.substring(0, 6)}`}
                  </td>
                  <td className="py-4 px-6 capitalize text-slate-600 font-medium">{r.resource_type}</td>
                  <td className="py-4 px-6 font-mono font-bold text-slate-800">
                    {r.quantity.toFixed(0)}{' '}
                    <span className="text-xs text-slate-400 font-normal">{r.unit}</span>
                  </td>
                  <td className="py-4 px-6">
                    <span className={`px-2 py-1 text-xs font-bold uppercase rounded ${statusStyle(r.status)}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => { setEditTarget(r); setEditQty(String(r.quantity.toFixed(0))); setEditError(''); }}
                        className="p-1.5 text-slate-400 hover:text-indigo-600 transition"
                        title="Edit quantity"
                      >
                        <Edit size={16} />
                      </button>
                      <button
                        onClick={() => handleDelete(r.id, r.depot_name)}
                        className="p-1.5 text-slate-400 hover:text-red-600 transition"
                        title="Delete depot"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Add Depot Modal ────────────────────────────────────────────────── */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-800">Add Resource Depot</h2>
              <button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
            </div>
            <form onSubmit={handleAdd} className="p-6 space-y-4">
              {addError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{addError}</div>
              )}
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Depot Name</label>
                <input required type="text" value={addForm.depot_name}
                  onChange={e => setAddForm(f => ({ ...f, depot_name: e.target.value }))}
                  placeholder="e.g. Osaka Supply Hub"
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Resource Type</label>
                  <select value={addForm.resource_type}
                    onChange={e => setAddForm(f => ({ ...f, resource_type: e.target.value, unit: UNITS[e.target.value] || 'units' }))}
                    className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  >
                    {RESOURCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Unit</label>
                  <input type="text" value={addForm.unit}
                    onChange={e => setAddForm(f => ({ ...f, unit: e.target.value }))}
                    className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Quantity</label>
                <input required type="number" min="1" value={addForm.quantity}
                  onChange={e => setAddForm(f => ({ ...f, quantity: e.target.value }))}
                  placeholder="e.g. 5000"
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Latitude</label>
                  <input required type="number" step="any" value={addForm.lat}
                    onChange={e => setAddForm(f => ({ ...f, lat: e.target.value }))}
                    className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Longitude</label>
                  <input required type="number" step="any" value={addForm.lng}
                    onChange={e => setAddForm(f => ({ ...f, lng: e.target.value }))}
                    className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setShowAdd(false)}
                  className="flex-1 py-2.5 rounded-lg border border-slate-300 text-slate-600 text-sm font-semibold hover:bg-slate-50 transition">
                  Cancel
                </button>
                <button type="submit" disabled={addLoading}
                  className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition disabled:opacity-60 flex items-center justify-center gap-2">
                  {addLoading ? <><Loader2 size={14} className="animate-spin" />Adding...</> : 'Add Depot'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Edit Quantity Modal ────────────────────────────────────────────── */}
      {editTarget && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-slate-800 mb-1">Edit Quantity</h2>
            <p className="text-sm text-slate-500 mb-4">
              {editTarget.depot_name} — {editTarget.resource_type}
            </p>
            {editError && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3 mb-4">{editError}</div>
            )}
            <div className="flex gap-2 items-center mb-4">
              <input
                type="number" min="0" value={editQty}
                onChange={e => setEditQty(e.target.value)}
                className="flex-1 px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono font-bold"
              />
              <span className="text-slate-500 text-sm">{editTarget.unit}</span>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setEditTarget(null)}
                className="flex-1 py-2.5 rounded-lg border border-slate-300 text-slate-600 text-sm font-semibold hover:bg-slate-50 transition">
                Cancel
              </button>
              <button onClick={handleEditSave} disabled={editLoading}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition disabled:opacity-60 flex items-center justify-center gap-2">
                {editLoading ? <><Loader2 size={14} className="animate-spin" />Saving...</> : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
