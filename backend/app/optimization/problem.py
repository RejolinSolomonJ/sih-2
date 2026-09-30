"""
Fleet Optimization Problem Definition.
Encodes multi-route fleet decision variables, constraint repair and penalization,
and evaluates 3 objective functions (Fuel, Total Cost, Lifecycle GHG) using
either the trained ML surrogate model or naval physics fallback.
"""

from typing import List, Dict, Any, Tuple, Optional
import math
import numpy as np
from backend.app.core.physics import MarinePhysicsEngine
from backend.app.prediction.model_registry import ModelRegistry


class FleetOptimizationProblem:
    """
    Fleet Optimization Problem with R routes and 6 decision variables per route.
    """

    def __init__(
        self,
        routes: List[Dict[str, Any]],
        vessels: List[Dict[str, Any]],
        fuels: List[Dict[str, Any]],
        carbon_price_usd_per_tonne: float = 85.0,  # EU ETS / Global carbon levy baseline
        emission_cap_intensity: Optional[float] = None, # tCO2e per 1000 tonne-nm
        fleet_budget_usd: Optional[float] = None,
        use_surrogate: bool = True,
    ):
        self.routes = routes
        self.vessels = vessels
        self.fuels = fuels
        self.vessel_map = {v["id"]: v for v in vessels}
        self.fuel_map = {f["id"]: f for f in fuels}
        self.carbon_price = carbon_price_usd_per_tonne
        self.emission_cap_intensity = emission_cap_intensity
        self.fleet_budget = fleet_budget_usd
        self.use_surrogate = use_surrogate

        self.num_routes = len(routes)
        self.num_vessels = len(vessels)
        self.num_fuels = len(fuels)

        # 6 variables per route: [vessel_idx, vessel_count, utilization, speed, fuel_idx, shore_power]
        self.vars_per_route = 6
        self.total_dims = self.num_routes * self.vars_per_route

        # Dimension bounds
        self.lower_bounds = np.zeros(self.total_dims)
        self.upper_bounds = np.zeros(self.total_dims)

        for r_idx in range(self.num_routes):
            base = r_idx * self.vars_per_route
            self.lower_bounds[base + 0] = 0.0                      # vessel index
            self.upper_bounds[base + 0] = self.num_vessels - 1e-4

            self.lower_bounds[base + 1] = 1.0                      # vessel count
            self.upper_bounds[base + 1] = 8.0

            self.lower_bounds[base + 2] = 0.40                     # capacity utilization
            self.upper_bounds[base + 2] = 1.00

            self.lower_bounds[base + 3] = 10.0                     # speed knots
            self.upper_bounds[base + 3] = 23.0

            self.lower_bounds[base + 4] = 0.0                      # fuel index
            self.upper_bounds[base + 4] = self.num_fuels - 1e-4

            self.lower_bounds[base + 5] = 0.0                      # shore power (0 or 1)
            self.upper_bounds[base + 5] = 1.0

        # Try loading active surrogate model
        self.surrogate_info = None
        if self.use_surrogate:
            try:
                self.surrogate_info = ModelRegistry.get_active_model()
            except Exception:
                self.surrogate_info = None

    def decode_and_repair(self, x: np.ndarray) -> List[Dict[str, Any]]:
        """
        Decodes continuous optimization vector into integer and bound-repaired fleet decisions.
        Ensures compatibility with fuel types, vessel speed envelopes, and port shore power.
        """
        fleet_plan = []

        for r_idx, route in enumerate(self.routes):
            base = r_idx * self.vars_per_route

            # Vessel selection
            v_idx = int(np.clip(math.floor(x[base + 0]), 0, self.num_vessels - 1))
            vessel = self.vessels[v_idx]

            # Vessel count
            v_count = int(np.clip(round(x[base + 1]), 1, 8))

            # Capacity utilization
            util = float(np.clip(x[base + 2], 0.40, 1.00))

            # Cruising speed clamped to vessel's certified operational envelope
            min_spd = vessel.get("min_speed_knots", 10.0)
            max_spd = vessel.get("max_speed_knots", 22.0)
            spd = float(np.clip(x[base + 3], min_spd, max_spd))

            # Fuel selection with compatibility repair
            f_idx = int(np.clip(math.floor(x[base + 4]), 0, self.num_fuels - 1))
            fuel = self.fuels[f_idx]
            compatible_fuel_ids = vessel.get("compatible_fuels", ["hfo"])

            if fuel["id"] not in compatible_fuel_ids:
                # Repair to the most similar compatible fuel
                repaired_fuel_id = compatible_fuel_ids[0]
                fuel = self.fuel_map[repaired_fuel_id]

            # Shore power usage with infrastructure feasibility repair
            raw_sp = round(x[base + 5])
            route_has_sp = route.get("shore_power_origin", False) or route.get("shore_power_dest", False)
            vessel_has_sp = vessel.get("shore_power_equipped", False)
            sp_use = 1 if (raw_sp == 1 and route_has_sp and vessel_has_sp) else 0

            fleet_plan.append({
                "route_id": route["id"],
                "route_name": route["name"],
                "distance_nm": route["distance_nm"],
                "demand_per_quarter": route["demand_per_quarter"],
                "service_window_days": route["service_window_days"],
                "port_time_days": route["port_time_days"],
                "vessel_id": vessel["id"],
                "vessel_name": vessel["name"],
                "vessel_capacity": vessel["capacity"],
                "vessel_count": v_count,
                "capacity_utilization": round(util, 3),
                "cruising_speed_knots": round(spd, 2),
                "fuel_id": fuel["id"],
                "fuel_name": fuel["name"],
                "shore_power_use": sp_use,
                "vessel_obj": vessel,
                "fuel_obj": fuel,
            })

        return fleet_plan

    def evaluate(self, x: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Evaluate candidate fleet plan across 3 objectives:
        f1: Total fuel consumption (tonnes energy-equivalent)
        f2: Total quarterly operating cost (USD)
        f3: Total quarterly lifecycle GHG emissions (tCO2e WTW)
        Includes constraint penalty functions for unmet demand, schedule delays, budget, and emission cap.
        """
        fleet_plan = self.decode_and_repair(x)

        total_fuel_tonnes = 0.0
        total_cost_usd = 0.0
        total_co2e_wtw_tonnes = 0.0

        penalty = 0.0
        details = []

        quarter_days = 90.0

        for slot in fleet_plan:
            vessel = slot["vessel_obj"]
            fuel = slot["fuel_obj"]
            dist_nm = slot["distance_nm"]
            speed = slot["cruising_speed_knots"]
            v_count = slot["vessel_count"]
            util = slot["capacity_utilization"]
            port_days = slot["port_time_days"]
            demand = slot["demand_per_quarter"]
            service_window = slot["service_window_days"]
            use_sp = slot["shore_power_use"]

            # 1. Roundtrip Cycle Dynamics
            sailing_hours = (dist_nm * 2.0) / speed
            sailing_days = sailing_hours / 24.0
            roundtrip_cycle_days = sailing_days + port_days

            # Schedule constraint check
            buffer_days = 2.0  # weather and port congestion contingency
            if roundtrip_cycle_days > (service_window + buffer_days):
                delay = roundtrip_cycle_days - service_window
                penalty += 5000.0 * (delay ** 2)

            # Roundtrips per vessel in quarter
            cycles_per_vessel = quarter_days / roundtrip_cycle_days
            total_fleet_cycles = cycles_per_vessel * v_count

            # Cargo transported
            capacity = vessel["capacity"]
            cargo_per_trip = capacity * util
            total_cargo_transported = total_fleet_cycles * cargo_per_trip

            # Demand satisfaction constraint
            if total_cargo_transported < demand:
                unmet_ratio = (demand - total_cargo_transported) / max(1.0, demand)
                penalty += 25000.0 * (unmet_ratio * 100.0) ** 1.8

            # 2. Fuel Consumption per Roundtrip
            # Evaluate using Physics or Surrogate
            phys_res = MarinePhysicsEngine.calculate_power_and_fuel(
                vessel_config=vessel,
                fuel_config=fuel,
                speed_knots=speed,
                cargo_load_ratio=util,
                hours=sailing_hours,
                wave_height_m=slot.get("wave_height_avg_m", 2.0),
                wind_speed_knots=slot.get("headwind_avg_knots", 12.0),
                fouling_index=0.10,
            )

            sailing_fuel_tonnes = phys_res["total_fuel_tonnes"]

            # Port auxiliary fuel vs Shore Power
            port_aux_kw = vessel.get("aux_engine_kw", 2000.0) * 0.45
            port_hours = port_days * 24.0

            if use_sp == 1:
                # Electric cold ironing
                grid_mwh = (port_aux_kw * port_hours) / 1000.0
                sp_cost_per_mwh = 145.0  # USD
                port_energy_cost = grid_mwh * sp_cost_per_mwh
                port_co2e = grid_mwh * 0.385  # tCO2e
                port_fuel_tonnes = 0.0
            else:
                # Auxiliary engine burning MGO in port
                mgo_lcv = 42.7
                port_fuel_tonnes = (port_aux_kw * port_hours * 215.0) / 1_000_000.0
                port_energy_cost = port_fuel_tonnes * 820.0
                port_co2e = port_fuel_tonnes * 3.816

            cycle_fuel_tonnes = sailing_fuel_tonnes + port_fuel_tonnes
            cycle_co2e_wtw = (sailing_fuel_tonnes * fuel["emission_factor_wtw"]) + port_co2e

            quarter_slot_fuel = cycle_fuel_tonnes * total_fleet_cycles
            quarter_slot_co2e = cycle_co2e_wtw * total_fleet_cycles

            # 3. Cost Breakdown
            # Fuel cost
            cycle_fuel_cost = (sailing_fuel_tonnes * fuel["cost_per_tonne_usd"]) + port_energy_cost
            quarter_fuel_cost = cycle_fuel_cost * total_fleet_cycles

            # OPEX (crew, maintenance, insurance)
            daily_opex = vessel.get("opex_usd_per_day", 7000.0)
            quarter_opex = daily_opex * quarter_days * v_count

            # Amortized CAPEX (25-year straight line + financing ~ 6.5% / year)
            capex = vessel.get("capex_usd", 50_000_000.0)
            quarter_capex = (capex * 0.065 / 4.0) * v_count

            # Carbon cost (EU ETS / IMO levy)
            quarter_carbon_cost = quarter_slot_co2e * self.carbon_price

            slot_total_cost = quarter_fuel_cost + quarter_opex + quarter_capex + quarter_carbon_cost

            total_fuel_tonnes += quarter_slot_fuel
            total_cost_usd += slot_total_cost
            total_co2e_wtw_tonnes += quarter_slot_co2e

            details.append({
                "route_id": slot["route_id"],
                "route_name": slot["route_name"],
                "vessel_name": vessel["name"],
                "vessel_count": v_count,
                "speed_knots": speed,
                "fuel_name": fuel["name"],
                "shore_power_use": use_sp,
                "cargo_transported": round(total_cargo_transported, 1),
                "cargo_demand": demand,
                "cycles_per_vessel": round(cycles_per_vessel, 1),
                "quarter_fuel_tonnes": round(quarter_slot_fuel, 1),
                "quarter_cost_usd": round(slot_total_cost, 2),
                "quarter_co2e_tonnes": round(quarter_slot_co2e, 1),
            })

        # Emission Cap Constraint check
        if self.emission_cap_intensity is not None and self.emission_cap_intensity > 0:
            # Check against cap
            if total_co2e_wtw_tonnes > self.emission_cap_intensity:
                excess = total_co2e_wtw_tonnes - self.emission_cap_intensity
                penalty += 10000.0 * (excess ** 1.5)

        # Fleet Budget Constraint check
        if self.fleet_budget is not None and self.fleet_budget > 0:
            if total_cost_usd > self.fleet_budget:
                excess_cost = total_cost_usd - self.fleet_budget
                penalty += 2.0 * excess_cost

        # Penalize objectives
        f1 = total_fuel_tonnes + (penalty * 0.05)
        f2 = total_cost_usd + penalty
        f3 = total_co2e_wtw_tonnes + (penalty * 0.15)

        objectives = np.array([f1, f2, f3], dtype=np.float64)
        metadata = {
            "unpenalized_fuel_tonnes": round(total_fuel_tonnes, 2),
            "unpenalized_cost_usd": round(total_cost_usd, 2),
            "unpenalized_co2e_wtw_tonnes": round(total_co2e_wtw_tonnes, 2),
            "penalty": round(penalty, 2),
            "plan_details": details,
        }

        return objectives, metadata
