import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import IncidentsPage from './pages/IncidentsPage';
import ResourcesPage from './pages/ResourcesPage';
import MissionsPage from './pages/MissionsPage';
import LogisticsPage from './pages/LogisticsPage';
import ReportsPage from './pages/ReportsPage';
import PredictionsPage from './pages/PredictionsPage';
import ReliefMapPage from './pages/ReliefMapPage';
import LoginPage from './pages/LoginPage';
import SettingsPage from './pages/SettingsPage';
import VolunteersPage from './pages/VolunteersPage';

// ── ProtectedRoute ─────────────────────────────────────────────────────────────
// Waits for the auth state to resolve (isLoading), then either renders the
// child or redirects to /login. This prevents a flash-redirect on page refresh.
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
          <span className="text-white text-sm font-bold">DB</span>
        </div>
        <span className="text-slate-500 text-sm font-medium animate-pulse">Starting Disaster Bridge...</span>
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

// ── Main app layout (only rendered when authenticated) ─────────────────────────
function AppLayout() {
  return (
    <div className="flex flex-col h-screen bg-slate-50 font-sans">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6 relative z-0">
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/incidents"  element={<IncidentsPage />} />
            <Route path="/predictions" element={<PredictionsPage />} />
            <Route path="/resources"  element={<ResourcesPage />} />
            <Route path="/volunteers" element={<VolunteersPage />} />
            <Route path="/map"        element={<ReliefMapPage />} />
            <Route path="/logistics"  element={<LogisticsPage />} />
            <Route path="/missions"   element={<MissionsPage />} />
            <Route path="/reports"    element={<ReportsPage />} />
            <Route path="/settings"   element={<SettingsPage />} />
            <Route path="*"           element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

// ── Root ───────────────────────────────────────────────────────────────────────
function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public route — login page, no protection */}
          <Route path="/login" element={<LoginPage />} />

          {/* All other routes are protected */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
