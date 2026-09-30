import { create } from 'zustand';

interface FleetState {
  currentProject: string;
  theme: 'dark' | 'light';
  activeModelId: string | null;
  latestOptimizationJobId: string | null;
  setCurrentProject: (proj: string) => void;
  toggleTheme: () => void;
  setActiveModelId: (id: string | null) => void;
  setLatestOptimizationJobId: (id: string | null) => void;
}

export const useFleetStore = create<FleetState>((set) => ({
  currentProject: 'Trans-Oceanic Green Fleet 2026',
  theme: 'dark',
  activeModelId: 'qiea_xgboost_v1',
  latestOptimizationJobId: null,
  setCurrentProject: (currentProject) => set({ currentProject }),
  toggleTheme: () =>
    set((state) => {
      const next = state.theme === 'dark' ? 'light' : 'dark';
      if (next === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return { theme: next };
    }),
  setActiveModelId: (activeModelId) => set({ activeModelId }),
  setLatestOptimizationJobId: (latestOptimizationJobId) => set({ latestOptimizationJobId }),
}));
