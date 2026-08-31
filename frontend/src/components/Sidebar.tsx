import React from 'react';
import {
  LayoutDashboard, AlertTriangle, Package, Users, Map,
  Route, Truck, FileText, Settings, Activity, ChevronRight
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const NAV = [
  {
    label: 'Overview',
    items: [
      { name: 'Dashboard',     path: '/',            icon: LayoutDashboard },
      { name: 'Relief Map',    path: '/map',          icon: Map },
    ],
  },
  {
    label: 'Incident Response',
    items: [
      { name: 'Active Incidents', path: '/incidents',   icon: AlertTriangle },
      { name: 'AI Predictions',   path: '/predictions', icon: Activity },
      { name: 'Mission Tracker',  path: '/missions',    icon: Truck },
    ],
  },
  {
    label: 'Resources',
    items: [
      { name: 'Supply Depots',  path: '/resources',  icon: Package },
      { name: 'Volunteers',     path: '/volunteers', icon: Users },
      { name: 'Logistics',      path: '/logistics',  icon: Route },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { name: 'Reports',   path: '/reports',  icon: FileText },
      { name: 'Settings',  path: '/settings', icon: Settings },
    ],
  },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-60 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col z-20">
      <nav className="flex-1 px-2 py-5 overflow-y-auto space-y-5">
        {NAV.map(section => (
          <div key={section.label}>
            {/* Section label */}
            <p className="px-3 mb-1.5 text-[10px] font-extrabold tracking-widest uppercase text-slate-400">
              {section.label}
            </p>

            {section.items.map(item => {
              const Icon = item.icon;
              const isActive =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg mb-0.5 text-sm font-semibold transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <Icon
                    size={16}
                    className={`flex-shrink-0 transition-colors ${
                      isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-600'
                    }`}
                  />
                  <span className="flex-1 truncate">{item.name}</span>
                  {isActive && (
                    <ChevronRight size={12} className="text-blue-300 flex-shrink-0" />
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer status */}
      <div className="px-4 py-3 border-t border-slate-100 bg-slate-50">
        <div className="flex items-center gap-2 mb-1">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-xs font-semibold text-slate-500">All systems operational</span>
        </div>
        <p className="text-[10px] text-slate-400 pl-4">OSRM routing · OR-Tools · Random Forest</p>
      </div>
    </aside>
  );
}
