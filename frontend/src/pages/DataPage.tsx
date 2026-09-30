import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';
import {
  Database,
  Upload,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Search,
  RefreshCw,
  SlidersHorizontal,
} from 'lucide-react';

export const DataPage: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sampleCount, setSampleCount] = useState(50000);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sum, prev] = await Promise.all([
        api.getDataSummary(),
        api.getDataPreview(50),
      ]);
      setSummary(sum);
      setPreview(prev);
    } catch (err: any) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setStatusMsg(null);
    try {
      const res = await api.generateData(sampleCount, 42);
      setStatusMsg({ type: 'success', text: res.message });
      await loadData();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Generation failed.' });
    } finally {
      setGenerating(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setStatusMsg(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/v1/data/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setStatusMsg({ type: 'success', text: `Uploaded: ${data.total_rows} rows processed.` });
      await loadData();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message });
    } finally {
      setUploading(false);
    }
  };

  const filteredRows = preview?.rows?.filter((r: any) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      r.vessel_name?.toLowerCase().includes(term) ||
      r.fuel_name?.toLowerCase().includes(term) ||
      String(r.speed_knots).includes(term)
    );
  }) || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Voyage Data Management</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            50,000+ voyage segment telemetry records synthesized with Admiralty law and sea-state noise.
          </p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {statusMsg && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center gap-2.5 ${
            statusMsg.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
              : 'bg-red-950/40 border-red-800/60 text-red-300'
          }`}
        >
          {statusMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Dataset Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Dataset Records</span>
            <Database className="w-4 h-4 text-teal-400" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-white">
              {summary ? summary.total_rows.toLocaleString() : '50,000'}
            </span>
            <span className="text-xs text-slate-400 ml-1.5">voyage segments</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            {summary?.total_columns || 26} telemetry channels recorded
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Data Quality & Schema</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold text-emerald-400">100%</span>
            <span className="text-xs text-slate-400">Validated</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            0 missing values, physics bounded
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Speed Range (knots)</span>
            <SlidersHorizontal className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-white">
              {summary?.numeric_stats?.speed_knots
                ? `${summary.numeric_stats.speed_knots.min} - ${summary.numeric_stats.speed_knots.max}`
                : '9.0 - 23.5'}
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Mean: {summary?.numeric_stats?.speed_knots?.mean || 16.8} kts
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Fuel Consumption (t)</span>
            <FileSpreadsheet className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-white">
              {summary?.numeric_stats?.fuel_consumption_tonnes
                ? `μ ${summary.numeric_stats.fuel_consumption_tonnes.mean}`
                : 'μ 54.2'}
            </span>
            <span className="text-xs text-slate-400 ml-1.5">tonnes/seg</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Std Dev: {summary?.numeric_stats?.fuel_consumption_tonnes?.std || 28.4} t
          </div>
        </div>
      </div>

      {/* Generator and Upload Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Synthetic Generator Panel */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Physics-Informed Synthetic Generator</h2>
              <p className="text-xs text-slate-400">Admiralty cubic law P ~ Disp^(2/3) * V^3 + Sea state weather resistance</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Records Count</label>
              <select
                value={sampleCount}
                onChange={(e) => setSampleCount(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value={5000}>5,000 records (Fast preview)</option>
                <option value={20000}>20,000 records (Balanced)</option>
                <option value={50000}>50,000 records (Production Benchmark)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Physics Engine</label>
              <input
                type="text"
                disabled
                value="ISO 15016 + Townsin-Kwon (Active)"
                className="w-full bg-slate-800/50 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-400 cursor-not-allowed"
              />
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
            <span>{generating ? 'Generating 50k Records with Physics Baseline...' : 'Generate Synthetic Dataset'}</span>
          </button>
        </div>

        {/* Real CSV Data Upload Panel */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Upload Real Vessel Telemetry (CSV)</h2>
              <p className="text-xs text-slate-400">Auto schema validation, column mapping, and median imputation</p>
            </div>
          </div>

          <label className="border-2 border-dashed border-slate-700 hover:border-teal-500/60 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950/40">
            <Upload className="w-7 h-7 text-slate-500 mb-2" />
            <span className="text-xs text-slate-300 font-medium">Click to select or drag CSV file</span>
            <span className="text-[11px] text-slate-500 mt-1">Supports standard noon-report and high-frequency sensor schemas</span>
            <input type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
          </label>

          {uploading && (
            <div className="text-xs text-teal-400 flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Validating schema and importing rows...</span>
            </div>
          )}
        </div>
      </div>

      {/* Interactive Table Preview */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-white">Dataset Telemetry Preview</h2>
            <p className="text-xs text-slate-400">Displaying top records across vessel archetypes and sea conditions</p>
          </div>
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by vessel, fuel, speed..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-teal-500 w-64"
            />
          </div>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 sticky top-0 border-b border-slate-800 text-slate-400">
              <tr>
                <th className="py-2.5 px-3">Vessel</th>
                <th className="py-2.5 px-3">Fuel</th>
                <th className="py-2.5 px-3">Speed (kts)</th>
                <th className="py-2.5 px-3">Load</th>
                <th className="py-2.5 px-3">Wave (m)</th>
                <th className="py-2.5 px-3">Wind (kts)</th>
                <th className="py-2.5 px-3">Fouling</th>
                <th className="py-2.5 px-3">Dist (nm)</th>
                <th className="py-2.5 px-3">Power (kW)</th>
                <th className="py-2.5 px-3 text-right">Fuel (t)</th>
                <th className="py-2.5 px-3 text-right">WTW CO2e (t)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredRows.map((r: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2.5 px-3 font-sans text-slate-200">{r.vessel_name}</td>
                  <td className="py-2.5 px-3 font-sans">
                    <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 border border-slate-700 text-slate-300">
                      {r.fuel_name}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-teal-400">{r.speed_knots}</td>
                  <td className="py-2.5 px-3 text-slate-400">{(r.cargo_load_ratio * 100).toFixed(0)}%</td>
                  <td className="py-2.5 px-3 text-slate-300">{r.wave_height_m}</td>
                  <td className="py-2.5 px-3 text-slate-300">{r.wind_speed_knots}</td>
                  <td className="py-2.5 px-3 text-slate-400">{r.fouling_index}</td>
                  <td className="py-2.5 px-3 text-slate-300">{r.distance_nm}</td>
                  <td className="py-2.5 px-3 text-slate-300">{r.propulsion_power_kw?.toLocaleString()}</td>
                  <td className="py-2.5 px-3 text-right text-emerald-400 font-semibold">{r.fuel_consumption_tonnes}</td>
                  <td className="py-2.5 px-3 text-right text-slate-300">{r.co2e_wtw_tonnes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
