import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/layout/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { DataPage } from './pages/DataPage';
import { PredictionPage } from './pages/PredictionPage';
import { OptimizerPage } from './pages/OptimizerPage';
import { ScenariosPage } from './pages/ScenariosPage';
import { BenchmarksPage } from './pages/BenchmarksPage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="data" element={<DataPage />} />
            <Route path="prediction" element={<PredictionPage />} />
            <Route path="optimizer" element={<OptimizerPage />} />
            <Route path="scenarios" element={<ScenariosPage />} />
            <Route path="benchmarks" element={<BenchmarksPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
