import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  Cpu,
  Compass,
  GitCompare,
  BarChart3,
  Sliders,
  Anchor,
  Atom,
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Data Management', path: '/data', icon: Database },
  { name: 'Fuel Prediction (QI)', path: '/prediction', icon: Cpu, badge: 'Quantum' },
  { name: 'Fleet Optimizer', path: '/optimizer', icon: Compass, badge: 'QIEA' },
  { name: 'Scenario Analysis', path: '/scenarios', icon: GitCompare },
  { name: 'Benchmarks', path: '/benchmarks', icon: BarChart3 },
  { name: 'Settings & Models', path: '/settings', icon: Sliders },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 h-screen sticky top-0 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 gap-3 border-b border-slate-800">
        <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
          <Anchor className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-white text-base tracking-tight">GreenFleet</span>
            <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300 font-semibold border border-teal-500/30">
              Q
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium">SIH26138 Platform</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30 shadow-xs'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full font-mono bg-teal-500/20 text-teal-300 border border-teal-500/40">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Quantum Subsystem Indicator */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] space-y-1.5">
          <div className="flex items-center justify-between text-slate-300">
            <span className="flex items-center gap-1.5">
              <Atom className="w-3.5 h-3.5 text-teal-400 animate-pulse" />
              <span>Simulated Q-Circuit</span>
            </span>
            <span className="text-[10px] text-teal-400 font-mono font-semibold">Active</span>
          </div>
          <p className="text-[10px] text-slate-400 leading-tight">
            QIEA Rotation Gate & statevector ansatz initialized.
          </p>
        </div>
      </div>
    </aside>
  );
};
