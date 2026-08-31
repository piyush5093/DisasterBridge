import React, { useState, FormEvent, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2, ShieldAlert, Eye, EyeOff, Map, Activity } from 'lucide-react';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setLoading(true);
    setError('');
    try {
      await login(email.trim(), password);
      navigate('/', { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Login failed. Please verify your credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex font-sans">
      {/* ── Left Side: Login Form (Dark/Amber Theme to match image) ── */}
      <div className="flex-1 flex flex-col justify-center px-6 sm:px-12 lg:flex-none lg:w-[480px] xl:w-[560px] bg-slate-950 border-r border-slate-800 shadow-[20px_0_40px_rgba(0,0,0,0.8)] z-10 relative">
        <div className={`mx-auto w-full max-w-sm transition-all duration-700 ease-out transform ${isMounted ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
          {/* Logo & Header */}
          <div className="mb-8">
            <div className="w-12 h-12 rounded-xl bg-orange-600 flex items-center justify-center shadow-lg shadow-orange-600/20 mb-6">
              <ShieldAlert size={24} className="text-white" />
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">Disaster Bridge</h2>
            <p className="text-sm text-slate-400 mt-2 font-medium uppercase tracking-widest">
              Commander Portal
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 text-red-400 text-sm rounded-xl px-4 py-3 flex items-start gap-2.5">
                <span className="mt-0.5">⚠</span>
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
                Commander Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="commander@disasterbridge.com"
                required
                autoFocus
                className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all sm:text-sm font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full px-4 py-3 pr-11 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all sm:text-sm font-medium"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
                  tabIndex={-1}
                >
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-orange-600 hover:bg-orange-500 disabled:opacity-70 disabled:cursor-not-allowed text-white font-bold text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-orange-900/50 mt-2"
            >
              {loading ? (
                <><Loader2 size={18} className="animate-spin" /> Authenticating...</>
              ) : (
                'Secure Sign In'
              )}
            </button>
          </form>

          <p className="text-center text-slate-600 text-xs font-medium mt-10">
            Disaster Bridge Core v2.0 &nbsp;·&nbsp; Authorized Personnel Only
          </p>
        </div>
      </div>

      {/* ── Right Side: Background Image ── */}
      <div 
        className="hidden lg:flex flex-1 relative overflow-hidden items-center justify-center bg-cover bg-center"
        style={{ backgroundImage: "url('/disaster-bg.jpg')" }}
      >
        {/* Dark vignette / gradient overlay to make text readable */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent"></div>
        <div className="absolute inset-0 bg-slate-950/20"></div>

        {/* Content */}
        <div className="relative z-10 w-full max-w-2xl px-12 mt-auto pb-24">
          <div className={`transition-all duration-1000 delay-300 ease-out transform ${isMounted ? 'translate-y-0 opacity-100' : 'translate-y-12 opacity-0'}`}>
            <h1 className="text-6xl font-extrabold text-white tracking-tight mb-2 leading-tight drop-shadow-lg">
              Disaster <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-amber-300">Bridge</span>
            </h1>
            <p className="text-lg text-orange-400 font-bold uppercase tracking-widest mb-8 drop-shadow-md">
              Disaster Resource Allocation & Relief Coordination
            </p>
            <p className="text-lg text-slate-200 mb-10 max-w-xl leading-relaxed drop-shadow-md">
              Coordinate ground resources, anticipate supply bottlenecks with machine learning, and dispatch targeted relief missions instantly during active crisis events.
            </p>

            <div className="grid grid-cols-2 gap-6">
              <div className="bg-slate-950/60 border border-white/10 rounded-2xl p-5 backdrop-blur-md">
                <Map size={24} className="text-orange-400 mb-4" />
                <h3 className="text-white font-bold mb-1">Live Relief Map</h3>
                <p className="text-sm text-slate-300 leading-relaxed">Real-time geospatial tracking of all active missions and ground events.</p>
              </div>
              <div className="bg-slate-950/60 border border-white/10 rounded-2xl p-5 backdrop-blur-md">
                <Activity size={24} className="text-amber-400 mb-4" />
                <h3 className="text-white font-bold mb-1">AI Engine Active</h3>
                <p className="text-sm text-slate-300 leading-relaxed">Random Forest demand predictions combined with OR-Tools logistics routing.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
