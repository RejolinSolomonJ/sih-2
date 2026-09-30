"""
GreenFleet Q - Naval Architecture Physics Baseline & Admiralty Law Engine
Calculates accurate hydrodynamic resistance, engine load, SFOC, and fuel consumption
under variable drafts, weather conditions, hull fouling, and fuel types.
"""

from typing import Dict, Any, Optional
import math
import numpy as np


class MarinePhysicsEngine:
    """
    Empirical and semi-analytical marine propulsion model combining:
    - Admiralty coefficient power scaling (P ~ Displacement^(2/3) * Speed^3)
    - ISO 15016 / ITTC weather added resistance (wave height, relative wind speed)
    - Townsin & Kwon biofouling hydrodynamic roughness degradation
    - Non-linear engine load SFOC thermal efficiency curve (optimal at 70-85% MCR)
    - Lower Calorific Value (LCV) energy-density fuel equivalence
    """

    # Reference constants
    RHO_SEAWATER = 1025.0  # kg/m^3
    RHO_AIR = 1.225        # kg/m^3
    G_ACCEL = 9.80665      # m/s^2
    HFO_REF_LCV = 40.2     # MJ/kg baseline reference for SFOC

    @staticmethod
    def knots_to_mps(knots: float) -> float:
        """Convert nautical knots to meters per second."""
        return knots * 0.514444

    @staticmethod
    def mps_to_knots(mps: float) -> float:
        """Convert meters per second to knots."""
        return mps / 0.514444

    @classmethod
    def calculate_power_and_fuel(
        cls,
        vessel_config: Dict[str, Any],
        fuel_config: Dict[str, Any],
        speed_knots: float,
        draft_m: Optional[float] = None,
        cargo_load_ratio: float = 0.85,
        wave_height_m: float = 1.5,
        wind_speed_knots: float = 10.0,
        wind_direction_deg: float = 0.0,  # 0 deg = headwind, 180 deg = tailwind
        current_knots: float = 0.0,       # positive = following current, negative = counter current
        fouling_index: float = 0.05,       # 0.0 = newly painted/cleaned hull, 1.0 = heavy barnacle macro-fouling
        hours: float = 24.0,              # duration
        distance_nm: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate total propulsion power, engine load fraction, and fuel consumption.
        """
        # Clamp inputs to safe boundaries
        speed_knots = max(4.0, min(speed_knots, vessel_config.get("max_speed_knots", 25.0)))
        cargo_load_ratio = max(0.0, min(1.0, cargo_load_ratio))
        wave_height_m = max(0.0, wave_height_m)
        wind_speed_knots = max(0.0, wind_speed_knots)
        fouling_index = max(0.0, min(1.0, fouling_index))

        # Speed through water (STW) adjusted for current
        speed_stw_knots = max(1.0, speed_knots - current_knots)
        speed_stw_mps = cls.knots_to_mps(speed_stw_knots)

        # Displacement calculation based on lightship and deadweight cargo ratio
        lightship = vessel_config.get("lightship_tonnes", 15000.0)
        deadweight = vessel_config.get("deadweight_dwt", 40000.0)
        actual_displacement = lightship + (cargo_load_ratio * deadweight)

        design_displacement = vessel_config.get(
            "displacement_tonnes", lightship + deadweight
        )
        design_speed = vessel_config.get("design_speed_knots", 18.0)
        mcr_kw = vessel_config.get("engine_mcr_kw", 15000.0)
        aux_kw = vessel_config.get("aux_engine_kw", 2000.0)
        base_sfoc = vessel_config.get("base_sfoc_g_per_kwh", 175.0)

        # 1. Admiralty Calm Water Power
        # P_calm = P_design * (Disp / Disp_design)^(2/3) * (V / V_design)^3.15
        disp_ratio = actual_displacement / max(100.0, design_displacement)
        speed_ratio = speed_stw_knots / max(1.0, design_speed)

        # Exponent ~3.1 to 3.3 for displacement hulls
        power_exponent = 3.12
        p_calm_kw = (
            (0.85 * mcr_kw)
            * (disp_ratio ** (2.0 / 3.0))
            * (speed_ratio ** power_exponent)
        )

        # 2. Weather Added Resistance
        # 2a. Wind resistance (headwind component)
        wind_angle_rad = math.radians(wind_direction_deg)
        headwind_comp_knots = wind_speed_knots * math.cos(wind_angle_rad)
        apparent_wind_mps = cls.knots_to_mps(max(0.0, speed_stw_knots + headwind_comp_knots))
        
        beam_m = vessel_config.get("beam_m", 30.0)
        length_m = vessel_config.get("length_m", 200.0)
        transverse_area = beam_m * (12.0 + 8.0 * (1.0 - cargo_load_ratio)) # Windage area
        c_wind = 0.78  # Aerodynamic drag coefficient
        wind_drag_n = 0.5 * cls.RHO_AIR * c_wind * transverse_area * (apparent_wind_mps ** 2)
        p_wind_kw = (wind_drag_n * speed_stw_mps) / 1000.0

        # 2b. Wave resistance (Townsin-Kwon empirical reflection & motion)
        c_wave = 1.35
        wave_drag_n = (
            0.5
            * c_wave
            * cls.RHO_SEAWATER
            * cls.G_ACCEL
            * (wave_height_m ** 2)
            * (beam_m ** 2)
            / length_m
        )
        p_wave_kw = (wave_drag_n * speed_stw_mps) / 1000.0

        # 3. Hull Fouling Penalty (up to 30% resistance increase for severe fouling)
        p_fouling_kw = p_calm_kw * (0.28 * fouling_index)

        # Total Propulsion Power Required at Propeller shaft
        propulsive_efficiency = 0.68
        p_propulsion_kw = (p_calm_kw + p_wind_kw + p_wave_kw + p_fouling_kw) / propulsive_efficiency
        
        # Engine load fraction (Main Engine)
        engine_load = p_propulsion_kw / max(1.0, mcr_kw)
        engine_load_clamped = max(0.15, min(1.05, engine_load))

        # 4. Engine Thermal Efficiency & SFOC curve
        # Lowest SFOC typically at 75-80% load. Penalty rises sharply below 40% and above 95%
        sfoc_factor = 1.0 + 0.38 * ((engine_load_clamped - 0.78) ** 2)
        if engine_load_clamped < 0.40:
            sfoc_factor += 0.15 * ((0.40 - engine_load_clamped) / 0.40)
        
        actual_main_sfoc = base_sfoc * sfoc_factor  # g/kWh for reference HFO

        # 5. Alternative Fuel Energy Equivalent Scaling
        # Fuel consumption in grams = Power (kW) * Time (h) * SFOC * (LCV_HFO / LCV_fuel)
        fuel_lcv = fuel_config.get("lcv_mj_per_kg", cls.HFO_REF_LCV)
        lcv_ratio = cls.HFO_REF_LCV / max(5.0, fuel_lcv)

        # Effective duration
        if distance_nm is not None and distance_nm > 0 and speed_knots > 0:
            actual_hours = distance_nm / speed_knots
        else:
            actual_hours = hours

        # Main Engine fuel mass (tonnes)
        main_fuel_tonnes = (
            p_propulsion_kw
            * actual_hours
            * actual_main_sfoc
            * lcv_ratio
            / 1_000_000.0
        )

        # Auxiliary Engine fuel mass (tonnes, generator for hoteling and steering)
        aux_load = 0.50
        aux_sfoc = 210.0 * lcv_ratio
        aux_fuel_tonnes = (
            aux_kw
            * aux_load
            * actual_hours
            * aux_sfoc
            / 1_000_000.0
        )

        total_fuel_tonnes = main_fuel_tonnes + aux_fuel_tonnes
        fuel_per_day_tonnes = (total_fuel_tonnes / max(0.01, actual_hours)) * 24.0

        # Lifecycle GHG (Well-to-Wake CO2e)
        wtw_factor = fuel_config.get("emission_factor_wtw", 3.664)
        ttw_factor = fuel_config.get("emission_factor_ttw", 3.114)
        wtt_factor = fuel_config.get("emission_factor_wtt", 0.550)

        total_co2e_wtw_tonnes = total_fuel_tonnes * wtw_factor
        total_co2e_ttw_tonnes = total_fuel_tonnes * ttw_factor
        total_co2e_wtt_tonnes = total_fuel_tonnes * wtt_factor

        # Fuel cost
        cost_per_tonne = fuel_config.get("cost_per_tonne_usd", 580.0)
        fuel_cost_usd = total_fuel_tonnes * cost_per_tonne

        return {
            "speed_knots": round(speed_knots, 2),
            "speed_stw_knots": round(speed_stw_knots, 2),
            "hours": round(actual_hours, 2),
            "distance_nm": round(speed_knots * actual_hours, 2) if distance_nm is None else distance_nm,
            "propulsion_power_kw": round(p_propulsion_kw, 1),
            "engine_load_fraction": round(engine_load_clamped, 4),
            "actual_sfoc_g_per_kwh": round(actual_main_sfoc, 2),
            "main_fuel_tonnes": round(main_fuel_tonnes, 4),
            "aux_fuel_tonnes": round(aux_fuel_tonnes, 4),
            "total_fuel_tonnes": round(total_fuel_tonnes, 4),
            "fuel_per_day_tonnes": round(fuel_per_day_tonnes, 3),
            "fuel_cost_usd": round(fuel_cost_usd, 2),
            "co2e_wtw_tonnes": round(total_co2e_wtw_tonnes, 4),
            "co2e_ttw_tonnes": round(total_co2e_ttw_tonnes, 4),
            "co2e_wtt_tonnes": round(total_co2e_wtt_tonnes, 4),
            "added_resistance_wind_kw": round(p_wind_kw, 1),
            "added_resistance_wave_kw": round(p_wave_kw, 1),
            "added_resistance_fouling_kw": round(p_fouling_kw, 1),
        }
