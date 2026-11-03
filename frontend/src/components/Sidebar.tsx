import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Settings,
  Sparkles,
  Clapperboard,
  ShieldCheck,
  Video,
} from 'lucide-react';
import { useStore } from '../store/useStore';

export const Sidebar: React.FC = () => {
  const currentProject = useStore((state) => state.currentProject);
  const currentEpisode = useStore((state) => state.currentEpisode);
  const servicesStatus = useStore((state) => state.servicesStatus);

  const connectedCount = servicesStatus.filter((s) => s.connected).length;
  const totalCount = servicesStatus.length;

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/characters', label: 'Karakter Kluis', icon: Users },
    { to: '/setup', label: 'Setup Centrum', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0 h-screen sticky top-0 select-none">
      <div>
        {/* Logo / Header */}
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 via-rose-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-wide flex items-center gap-1.5">
              AI-Studio
              <span className="text-[10px] uppercase font-extrabold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                KidsEdu
              </span>
            </h1>
            <p className="text-xs text-slate-400">Viral Video Creator</p>
          </div>
        </div>

        {/* Current Active Context */}
        {currentProject && (
          <div className="mx-4 mt-4 p-3 rounded-lg bg-slate-800/60 border border-slate-700/60">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Huidig Project
            </div>
            <div className="text-sm font-medium text-slate-200 truncate flex items-center gap-2">
              <Clapperboard className="w-4 h-4 text-amber-400 shrink-0" />
              <span className="truncate">{currentProject.name}</span>
            </div>
            {currentEpisode && (
              <div className="mt-2 pt-2 border-t border-slate-700/40 text-xs text-indigo-300 truncate flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{currentEpisode.title}</span>
              </div>
            )}
          </div>
        )}

        {/* Main Navigation */}
        <nav className="p-4 space-y-1.5 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/70'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer / Status Indicator */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/50">
        <NavLink
          to="/setup"
          className="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/40 transition-colors"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-xs text-slate-300 font-medium">AI Services</span>
          </div>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-bold ${
              connectedCount > 0
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
            }`}
          >
            {connectedCount}/{totalCount || 6} Actief
          </span>
        </NavLink>
      </div>
    </aside>
  );
};

