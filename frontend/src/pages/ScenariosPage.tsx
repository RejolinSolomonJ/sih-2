import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';
import {
  GitCompare,
  TrendingDown,
  DollarSign,
  Leaf,
  Anchor,
  HelpCircle,
  Zap,
  Gauge,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  ReferenceLine,
} from 'recharts';

export const ScenariosPage: React.FC = () => {
  const [pathways, setPathways] = useState<any[]>([]);
  const [carbonSens, setCarbonSens] = useState<any>(null);
  const [slowSteaming, setSlowSteaming] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadScenarios() {
      try {
        const [pw, cs, ss] = await Promise.all([
          api.getFuelPathways(),
          api.getCarbonSensitivity(),
          api.getSlowSteaming('panamax_container'),
        ]);
        setPathways(pw.scenarios || []);
        setCarbonSens(cs);
        setSlowSteaming(ss || []);
      } catch (err) {
        console.error('Error loading scenarios:', err);
      } finally {
        setLoading(false);
      }
    }
    loadScenarios();
  }, []);

  const chartPathways = pathways.map((s) => ({
    name: s.name.replace('Baseline ', '').replace(' (Cold Ironing)', ''),
    cost_millions: s.total_cost_usd / 1_000_000,
    ghg_thousands: s.total_co2e_wtw_tonnes / 1_000,
  }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Decarbonization Scenario Analysis</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Side-by-side evaluation of alternative marine fuel pathways, carbon price thresholds, and slow steaming.
        </p>
      </div>

      {/* Fuel Transition Pathways Table */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Fuel Pathways Comparison vs Conventional Baseline</h2>
          <p className="text-xs text-slate-400">Quarterly fleet operational costs, lifecycle Well-to-Wake CO2e, and marginal abatement costs</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="pb-2.5">Scenario / Energy Pathway</th>
                <th className="pb-2.5">Shore Power</th>
                <th className="pb-2.5">Fuel Consumed (t)</th>
                <th className="pb-2.5">Quarter Cost ($M)</th>
                <th className="pb-2.5">Cost Delta</th>
                <th className="pb-2.5">WTW GHG (kt)</th>
                <th className="pb-2.5">GHG Cut</th>
                <th className="pb-2.5 text-right">Abatement Cost ($/t)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {pathways.map((s: any) => (
                <tr key={s.scenario_id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2.5 font-sans font-medium text-slate-200">{s.name}</td>
                  <td className="py-2.5 font-sans">
                    {s.shore_power_forced ? (
                      <span className="flex items-center gap-1 text-emerald-400 font-medium text-[11px]">
                        <Zap className="w-3 h-3" /> Mandatory
                      </span>
                    ) : (
                      <span className="text-slate-500 text-[11px]">Standard</span>
                    )}
                  </td>
                  <td className="py-2.5 text-slate-300">{s.total_fuel_tonnes?.toLocaleString()}</td>
                  <td className="py-2.5 text-slate-200 font-semibold">
                    ${(s.total_cost_usd / 1_000_000).toFixed(2)}M
                  </td>
                  <td className="py-2.5">
                    <span className={s.delta_cost_pct > 0 ? 'text-amber-400' : 'text-emerald-400'}>
                      {s.delta_cost_pct > 0 ? `+${s.delta_cost_pct}%` : `${s.delta_cost_pct}%`}
                    </span>
                  </td>
                  <td className="py-2.5 text-teal-400 font-semibold">
                    {(s.total_co2e_wtw_tonnes / 1000).toFixed(1)} kt
                  </td>
                  <td className="py-2.5 text-emerald-400 font-bold">
                    {s.delta_ghg_pct > 0 ? `+${s.delta_ghg_pct}%` : `${s.delta_ghg_pct}%`}
                  </td>
                  <td className="py-2.5 text-right text-slate-300">
                    {s.marginal_abatement_cost > 0 ? `$${s.marginal_abatement_cost}/t` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost vs GHG Comparison Chart */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <h2 className="text-sm font-semibold text-white">Cost vs. Emissions Trade-Off Across Fuels</h2>
          <p className="text-xs text-slate-400">Total quarterly fleet cost ($M) alongside lifecycle GHG (kt CO2e)</p>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartPathways} margin={{ top: 15, right: 15, left: -15, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="cost_millions" name="Cost ($ Millions)" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ghg_thousands" name="GHG (kt CO2e)" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Carbon Price Sensitivity & Break-Even Chart */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Carbon Price Sensitivity & Break-Even Curve</h2>
              <p className="text-xs text-slate-400">Fleet cost trajectories across ETS carbon levy from $0 to $300 / tonne</p>
            </div>
            {carbonSens && (
              <span className="text-xs font-mono px-2.5 py-1 rounded bg-teal-500/20 text-teal-300 border border-teal-500/40">
                Break-Even: ${carbonSens.breakeven_carbon_price_usd}/t
              </span>
            )}
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={carbonSens?.curve || []} margin={{ top: 15, right: 15, left: -5, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="carbon_price_usd" unit="$" stroke="#64748b" tick={{ fontSize: 11 }} label={{ value: 'Carbon Price ($/t)', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} />
                <Tooltip
                  formatter={(val: any) => [`$${(Number(val) / 1e6).toFixed(2)}M`, '']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                <Line type="monotone" dataKey="hfo_total_cost_usd" name="HFO Fleet" stroke="#94a3b8" strokeWidth={2} />
                <Line type="monotone" dataKey="methanol_total_cost_usd" name="Green Methanol Fleet" stroke="#14b8a6" strokeWidth={2} />
                <Line type="monotone" dataKey="ammonia_total_cost_usd" name="Ammonia Fleet" stroke="#f59e0b" strokeWidth={2} />
                {carbonSens && (
                  <ReferenceLine x={carbonSens.breakeven_carbon_price_usd} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'Break-Even', fill: '#ef4444', fontSize: 10 }} />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Slow Steaming Analysis Section */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Speed Reduction (Slow Steaming) Operational Curve</h2>
          <p className="text-xs text-slate-400">
            Admiralty power scaling on 6,000 nm Transoceanic voyage for Panamax Container
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400">
              <tr>
                <th className="py-2.5 px-3">Cruising Speed</th>
                <th className="py-2.5 px-3">Voyage Duration</th>
                <th className="py-2.5 px-3">Engine Power</th>
                <th className="py-2.5 px-3">Engine Load</th>
                <th className="py-2.5 px-3">Fuel / Day</th>
                <th className="py-2.5 px-3">Total Fuel (t)</th>
                <th className="py-2.5 px-3">Fuel Cost</th>
                <th className="py-2.5 px-3 text-right">WTW CO2e (t)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {slowSteaming.map((row: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2 px-3 font-semibold text-teal-400">{row.speed_knots} kts</td>
                  <td className="py-2 px-3 text-slate-300">{row.voyage_days} days</td>
                  <td className="py-2 px-3 text-slate-300">{row.propulsion_power_kw?.toLocaleString()} kW</td>
                  <td className="py-2 px-3 text-slate-400">{(row.engine_load_fraction * 100).toFixed(0)}%</td>
                  <td className="py-2 px-3 text-amber-400 font-semibold">{row.fuel_per_day_tonnes} t/d</td>
                  <td className="py-2 px-3 text-emerald-400 font-bold">{row.fuel_consumption_tonnes} t</td>
                  <td className="py-2 px-3 text-slate-200">${row.fuel_cost_usd?.toLocaleString()}</td>
                  <td className="py-2 px-3 text-right text-slate-300">{row.co2e_wtw_tonnes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
