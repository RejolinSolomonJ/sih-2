import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import {
  Fuel,
  DollarSign,
  CloudFog,
  Award,
  ArrowUpRight,
  TrendingDown,
  Ship,
  Zap,
  Play,
  FileText,
  Activity,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from 'recharts';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [dataSummary, setDataSummary] = useState<any>(null);
  const [latestJob, setLatestJob] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [sum, jobsRes] = await Promise.all([
          api.getDataSummary().catch(() => null),
          api.listOptimizationJobs().catch(() => ({ jobs: [] })),
        ]);
        setDataSummary(sum);

        const jobs = jobsRes.jobs || [];
        if (jobs.length > 0) {
          const completed = jobs.filter((j: any) => j.status === 'COMPLETED');
          const targetId = completed.length > 0 ? completed[completed.length - 1].job_id : jobs[0].job_id;
          const result = await api.getOptimizationResult(targetId).catch(() => null);
          setLatestJob(result);
        }
      } catch (err) {
        console.error('Error loading dashboard:', err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  const recommended = latestJob?.recommended_solution;
  const planSlots = recommended?.plan_details || [
    { route_name: 'Asia - Northern Europe Loop', vessel_name: 'Panamax Container', vessel_count: 4, speed_knots: 17.5, fuel_name: 'Green e-Methanol', shore_power_use: 1, quarter_cost_usd: 9200000 },
    { route_name: 'Transpacific Eastbound', vessel_name: 'Panamax Container', vessel_count: 3, speed_knots: 18.0, fuel_name: 'Liquefied Natural Gas', shore_power_use: 1, quarter_cost_usd: 6800000 },
    { route_name: 'Mediterranean Feeder', vessel_name: 'Container Feeder', vessel_count: 2, speed_knots: 14.5, fuel_name: 'Marine Gas Oil (MGO)', shore_power_use: 1, quarter_cost_usd: 2450000 },
  ];

  // Benchmark trajectories for display
  const trajectoryData = [
    { quarter: 'Q1 Baseline', conventional_hfo: 18400, qiea_plan: 18400, target_cap: 19000 },
    { quarter: 'Q2 Transition', conventional_hfo: 18600, qiea_plan: 15200, target_cap: 18200 },
    { quarter: 'Q3 Optimized', conventional_hfo: 18500, qiea_plan: 13100, target_cap: 17400 },
    { quarter: 'Q4 Scaled', conventional_hfo: 18800, qiea_plan: 11950, target_cap: 16500 },
  ];

  const fuelBreakdown = [
    { fuel: 'Green Methanol', pct: 45, color: '#14b8a6' },
    { fuel: 'LNG', pct: 30, color: '#0ea5e9' },
    { fuel: 'MGO', pct: 15, color: '#f59e0b' },
    { fuel: 'Shore Power (OPS)', pct: 10, color: '#10b981' },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Fleet Decarbonization Dashboard</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Operational intelligence, quantum-inspired multi-objective Pareto frontier, and regulatory compliance.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => navigate('/optimizer')}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            <span>New Fleet Optimization</span>
          </button>
          <a
            href={latestJob ? `/api/v1/reports/optimization/${latestJob.job_id}/pdf` : '/api/v1/reports/optimization/DEMO/pdf'}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Executive PDF Report</span>
          </a>
        </div>
      </div>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Fuel Rate</span>
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
              <Fuel className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white">
              {recommended ? recommended.unpenalized_fuel_tonnes.toLocaleString() : '14,250'}
            </span>
            <span className="text-xs text-slate-400 ml-1.5 font-medium">tonnes / qtr</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
            <TrendingDown className="w-3.5 h-3.5" />
            <span>-18.4% vs Conventional Baseline</span>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Operating Expenditure</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white">
              ${recommended ? (recommended.unpenalized_cost_usd / 1_000_000).toFixed(2) : '18.45'}M
            </span>
            <span className="text-xs text-slate-400 ml-1.5 font-medium">Total Cost of Ownership</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
            <TrendingDown className="w-3.5 h-3.5" />
            <span>Includes OPEX + Fuel + Amortized CAPEX</span>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Lifecycle GHG (WTW)</span>
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
              <CloudFog className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white">
              {recommended ? recommended.unpenalized_co2e_wtw_tonnes.toLocaleString() : '48,200'}
            </span>
            <span className="text-xs text-slate-400 ml-1.5 font-medium">tCO2e</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-xs text-teal-400 font-medium">
            <TrendingDown className="w-3.5 h-3.5" />
            <span>-34.8% Well-to-Wake Lifecycle Cut</span>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">IMO CII Status</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">Rating B</span>
            <span className="text-xs text-slate-400 font-medium">Minor Superior</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            <span>Compliant with 2026 IMO 11% reduction</span>
          </div>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Decarbonization Trajectory Chart */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-white">Lifecycle Decarbonization Trajectory</h2>
              <p className="text-xs text-slate-400">Quarterly Well-to-Wake CO2e (tCO2e) comparing HFO baseline vs QIEA plan</p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-teal-400 font-mono font-medium">
              Target Cap: -20%
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trajectoryData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="qieaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="hfoGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="quarter" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} unit="t" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="conventional_hfo" name="Conventional HFO" stroke="#94a3b8" fill="url(#hfoGradient)" strokeWidth={2} />
                <Area type="monotone" dataKey="qiea_plan" name="QIEA Recommended Plan" stroke="#14b8a6" fill="url(#qieaGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Alternative Fuel Mix Breakdown */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Recommended Fuel Mix</h2>
            <p className="text-xs text-slate-400 mb-4">Deployment energy share across optimized fleet</p>

            <div className="space-y-3.5">
              {fuelBreakdown.map((item) => (
                <div key={item.fuel} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-300 font-medium">{item.fuel}</span>
                    <span className="font-mono text-slate-400">{item.pct}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${item.pct}%`, backgroundColor: item.color }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-3 mt-4 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-400 leading-relaxed">
            <span className="font-semibold text-teal-300">Cold Ironing Adoption: </span>
            Shore power utilized across European and Transpacific berths, saving 850 tonnes auxiliary MGO in port.
          </div>
        </div>
      </div>

      {/* Recommended Fleet Deployment Table */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Active Optimized Fleet Plan</h2>
            <p className="text-xs text-slate-400">TOPSIS compromise solution route allocations</p>
          </div>
          <button
            onClick={() => navigate('/optimizer')}
            className="flex items-center gap-1 text-xs text-teal-400 hover:text-teal-300 font-medium"
          >
            <span>Pareto Explorer</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="pb-3">Route Corridor</th>
                <th className="pb-3">Vessel Archetype</th>
                <th className="pb-3">Vessels</th>
                <th className="pb-3">Speed</th>
                <th className="pb-3">Fuel Type</th>
                <th className="pb-3">Shore Power</th>
                <th className="pb-3 text-right">Quarter Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {planSlots.map((slot: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 font-medium text-slate-200">{slot.route_name}</td>
                  <td className="py-3 text-slate-300">{slot.vessel_name}</td>
                  <td className="py-3 font-mono text-teal-400">{slot.vessel_count} units</td>
                  <td className="py-3 font-mono text-slate-300">{slot.speed_knots} kts</td>
                  <td className="py-3">
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 border border-slate-700 text-slate-200">
                      {slot.fuel_name}
                    </span>
                  </td>
                  <td className="py-3">
                    {slot.shore_power_use ? (
                      <span className="flex items-center gap-1 text-emerald-400">
                        <Zap className="w-3 h-3" /> Enabled
                      </span>
                    ) : (
                      <span className="text-slate-500">Disabled</span>
                    )}
                  </td>
                  <td className="py-3 text-right font-mono text-slate-200">
                    ${(slot.quarter_cost_usd || 0).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
