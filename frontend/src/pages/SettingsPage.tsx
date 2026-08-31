import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { ShieldOff, ShieldCheck, UserPlus, Loader2, X, Eye, EyeOff, ShieldAlert } from 'lucide-react';

const API = 'http://localhost:8000';

interface Commander {
  id: string;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface FormState {
  full_name: string;
  email: string;
  password: string;
  role: string;
}

export default function SettingsPage() {
  const { commander: me, token } = useAuth();
  const isAdmin = me?.role === 'admin';

  const [commanders, setCommanders] = useState<Commander[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Add commander modal
  const [showModal, setShowModal] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [formError, setFormError] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  const [form, setForm] = useState<FormState>({
    full_name: '',
    email: '',
    password: '',
    role: 'commander',
  });

  const authHeader = { Authorization: `Bearer ${token}` };

  const fetchCommanders = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await axios.get(`${API}/api/commanders`, { headers: authHeader });
      setCommanders(res.data);
    } catch {
      setError('Failed to load commanders.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) fetchCommanders();
    else setLoading(false);
  }, [isAdmin]);

  const handleDeactivate = async (id: string) => {
    if (!window.confirm('Deactivate this commander? They will not be able to log in until reactivated.')) return;
    setActionLoading(id);
    setSuccess('');
    setError('');
    try {
      await axios.delete(`${API}/api/commanders/${id}`, { headers: authHeader });
      setSuccess('Commander deactivated.');
      fetchCommanders();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to deactivate.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReactivate = async (id: string) => {
    setActionLoading(id);
    setSuccess('');
    setError('');
    try {
      await axios.patch(`${API}/api/commanders/${id}/reactivate`, {}, { headers: authHeader });
      setSuccess('Commander reactivated.');
      fetchCommanders();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to reactivate.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFormLoading(true);
    try {
      await axios.post(`${API}/api/commanders`, form, { headers: authHeader });
      setShowModal(false);
      setForm({ full_name: '', email: '', password: '', role: 'commander' });
      setSuccess(`Account created for ${form.full_name}.`);
      fetchCommanders();
    } catch (e: any) {
      setFormError(e?.response?.data?.detail || 'Failed to create account.');
    } finally {
      setFormLoading(false);
    }
  };

  // ── Non-admin view ────────────────────────────────────────────────────────
  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center py-20">
        <ShieldAlert size={48} className="text-slate-300 mb-4" />
        <h2 className="text-xl font-bold text-slate-700 mb-2">Admin Access Required</h2>
        <p className="text-slate-500 text-sm">
          Only admins can manage commander accounts.<br />
          Contact your system administrator.
        </p>
      </div>
    );
  }

  // ── Admin view ────────────────────────────────────────────────────────────
  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Manage Commanders</h1>
          <p className="text-slate-500 text-sm mt-1">
            Create and manage commander accounts. Only admins can access this page.
          </p>
        </div>
        <button
          onClick={() => { setShowModal(true); setFormError(''); }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-bold transition shadow"
        >
          <UserPlus size={15} />
          Add Commander
        </button>
      </div>

      {/* Feedback banners */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3">
          {success}
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-400">
            <Loader2 size={20} className="animate-spin mr-2" /> Loading...
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">Name</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">Email</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">Role</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">Status</th>
                <th className="text-left px-5 py-3 font-semibold text-slate-600">Created</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {commanders.map(c => (
                <tr key={c.id} className={`hover:bg-slate-50 transition ${!c.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-5 py-3 font-medium text-slate-800">
                    {c.full_name}
                    {c.id === me?.id && (
                      <span className="ml-2 text-[10px] bg-indigo-100 text-indigo-600 font-bold px-1.5 py-0.5 rounded-full uppercase">You</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-slate-500">{c.email}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-block px-2 py-0.5 text-[10px] font-bold uppercase rounded-full ${
                      c.role === 'admin' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {c.role}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${
                      c.is_active ? 'text-green-600' : 'text-red-500'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${c.is_active ? 'bg-green-500' : 'bg-red-400'}`} />
                      {c.is_active ? 'Active' : 'Deactivated'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-400 text-xs">
                    {c.created_at ? new Date(c.created_at).toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' }) : '—'}
                  </td>
                  <td className="px-5 py-3 text-right">
                    {/* Can't act on yourself */}
                    {c.id !== me?.id && (
                      c.is_active ? (
                        <button
                          onClick={() => handleDeactivate(c.id)}
                          disabled={actionLoading === c.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 border border-red-200 rounded-lg transition disabled:opacity-50"
                        >
                          {actionLoading === c.id
                            ? <Loader2 size={12} className="animate-spin" />
                            : <ShieldOff size={12} />
                          }
                          Deactivate
                        </button>
                      ) : (
                        <button
                          onClick={() => handleReactivate(c.id)}
                          disabled={actionLoading === c.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-green-600 hover:bg-green-50 border border-green-200 rounded-lg transition disabled:opacity-50"
                        >
                          {actionLoading === c.id
                            ? <Loader2 size={12} className="animate-spin" />
                            : <ShieldCheck size={12} />
                          }
                          Reactivate
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Commander Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-800">Add New Commander</h2>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600 transition">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-6 space-y-4">
              {formError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
                  {formError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Full Name</label>
                <input
                  type="text"
                  required
                  value={form.full_name}
                  onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  placeholder="e.g. Commander Singh"
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Email</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  placeholder="e.g. singh@disasterbridge.com"
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Password</label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    required
                    minLength={6}
                    value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    placeholder="Minimum 6 characters"
                    className="w-full px-3 py-2.5 pr-10 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    tabIndex={-1}
                  >
                    {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                <p className="text-xs text-slate-400 mt-1">Share this password with the commander directly — it won't be shown again.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Role</label>
                <select
                  value={form.role}
                  onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition bg-white"
                >
                  <option value="commander">Commander — field operations</option>
                  <option value="admin">Admin — can manage accounts</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2.5 rounded-lg border border-slate-300 text-slate-600 text-sm font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition disabled:opacity-60 flex items-center justify-center gap-2"
                >
                  {formLoading ? <><Loader2 size={14} className="animate-spin" /> Creating...</> : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
