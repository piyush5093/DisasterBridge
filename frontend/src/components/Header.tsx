import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Settings, ChevronDown, ShieldAlert } from 'lucide-react';

function useClock() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return time;
}

export default function Header() {
  const { commander, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const now = useClock();

  const initials = commander
    ? commander.full_name.split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const dateStr = now.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });

  return (
    <>
      <header className="bg-white border-b border-slate-200 shadow-sm z-30 relative flex items-center justify-between pl-0 pr-6 h-14">

        {/* ── Left: Branding (matches sidebar width exactly) ── */}
        <div className="w-60 flex-shrink-0 flex items-center gap-2.5 px-4 border-r border-slate-200 h-full">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-sm flex-shrink-0">
            <ShieldAlert size={18} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-slate-900 text-sm leading-tight tracking-tight">Disaster Bridge</p>
            <p className="text-[9px] text-slate-400 font-semibold uppercase tracking-wider leading-tight">Resource Coordination</p>
          </div>
        </div>

        {/* ── Center: Clock ── */}
        <div className="flex-1 flex items-center justify-end px-6">
          {/* Clock */}
          <div className="text-right hidden sm:block">
            <p className="text-sm font-bold text-slate-700 tabular-nums">{timeStr}</p>
            <p className="text-[10px] text-slate-400 font-medium">{dateStr}</p>
          </div>
        </div>

        {/* ── Right: Profile ── */}
        <div className="relative ml-4">
          <button
            onClick={() => setDropdownOpen(v => !v)}
            className="flex items-center gap-2.5 hover:bg-slate-50 rounded-xl px-2 py-1.5 transition focus:outline-none"
          >
            <div className="text-right hidden sm:block">
              <p className="text-sm font-bold text-slate-800 leading-tight">{commander?.full_name ?? 'Commander'}</p>
              <p className="text-[10px] text-slate-400 font-medium leading-tight">
                {commander?.role === 'admin' ? 'Administrator' : 'Field Commander'}
              </p>
            </div>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-sm">
              {initials}
            </div>
            <ChevronDown size={14} className={`text-slate-400 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
              <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-200 z-50 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-blue-50">
                  <p className="text-sm font-bold text-slate-900 truncate">{commander?.full_name}</p>
                  <p className="text-xs text-slate-500 truncate mt-0.5">{commander?.email}</p>
                  <span className="mt-1.5 inline-block px-2 py-0.5 text-[10px] font-bold uppercase rounded-full bg-blue-100 text-blue-700">
                    {commander?.role}
                  </span>
                </div>
                <button
                  onClick={() => { setDropdownOpen(false); setShowSettings(true); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition flex items-center gap-2"
                >
                  <Settings size={14} className="text-slate-400" /> Account Settings
                </button>
                <div className="border-t border-slate-100" />
                <button
                  onClick={() => { setDropdownOpen(false); logout(); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition flex items-center gap-2 font-semibold"
                >
                  <LogOut size={14} /> Sign Out
                </button>
              </div>
            </>
          )}
        </div>
      </header>

      {/* Account Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-slate-800 mb-4">Account Information</h2>
            <div className="space-y-3 text-sm">
              <div className="bg-slate-50 rounded-lg p-3">
                <span className="text-slate-400 block text-[10px] font-bold uppercase mb-0.5">Full Name</span>
                <span className="font-semibold text-slate-800">{commander?.full_name}</span>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <span className="text-slate-400 block text-[10px] font-bold uppercase mb-0.5">Email</span>
                <span className="font-semibold text-slate-800">{commander?.email}</span>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <span className="text-slate-400 block text-[10px] font-bold uppercase mb-0.5">Access Level</span>
                <span className="inline-block px-2 py-0.5 text-xs font-bold uppercase rounded-full bg-blue-100 text-blue-700">
                  {commander?.role}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-4 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              To change your password or name, ask an administrator via the Settings page.
            </p>
            <button
              onClick={() => setShowSettings(false)}
              className="mt-4 w-full py-2.5 rounded-xl bg-blue-600 text-white font-bold text-sm hover:bg-blue-700 transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
