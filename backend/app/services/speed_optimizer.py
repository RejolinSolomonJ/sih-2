"""
Single-Voyage What-If Speed Optimizer.
Calculates the optimal cruising speed minimizing total trip cost
(fuel expense + vessel operational charter rate + delay penalties)
given target arrival window / ETA deadline.
"""

from typing import Dict, Any, List
import numpy as np
from scipy.optimize import minimize_scalar
import yaml
from pathlib import Path
from backend.app.core.physics import MarinePhysicsEngine

CONFIG_DIR = Path("config")


class SpeedOptimizerService:
    @classmethod
    def optimize_voyage_speed(
        cls,
        vessel_id: str,
        fuel_id: str,
        distance_nm: float,
        target_eta_hours: float,
        fuel_price_override: float = 0.0,
        cargo_load_ratio: float = 0.85,
        wave_height_m: float = 1.8,
        wind_speed_knots: float = 12.0,
        delay_penalty_per_hour_usd: float = 1200.0,
    ) -> Dict[str, Any]:
        """
        Finds optimal speed balancing fuel consumption (∝ speed^3) against
        time-dependent OPEX charter costs and late arrival penalties.
        """
        with open(CONFIG_DIR / "vessels.yaml", "r", encoding="utf-8") as f:
            vessels = yaml.safe_load(f)["vessels"]
        with open(CONFIG_DIR / "fuels.yaml", "r", encoding="utf-8") as f:
            fuels = yaml.safe_load(f)["fuels"]

        vessel = next((v for v in vessels if v["id"] == vessel_id), vessels[0])
        fuel = next((f for f in fuels if f["id"] == fuel_id), fuels[0])
        if fuel_price_override > 0:
            fuel["cost_per_tonne_usd"] = fuel_price_override

        min_spd = vessel["min_speed_knots"]
        max_spd = vessel["max_speed_knots"]
        daily_opex = vessel["opex_usd_per_day"]
        hourly_opex = daily_opex / 24.0

        def cost_func(speed: float) -> float:
            hours = distance_nm / speed
            phys = MarinePhysicsEngine.calculate_power_and_fuel(
                vessel_config=vessel,
                fuel_config=fuel,
                speed_knots=speed,
                hours=hours,
                cargo_load_ratio=cargo_load_ratio,
                wave_height_m=wave_height_m,
                wind_speed_knots=wind_speed_knots,
            )
            fuel_cost = phys["fuel_cost_usd"]
            charter_cost = hours * hourly_opex
            
            # Late arrival penalty
            delay_penalty = 0.0
            if hours > target_eta_hours:
                lateness = hours - target_eta_hours
                delay_penalty = lateness * delay_penalty_per_hour_usd

            return fuel_cost + charter_cost + delay_penalty

        res = minimize_scalar(cost_func, bounds=(min_spd, max_spd), method="bounded")
        optimal_speed = float(res.x)

        # Full physics at optimal speed
        opt_hours = distance_nm / optimal_speed
        opt_phys = MarinePhysicsEngine.calculate_power_and_fuel(
            vessel_config=vessel,
            fuel_config=fuel,
            speed_knots=optimal_speed,
            hours=opt_hours,
            cargo_load_ratio=cargo_load_ratio,
            wave_height_m=wave_height_m,
            wind_speed_knots=wind_speed_knots,
        )

        # Generate cost-vs-speed curve for plotting
        curve_speeds = np.linspace(min_spd, max_spd, 15)
        curve = []
        for spd in curve_speeds:
            hrs = distance_nm / spd
            p = MarinePhysicsEngine.calculate_power_and_fuel(
                vessel_config=vessel,
                fuel_config=fuel,
                speed_knots=float(spd),
                hours=hrs,
                cargo_load_ratio=cargo_load_ratio,
                wave_height_m=wave_height_m,
                wind_speed_knots=wind_speed_knots,
            )
            f_cost = p["fuel_cost_usd"]
            c_cost = hrs * hourly_opex
            lat = max(0.0, hrs - target_eta_hours)
            d_pen = lat * delay_penalty_per_hour_usd
            curve.append({
                "speed_knots": round(float(spd), 1),
                "voyage_hours": round(hrs, 1),
                "fuel_cost_usd": round(f_cost, 2),
                "time_cost_usd": round(c_cost, 2),
                "delay_penalty_usd": round(d_pen, 2),
                "total_cost_usd": round(f_cost + c_cost + d_pen, 2),
                "fuel_consumption_tonnes": round(p["total_fuel_tonnes"], 2),
                "co2e_wtw_tonnes": round(p["co2e_wtw_tonnes"], 2),
            })

        return {
            "optimal_speed_knots": round(optimal_speed, 2),
            "voyage_duration_hours": round(opt_hours, 1),
            "arrival_variance_hours": round(opt_hours - target_eta_hours, 1),
            "fuel_consumption_tonnes": round(opt_phys["total_fuel_tonnes"], 2),
            "fuel_cost_usd": round(opt_phys["fuel_cost_usd"], 2),
            "total_voyage_cost_usd": round(float(res.fun), 2),
            "co2e_wtw_tonnes": round(opt_phys["co2e_wtw_tonnes"], 2),
            "engine_load_pct": round(opt_phys["engine_load_fraction"] * 100.0, 1),
            "sensitivity_curve": curve,
        }
