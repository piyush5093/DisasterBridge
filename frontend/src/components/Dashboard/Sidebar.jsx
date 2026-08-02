import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Map, AlertTriangle, Package,
  Building2, Users, Radio, Zap, Activity
} from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Overview',   to: '/',           icon: LayoutDashboard },
  { label: 'Live Map',   to: '/map',        icon: Map },
  { label: 'Zones',      to: '/zones',      icon: AlertTriangle },
  { label: 'Resources',  to: '/resources',  icon: Package },
  { label: 'Depots',     to: '/depots',     icon: Building2 },
  { label: 'Teams',      to: '/teams',      icon: Users },
  { label: 'Live Feed',  to: '/feed',       icon: Radio },
  { label: 'Allocation', to: '/allocation', icon: Zap },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🚨</div>
        <div className="sidebar-logo-text">
          <h1>DisasterAI</h1>
          <span>Command Center</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="status-indicator">
          <div className="status-dot" />
          <span>API Online — :8000</span>
        </div>
      </div>
    </aside>
  );
}
