import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { useFleetStore } from '@/store/useFleetStore';
import {
  Compass,
  Play,
  Activity,
  Layers,
  CheckCircle2,
  FileText,
  Sliders,
  Sparkles,
  Zap,
  Target,
  Award,
  RefreshCw,
} from 'lucide-react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

export const OptimizerPage: React.FC = () => {
  const { latestOptimizationJobId, setLatestOptimizationJobId } = useFleetStore();

  const [algorithm, setAlgorithm] = useState('QIEA-NSGA');
  const [popSize, setPopSize] = useState(24);
  const [generations, setGenerations] = useState(25);
  const [carbonPrice, setCarbonPrice] = useState(85.0);
  const [weightFuel, setWeightFuel] = useState(0.33);
  const [weightCost, setWeightCost] = useState(0.34);
  const [weightGhg, setWeightGhg] = useState(0.33);
  const [useSurrogate, setUseSurrogate] = useState(true);

  const [running, setRunning] = useState(false);
  const [currentGen, setCurrentGen] = useState(0);
  const [currentHv, setCurrentHv] = useState(0);
  const [liveHistory, setLiveHistory] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [selectedSolution, setSelectedSolution] = useState<any>(null);

  // Load latest completed job on mount if available
  useEffect(() => {
    async function loadLatest() {
      try {
        const jobsRes = await api.listOptimizationJobs();
        const completed = (jobsRes.jobs || []).filter((j: any) => j.status === 'COMPLETED');
        if (completed.length > 0) {
          const targetId = latestOptimizationJobId || completed[completed.length - 1].job_id;
          const res = await api.getOptimizationResult(targetId);
          setResult(res);
          setSelectedSolution(res.recommended_solution);
          setLiveHistory(res.convergence_history || []);
        }
      } catch (err) {
        console.error('Error loading latest optimization:', err);
      }
    }
    loadLatest();
  }, [latestOptimizationJobId]);

  const handleStartOptimization = async () => {
    setRunning(true);
    setResult(null);
    setSelectedSolution(null);
    setCurrentGen(0);
    setCurrentHv(0);
    setLiveHistory([]);

    try {
      const startRes = await api.startOptimization({
        algorithm,
        population_size: popSize,
        generations: generations,
        carbon_price_usd: carbonPrice,
        topsis_weights: [weightFuel, weightCost, weightGhg],
        use_surrogate: useSurrogate,
        seed: 42,
      });

      const jobId = startRes.job_id;
      setLatestOptimizationJobId(jobId);

      // Connect to SSE stream
      const eventSource = new EventSource(`/api/v1/optimize/${jobId}/stream`);

      eventSource.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.done) {
            eventSource.close();
            setRunning(false);
            // Fetch final result
            const finalRes = await api.getOptimizationResult(jobId);
            setResult(finalRes);
            setSelectedSolution(finalRes.recommended_solution);
            setLiveHistory(finalRes.convergence_history || []);
          } else {
            setCurrentGen(data.generation);
            setCurrentHv(data.hypervolume);
            setLiveHistory((prev) => [...prev, data]);
          }
        } catch (e) {
          console.error('Error parsing SSE event:', e);
        }
      };

      eventSource.onerror = async () => {
        eventSource.close();
        // Fallback polling
        setTimeout(async () => {
          try {
            const finalRes = await api.getOptimizationResult(jobId);
            setResult(finalRes);
            setSelectedSolution(finalRes.recommended_solution);
            setRunning(false);
          } catch (e) {
            setRunning(false);
          }
        }, 1500);
      };
    } catch (err: any) {
      alert(`Optimization failed: ${err.message}`);
      setRunning(false);
    }
  };

  // Prepare Pareto scatter points (Cost vs GHG vs Fuel)
  const paretoScatter = (result?.pareto_front || []).map((sol: any) => ({
    id: sol.solution_id,
    cost_millions: sol.unpenalized_cost_usd / 1_000_000,
    ghg_thousands: sol.unpenalized_co2e_wtw_tonnes / 1_000,
    fuel_thousands: sol.unpenalized_fuel_tonnes / 1_000,
    is_recommended: sol.is_topsis_recommended,
    topsis_score: sol.topsis_score,
    raw: sol,
  }));

  const activePlan = selectedSolution?.plan_details || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Quantum-Inspired Fleet Optimizer</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/40 font-mono font-medium">
              Multi-Objective Pareto
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-0.5">
            QIEA-NSGA Q-bit rotation optimization balancing Fuel, Operating Cost, and Lifecycle Well-to-Wake GHG.
          </p>
        </div>

        {result && (
          <a
            href={`/api/v1/reports/optimization/${result.job_id}/pdf`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors self-start sm:self-auto"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Export Solution PDF</span>
          </a>
        )}
      </div>

      {/* Configuration & Controls Panel */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-teal-400" />
          <h2 className="text-sm font-semibold text-white">Optimization Parameters & Algorithm Setup</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Algorithm</label>
            <select
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="QIEA-NSGA">QIEA-NSGA (Quantum-Inspired NSGA)</option>
              <option value="QPSO-MO">QPSO-MO (Quantum Particle Swarm)</option>
              <option value="NSGA-II">NSGA-II Baseline</option>
              <option value="MOPSO">MOPSO Baseline</option>
              <option value="Weighted-Sum GA">Weighted-Sum GA Baseline</option>
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Generations: {generations}</label>
            <input
              type="range"
              min={10}
              max={60}
              step={5}
              value={generations}
              onChange={(e) => setGenerations(Number(e.target.value))}
              className="w-full accent-teal-500 cursor-pointer"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Population Size: {popSize}</label>
            <input
              type="range"
              min={12}
              max={48}
              step={4}
              value={popSize}
              onChange={(e) => setPopSize(Number(e.target.value))}
              className="w-full accent-teal-500 cursor-pointer"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Carbon Levy: ${carbonPrice}/t</label>
            <input
              type="number"
              min={0}
              max={300}
              value={carbonPrice}
              onChange={(e) => setCarbonPrice(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Surrogate Evaluator</label>
            <div className="flex items-center gap-2 h-9 px-3 bg-slate-800 border border-slate-700 rounded-lg">
              <input
                type="checkbox"
                id="surrogateCheck"
                checked={useSurrogate}
                onChange={(e) => setUseSurrogate(e.target.checked)}
                className="accent-teal-500 rounded"
              />
              <label htmlFor="surrogateCheck" className="text-xs text-slate-300 cursor-pointer select-none">
                ML Surrogate Model
              </label>
            </div>
          </div>
        </div>

        {/* TOPSIS Weights */}
        <div className="pt-2 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span className="font-medium text-slate-300">TOPSIS Decision Weights:</span>
            <span>Fuel: {(weightFuel * 100).toFixed(0)}%</span>
            <span>Cost: {(weightCost * 100).toFixed(0)}%</span>
            <span>GHG: {(weightGhg * 100).toFixed(0)}%</span>
          </div>

          <button
            onClick={handleStartOptimization}
            disabled={running}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs font-semibold shadow-xs transition-colors self-end sm:self-auto"
          >
            <Play className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
            <span>{running ? `Optimizing Generation ${currentGen}/${generations}...` : 'Run Quantum-Inspired Optimization'}</span>
          </button>
        </div>
      </div>

      {/* Live Progress Banner during execution */}
      {running && (
        <div className="p-4 rounded-xl bg-teal-950/40 border border-teal-800/60 text-xs text-teal-300 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <RefreshCw className="w-4 h-4 animate-spin text-teal-400" />
            <span>
              Executing {algorithm} across {popSize} chromosomes — Generation {currentGen} of {generations}
            </span>
          </div>
          <div className="font-mono text-teal-200">
            Pareto Hypervolume: {currentHv?.toLocaleString()}
          </div>
        </div>
      )}

      {/* Pareto Front Explorer & Convergence History */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Interactive Pareto Front Scatter Plot */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Pareto Optimal Frontier (2D Projection)</h2>
              <p className="text-xs text-slate-400">Fleet Cost ($M) vs. Lifecycle GHG (kt CO2e). Gold = TOPSIS recommended</p>
            </div>
            {result && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-teal-300 border border-slate-700">
                {result.total_pareto_count} Non-Dominated Solutions
              </span>
            )}
          </div>

          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 15, right: 20, bottom: 15, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  type="number"
                  dataKey="cost_millions"
                  name="Cost"
                  unit="M"
                  stroke="#64748b"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'Fleet Cost ($ Millions)', position: 'insideBottom', offset: -10, fill: '#64748b', fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="ghg_thousands"
                  name="GHG"
                  unit="kt"
                  stroke="#64748b"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'Lifecycle GHG (kt CO2e)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }}
                />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ payload }) => {
                    if (!payload || !payload[0]) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-700 text-xs shadow-md">
                        <div className="font-semibold text-slate-200">
                          {d.is_recommended ? '★ TOPSIS Recommended Solution' : `Solution #${d.id}`}
                        </div>
                        <div className="text-teal-400 mt-1">Cost: ${d.cost_millions?.toFixed(2)}M</div>
                        <div className="text-slate-300">GHG: {(d.ghg_thousands * 1000)?.toLocaleString()} tCO2e</div>
                        <div className="text-slate-400">Fuel: {(d.fuel_thousands * 1000)?.toLocaleString()} tonnes</div>
                        <div className="text-slate-500 text-[10px] mt-1">Click dot to select & inspect plan</div>
                      </div>
                    );
                  }}
                />
                <Scatter
                  name="Pareto Solutions"
                  data={paretoScatter}
                  fill="#14b8a6"
                  onClick={(entry: any) => setSelectedSolution(entry?.raw || entry)}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Hypervolume Convergence Curve */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Hypervolume Convergence Curve</h2>
              <p className="text-xs text-slate-400">Front expansion and coverage progression across generations</p>
            </div>
          </div>

          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={liveHistory} margin={{ top: 15, right: 20, bottom: 15, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="generation" stroke="#64748b" tick={{ fontSize: 11 }} label={{ value: 'Generation', position: 'insideBottom', offset: -10, fill: '#64748b', fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Line type="monotone" dataKey="hypervolume" stroke="#0ea5e9" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Selected Compromise Solution Highlight Banner */}
      {selectedSolution && (
        <div className="p-5 rounded-xl bg-slate-900 border border-teal-500/40 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-300">
                <Award className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>{selectedSolution.is_topsis_recommended ? 'TOPSIS Optimal Compromise Fleet Plan' : `Inspected Solution #${selectedSolution.solution_id}`}</span>
                  {selectedSolution.is_topsis_recommended && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 font-mono">
                      Recommended
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400">Balanced trade-off solution across multi-objective Pareto front</p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono">
              <div>
                <span className="text-slate-400 font-sans">Fuel: </span>
                <span className="text-emerald-400 font-semibold">{selectedSolution.unpenalized_fuel_tonnes?.toLocaleString()} t</span>
              </div>
              <div>
                <span className="text-slate-400 font-sans">Cost: </span>
                <span className="text-slate-200 font-semibold">${(selectedSolution.unpenalized_cost_usd || 0).toLocaleString()}</span>
              </div>
              <div>
                <span className="text-slate-400 font-sans">GHG: </span>
                <span className="text-teal-300 font-semibold">{selectedSolution.unpenalized_co2e_wtw_tonnes?.toLocaleString()} tCO2e</span>
              </div>
            </div>
          </div>

          {/* Route Deployment Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-2.5 px-3">Route Corridor</th>
                  <th className="py-2.5 px-3">Vessel Type</th>
                  <th className="py-2.5 px-3">Fleet Size</th>
                  <th className="py-2.5 px-3">Cruising Speed</th>
                  <th className="py-2.5 px-3">Fuel Selection</th>
                  <th className="py-2.5 px-3">Shore Power</th>
                  <th className="py-2.5 px-3">Cargo Demand Met</th>
                  <th className="py-2.5 px-3 text-right">Quarter Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {activePlan.map((slot: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 px-3 font-sans font-medium text-slate-200">{slot.route_name}</td>
                    <td className="py-2.5 px-3 font-sans text-slate-300">{slot.vessel_name}</td>
                    <td className="py-2.5 px-3 text-teal-400 font-semibold">{slot.vessel_count} units</td>
                    <td className="py-2.5 px-3 text-slate-300">{slot.speed_knots} kts</td>
                    <td className="py-2.5 px-3 font-sans">
                      <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 border border-slate-700 text-slate-300 font-medium">
                        {slot.fuel_name}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      {slot.shore_power_use ? (
                        <span className="flex items-center gap-1 text-emerald-400">
                          <Zap className="w-3 h-3" /> Yes
                        </span>
                      ) : (
                        <span className="text-slate-500">No</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-emerald-400 font-sans">
                      {slot.cargo_transported?.toLocaleString()} / {slot.cargo_demand?.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-200 font-semibold">
                      ${(slot.quarter_cost_usd || 0).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
