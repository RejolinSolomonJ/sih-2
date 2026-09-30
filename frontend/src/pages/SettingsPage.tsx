import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';
import {
  Sliders,
  Fuel,
  Ship,
  ShieldCheck,
  Zap,
  Gauge,
  Play,
  Calculator,
  Info,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [fuels, setFuels] = useState<any[]>([]);
  const [vessels, setVessels] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'fuels' | 'vessels' | 'speed_tool' | 'compliance'>('fuels');

  // What-if Speed Optimizer state
  const [optVessel, setOptVessel] = useState('panamax_container');
  const [optFuel, setOptFuel] = useState('hfo');
  const [optDist, setOptDist] = useState(4800);
  const [optEta, setOptEta] = useState(260);
  const [speedOptResult, setSpeedOptResult] = useState<any>(null);
  const [optimizingSpeed, setOptimizingSpeed] = useState(false);

  // Compliance Calculator state
  const [compCat, setCompCat] = useState('container');
  const [compCap, setCompCap] = useState(5200);
  const [compFuel, setCompFuel] = useState(18500);
  const [compDist, setCompDist] = useState(85000);
  const [compResult, setCompResult] = useState<any>(null);
  const [calculatingComp, setCalculatingComp] = useState(false);

  useEffect(() => {
    async function loadConfigs() {
      try {
        const [f, v] = await Promise.all([api.getFuels(), api.getVessels()]);
        setFuels(f.fuels || []);
        setVessels(v.vessels || []);
      } catch (err) {
        console.error('Error loading config:', err);
      }
    }
    loadConfigs();
  }, []);

  const handleSpeedOptimize = async () => {
    setOptimizingSpeed(true);
    try {
      const res = await api.optimizeSpeed({
        vessel_id: optVessel,
        fuel_id: optFuel,
        distance_nm: optDist,
        target_eta_hours: optEta,
      });
      setSpeedOptResult(res);
    } catch (err: any) {
      alert(`Speed optimization failed: ${err.message}`);
    } finally {
      setOptimizingSpeed(false);
    }
  };

  const handleCalcCompliance = async () => {
    setCalculatingComp(true);
    try {
      const res = await api.getCompliance({
        vessel_category: compCat,
        capacity: compCap,
        annual_fuel_tonnes: compFuel,
        annual_distance_nm: compDist,
      });
      setCompResult(res);
    } catch (err: any) {
      alert(`Compliance calculation failed: ${err.message}`);
    } finally {
      setCalculatingComp(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Domain Models & Specialized Tools</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Marine fuel lifecycle emission factors, vessel naval specs, single-voyage speed optimizer, and IMO CII compliance.
        </p>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab('fuels')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === 'fuels'
              ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Fuel className="w-3.5 h-3.5" />
          <span>Marine Fuels Config ({fuels.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('vessels')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === 'vessels'
              ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Ship className="w-3.5 h-3.5" />
          <span>Vessel Archetypes ({vessels.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('speed_tool')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === 'speed_tool'
              ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Gauge className="w-3.5 h-3.5" />
          <span>What-If Speed Optimizer</span>
        </button>

        <button
          onClick={() => setActiveTab('compliance')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === 'compliance'
              ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>IMO CII & EU ETS Compliance</span>
        </button>
      </div>

      {/* Tab 1: Marine Fuels */}
      {activeTab === 'fuels' && (
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Configured Marine Fuels & Energy Carriers</h2>
              <p className="text-xs text-slate-400">
                Source: IMO 4th GHG Study & FuelEU Maritime (Regulation (EU) 2023/1805)
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-medium">
                  <th className="pb-2.5">Fuel Name</th>
                  <th className="pb-2.5">Category</th>
                  <th className="pb-2.5">LCV (MJ/kg)</th>
                  <th className="pb-2.5">Cost ($/t)</th>
                  <th className="pb-2.5">Tank-to-Wake (TtW)</th>
                  <th className="pb-2.5">Well-to-Tank (WtT)</th>
                  <th className="pb-2.5 text-right">Lifecycle WTW (tCO2e/t)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {fuels.map((f: any) => (
                  <tr key={f.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 font-sans font-medium text-slate-200">{f.name}</td>
                    <td className="py-2.5 font-sans text-slate-400">{f.category}</td>
                    <td className="py-2.5 text-slate-300">{f.lcv_mj_per_kg}</td>
                    <td className="py-2.5 text-teal-400 font-semibold">${f.cost_per_tonne_usd}</td>
                    <td className="py-2.5 text-slate-300">{f.emission_factor_ttw}</td>
                    <td className="py-2.5 text-slate-400">{f.emission_factor_wtt}</td>
                    <td className="py-2.5 text-right font-bold text-emerald-400">{f.emission_factor_wtw}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Vessel Archetypes */}
      {activeTab === 'vessels' && (
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Configured Vessel Archetypes</h2>
            <p className="text-xs text-slate-400">Clarkson's Research / IMO Technical Parameters</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-medium">
                  <th className="pb-2.5">Vessel Archetype</th>
                  <th className="pb-2.5">Capacity</th>
                  <th className="pb-2.5">Design Speed</th>
                  <th className="pb-2.5">Engine MCR</th>
                  <th className="pb-2.5">Base SFOC</th>
                  <th className="pb-2.5">CAPEX ($M)</th>
                  <th className="pb-2.5">OPEX ($/d)</th>
                  <th className="pb-2.5 text-right">Shore Power</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {vessels.map((v: any) => (
                  <tr key={v.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 font-sans font-medium text-slate-200">{v.name}</td>
                    <td className="py-2.5 text-slate-300">
                      {v.capacity.toLocaleString()} {v.capacity_unit}
                    </td>
                    <td className="py-2.5 text-teal-400">{v.design_speed_knots} kts</td>
                    <td className="py-2.5 text-slate-300">{v.engine_mcr_kw?.toLocaleString()} kW</td>
                    <td className="py-2.5 text-slate-300">{v.base_sfoc_g_per_kwh} g/kWh</td>
                    <td className="py-2.5 text-slate-200">${(v.capex_usd / 1e6).toFixed(1)}M</td>
                    <td className="py-2.5 text-slate-300">${v.opex_usd_per_day}</td>
                    <td className="py-2.5 text-right font-sans">
                      {v.shore_power_equipped ? (
                        <span className="text-emerald-400 font-semibold text-[11px]">Equipped</span>
                      ) : (
                        <span className="text-slate-500 text-[11px]">Retrofit Req</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: What-If Speed Optimizer */}
      {activeTab === 'speed_tool' && (
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-white">What-If Single Voyage Speed Optimizer</h2>
            <p className="text-xs text-slate-400">
              Minimizes total trip cost (Fuel expense + Vessel charter rate + Late arrival penalty) given target ETA
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Vessel</label>
              <select
                value={optVessel}
                onChange={(e) => setOptVessel(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value="panamax_container">Panamax Container</option>
                <option value="container_feeder">Container Feeder</option>
                <option value="bulk_carrier_panamax">Bulk Carrier</option>
                <option value="tanker_aframax">Tanker Aframax</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Fuel</label>
              <select
                value={optFuel}
                onChange={(e) => setOptFuel(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value="hfo">Heavy Fuel Oil / VLSFO</option>
                <option value="mgo">Marine Gas Oil</option>
                <option value="lng">LNG</option>
                <option value="methanol_green">Green Methanol</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Distance: {optDist} nm</label>
              <input
                type="number"
                min={200}
                max={15000}
                value={optDist}
                onChange={(e) => setOptDist(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Target ETA Window: {optEta} hours</label>
              <input
                type="number"
                min={24}
                max={800}
                value={optEta}
                onChange={(e) => setOptEta(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <button
            onClick={handleSpeedOptimize}
            disabled={optimizingSpeed}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Play className={`w-3.5 h-3.5 ${optimizingSpeed ? 'animate-spin' : ''}`} />
            <span>{optimizingSpeed ? 'Calculating Optimal Speed...' : 'Compute Optimal Speed'}</span>
          </button>

          {speedOptResult && (
            <div className="p-5 rounded-xl bg-slate-950/80 border border-teal-500/40 grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div>
                <span className="text-xs text-slate-400 font-medium">Optimal Cruising Speed</span>
                <div className="mt-1 font-mono text-2xl font-bold text-teal-300">
                  {speedOptResult.optimal_speed_knots} knots
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  Engine Load: {speedOptResult.engine_load_pct}% MCR
                </div>
              </div>

              <div>
                <span className="text-xs text-slate-400 font-medium">Voyage Duration</span>
                <div className="mt-1 font-mono text-2xl font-bold text-white">
                  {speedOptResult.voyage_duration_hours} hrs
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  Variance vs ETA: {speedOptResult.arrival_variance_hours > 0 ? `+${speedOptResult.arrival_variance_hours}h (late)` : `${speedOptResult.arrival_variance_hours}h (early)`}
                </div>
              </div>

              <div>
                <span className="text-xs text-slate-400 font-medium">Fuel Consumed</span>
                <div className="mt-1 font-mono text-2xl font-bold text-emerald-400">
                  {speedOptResult.fuel_consumption_tonnes} t
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  Fuel Cost: ${speedOptResult.fuel_cost_usd?.toLocaleString()}
                </div>
              </div>

              <div>
                <span className="text-xs text-slate-400 font-medium">Total Optimized Cost</span>
                <div className="mt-1 font-mono text-2xl font-bold text-slate-200">
                  ${speedOptResult.total_voyage_cost_usd?.toLocaleString()}
                </div>
                <div className="text-[11px] text-teal-400 mt-0.5">
                  Cost Minimum Solution
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: IMO CII & EU ETS Regulatory Calculator */}
      {activeTab === 'compliance' && (
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-white">IMO CII Rating & EU ETS Compliance Estimator</h2>
            <p className="text-xs text-slate-400">
              Operational Carbon Intensity Indicator (MEPC.354(78)) and FuelEU Maritime penalty balance
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Vessel Segment</label>
              <select
                value={compCat}
                onChange={(e) => setCompCat(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value="container">Container Ship</option>
                <option value="bulk">Bulk Carrier</option>
                <option value="tanker">Tanker</option>
                <option value="roro">Ro-Ro Vehicle Carrier</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Capacity (TEU or DWT)</label>
              <input
                type="number"
                value={compCap}
                onChange={(e) => setCompCap(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Annual Fuel (tonnes)</label>
              <input
                type="number"
                value={compFuel}
                onChange={(e) => setCompFuel(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Annual Distance (nm)</label>
              <input
                type="number"
                value={compDist}
                onChange={(e) => setCompDist(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <button
            onClick={handleCalcCompliance}
            disabled={calculatingComp}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Calculator className={`w-3.5 h-3.5 ${calculatingComp ? 'animate-spin' : ''}`} />
            <span>Evaluate Regulatory Standing</span>
          </button>

          {compResult && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* CII Rating Card */}
              <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Attained IMO CII Rating (2026)</h3>
                  <span
                    className="text-lg font-bold px-3 py-1 rounded-md"
                    style={{ backgroundColor: `${compResult.cii_evaluation.rating_color}20`, color: compResult.cii_evaluation.rating_color }}
                  >
                    Rating {compResult.cii_evaluation.rating}
                  </span>
                </div>
                <div className="text-xs text-slate-400">
                  Status: <span className="font-semibold text-slate-200">{compResult.cii_evaluation.rating_status}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800 font-mono">
                  <div>Attained CII: <span className="text-teal-300">{compResult.cii_evaluation.attained_cii} g/t-nm</span></div>
                  <div>Required CII: <span className="text-slate-300">{compResult.cii_evaluation.required_cii} g/t-nm</span></div>
                  <div>CII Ratio: <span className="text-emerald-400">{compResult.cii_evaluation.cii_ratio}</span></div>
                  <div>Target Year: <span className="text-slate-400">2026 (-11% Z)</span></div>
                </div>
              </div>

              {/* EU ETS / FuelEU Card */}
              <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                <h3 className="text-sm font-semibold text-white">EU ETS & FuelEU Maritime Cost Liabilities</h3>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>ETS Scope CO2: <span className="text-slate-200">{compResult.eu_regulatory_impact.applicable_ets_co2_tonnes?.toLocaleString()} t</span></div>
                  <div>ETS Carbon Liability: <span className="text-amber-400 font-semibold">${compResult.eu_regulatory_impact.estimated_ets_cost_usd?.toLocaleString()}</span></div>
                  <div>GHG Intensity: <span className="text-slate-200">{compResult.eu_regulatory_impact.actual_ghg_intensity_g_per_mj} g/MJ</span></div>
                  <div>FuelEU Status: <span className={compResult.eu_regulatory_impact.fueleu_compliant ? 'text-emerald-400' : 'text-red-400'}>
                    {compResult.eu_regulatory_impact.fueleu_compliant ? 'Compliant' : 'Deficit Penalty'}
                  </span></div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
                  Estimated Total Annual Regulatory Cost: <span className="font-bold text-white">${compResult.eu_regulatory_impact.estimated_ets_cost_usd?.toLocaleString()}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
