"""
GreenFleet Q - Synthetic Marine Voyage Dataset Generator
Generates realistic voyage segment records based on Admiralty hydrodynamic power law,
added sea-state resistance, hull fouling growth, and engine SFOC efficiency curves.
"""

import os
import sys
import argparse
from pathlib import Path
import yaml
import numpy as np
import pandas as pd

# Add repo root to path for backend core imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT))

from backend.app.core.physics import MarinePhysicsEngine


def load_yaml_configs():
    config_dir = REPO_ROOT / "config"
    with open(config_dir / "fuels.yaml", "r", encoding="utf-8") as f:
        fuels_data = yaml.safe_load(f)["fuels"]
    with open(config_dir / "vessels.yaml", "r", encoding="utf-8") as f:
        vessels_data = yaml.safe_load(f)["vessels"]
    
    fuels_map = {item["id"]: item for item in fuels_data}
    vessels_map = {item["id"]: item for item in vessels_data}
    return fuels_map, vessels_map


def generate_synthetic_voyages(
    n_samples: int = 50000,
    seed: int = 42,
    output_path: str = "data/voyages_50k.csv",
    noise_level: float = 0.035
) -> pd.DataFrame:
    """
    Generate n_samples synthetic voyage segment records across 6 vessel archetypes
    and 7 marine fuel varieties with realistic operational distributions.
    """
    rng = np.random.default_rng(seed)
    fuels_map, vessels_map = load_yaml_configs()
    vessel_ids = list(vessels_map.keys())

    records = []

    # Assign samples across vessel archetypes
    samples_per_vessel = n_samples // len(vessel_ids)
    remainder = n_samples % len(vessel_ids)

    print(f"Generating {n_samples} voyage segment records with seed={seed}...")

    for v_idx, v_id in enumerate(vessel_ids):
        vessel = vessels_map[v_id]
        compatible_fuels = vessel.get("compatible_fuels", ["hfo", "mgo"])
        count = samples_per_vessel + (1 if v_idx < remainder else 0)

        # Operational distributions
        min_spd = vessel["min_speed_knots"]
        max_spd = vessel["max_speed_knots"]
        design_spd = vessel["design_speed_knots"]

        # Speeds concentrated around eco-speed (design_spd * 0.85) to design speed
        speeds = rng.normal(loc=design_spd * 0.92, scale=1.8, size=count)
        speeds = np.clip(speeds, min_spd, max_spd)

        # Cargo load ratios (Beta distribution skewed towards laden 0.75-0.95 and ballast 0.3-0.4)
        is_ballast = rng.random(count) < 0.25
        cargo_loads = np.where(
            is_ballast,
            rng.uniform(0.10, 0.40, count),
            rng.beta(a=5.0, b=1.5, size=count) * 0.45 + 0.55
        )
        cargo_loads = np.clip(cargo_loads, 0.05, 1.0)

        # Sea states: Significant wave height (Rayleigh or Weibull distribution)
        wave_heights = rng.weibull(a=1.8, size=count) * 1.6  # typical 0.5 - 5.5m
        wave_heights = np.clip(wave_heights, 0.2, 8.5)

        # Wind speed (Beaufort scale aligned)
        wind_speeds = rng.weibull(a=2.0, size=count) * 14.0  # knots
        wind_speeds = np.clip(wind_speeds, 1.0, 48.0)

        # Wind direction relative to bow (-180 to +180 deg)
        wind_dirs = rng.uniform(-180.0, 180.0, count)

        # Surface ocean current (-2.5 to +2.5 knots along ship track)
        currents = rng.normal(loc=0.0, scale=0.85, size=count)
        currents = np.clip(currents, -2.5, 2.5)

        # Hull biofouling index (growth between dry-dock cycles, 0.0 = clean to 1.0 = heavy)
        # Skewed towards clean with occasional fouled voyages
        fouling_indices = rng.exponential(scale=0.22, size=count)
        fouling_indices = np.clip(fouling_indices, 0.01, 0.95)

        # Voyage segment distance (nautical miles, 100 to 1200 nm segments)
        distances = rng.uniform(120.0, 950.0, count)

        # Fuel choices based on compatibility
        fuel_choices = rng.choice(compatible_fuels, size=count)

        for i in range(count):
            f_id = fuel_choices[i]
            fuel = fuels_map[f_id]
            spd = float(speeds[i])
            c_load = float(cargo_loads[i])
            w_height = float(wave_heights[i])
            w_speed = float(wind_speeds[i])
            w_dir = float(wind_dirs[i])
            curr = float(currents[i])
            foul = float(fouling_indices[i])
            dist = float(distances[i])

            # Calculate draft from design draft and displacement ratio
            design_draft = vessel["design_draft_m"]
            lightship = vessel["lightship_tonnes"]
            dwt = vessel["deadweight_dwt"]
            disp_ratio = (lightship + c_load * dwt) / (lightship + dwt)
            actual_draft = design_draft * (0.65 + 0.35 * disp_ratio)

            # Physics evaluation
            phys = MarinePhysicsEngine.calculate_power_and_fuel(
                vessel_config=vessel,
                fuel_config=fuel,
                speed_knots=spd,
                draft_m=actual_draft,
                cargo_load_ratio=c_load,
                wave_height_m=w_height,
                wind_speed_knots=w_speed,
                wind_direction_deg=w_dir,
                current_knots=curr,
                fouling_index=foul,
                distance_nm=dist
            )

            # Add stochastic sensor / operational noise (turbulent weather, machinery fluctuations)
            noise_factor = 1.0 + rng.normal(0.0, noise_level)
            noisy_fuel_tonnes = max(0.05, phys["total_fuel_tonnes"] * noise_factor)
            noisy_power_kw = max(100.0, phys["propulsion_power_kw"] * noise_factor)
            noisy_fuel_per_day = (noisy_fuel_tonnes / max(0.1, phys["hours"])) * 24.0

            # Well-to-Wake CO2e
            co2e_wtw = noisy_fuel_tonnes * fuel["emission_factor_wtw"]

            records.append({
                "vessel_id": v_id,
                "vessel_name": vessel["name"],
                "fuel_id": f_id,
                "fuel_name": fuel["name"],
                "speed_knots": round(spd, 2),
                "speed_stw_knots": phys["speed_stw_knots"],
                "draft_m": round(actual_draft, 2),
                "cargo_load_ratio": round(c_load, 3),
                "cargo_tonnes": round(c_load * dwt, 1),
                "wave_height_m": round(w_height, 2),
                "wind_speed_knots": round(w_speed, 1),
                "wind_direction_deg": round(w_dir, 1),
                "current_knots": round(curr, 2),
                "fouling_index": round(foul, 3),
                "distance_nm": round(dist, 1),
                "voyage_duration_hours": phys["hours"],
                "propulsion_power_kw": round(noisy_power_kw, 1),
                "engine_load_fraction": phys["engine_load_fraction"],
                "sfoc_g_per_kwh": phys["actual_sfoc_g_per_kwh"],
                "fuel_consumption_tonnes": round(noisy_fuel_tonnes, 4),
                "fuel_per_day_tonnes": round(noisy_fuel_per_day, 3),
                "fuel_cost_usd": round(noisy_fuel_tonnes * fuel["cost_per_tonne_usd"], 2),
                "co2e_wtw_tonnes": round(co2e_wtw, 4),
                "added_resistance_wind_kw": phys["added_resistance_wind_kw"],
                "added_resistance_wave_kw": phys["added_resistance_wave_kw"],
                "added_resistance_fouling_kw": phys["added_resistance_fouling_kw"]
            })

    df = pd.DataFrame(records)
    # Shuffle dataframe
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    out_file = REPO_ROOT / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False)
    print(f"Successfully generated {len(df)} records and saved to {out_file}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GreenFleet Q Synthetic Data Generator")
    parser.add_argument("--samples", type=int, default=50000, help="Number of records to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="data/voyages_50k.csv", help="Output CSV path")
    args = parser.parse_args()

    generate_synthetic_voyages(n_samples=args.samples, seed=args.seed, output_path=args.output)
