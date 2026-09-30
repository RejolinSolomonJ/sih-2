import React from 'react';
import { useFleetStore } from '@/store/useFleetStore';
import { Layers, ShieldCheck, Moon, Sun, BookOpen } from 'lucide-react';

export const Header: React.FC = () => {
  const { currentProject, setCurrentProject, theme, toggleTheme, activeModelId } = useFleetStore();

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Project Selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
          <Layers className="w-4 h-4 text-teal-400" />
          <span>Project:</span>
        </div>
        <select
          value={currentProject}
          onChange={(e) => setCurrentProject(e.target.value)}
          className="bg-slate-800/90 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded-md border border-slate-700 focus:outline-none focus:border-teal-500 transition-colors"
        >
          <option value="Trans-Oceanic Green Fleet 2026">Trans-Oceanic Green Fleet 2026</option>
          <option value="Asia-Europe Zero Carbon Transition">Asia-Europe Zero Carbon Transition</option>
          <option value="Mediterranean Short-Sea Decarbonization">Mediterranean Short-Sea Decarbonization</option>
        </select>

        {/* Active Surrogate Indicator */}
        <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-800 text-xs">
          <span className="text-slate-400 text-[11px]">Surrogate Model:</span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-teal-950/80 text-teal-300 border border-teal-800/60 font-medium">
            {activeModelId || 'Physics Fallback'}
          </span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 text-[11px] font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          <span>Optimization Engine Ready</span>
        </div>

        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 px-2.5 py-1.5 rounded-md hover:bg-slate-800 transition-colors"
          title="OpenAPI Specifications"
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">API Docs</span>
        </a>

        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          title="Toggle Light/Dark Theme"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
};
