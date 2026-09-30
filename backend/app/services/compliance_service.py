"""
Regulatory Compliance Analysis Service.
Calculates IMO Carbon Intensity Indicator (CII) Rating (A-E)
and EU ETS / FuelEU Maritime compliance cost indicators.
Clearly labeled as parameterized regulatory estimates.
"""

from typing import Dict, Any, Optional
import math


class ComplianceService:
    """
    IMO MEPC.354(78) operational Carbon Intensity Indicator (CII)
    and EU ETS / FuelEU maritime emissions accounting.
    """

    DISCLAIMER = "Configurable regulatory estimates based on IMO MEPC.354(78) and EU Regulation 2023/1805."

    @classmethod
    def calculate_cii_rating(
        cls,
        vessel_category: str,
        capacity_dwt_or_teu: float,
        annual_fuel_tonnes: float,
        annual_distance_nm: float,
        fuel_cf: float = 3.114,  # tCO2 / tFuel for HFO
        year: int = 2026,
    ) -> Dict[str, Any]:
        """
        Calculates attained CII in grams CO2 / (tonne * nautical mile)
        and assigns rating [A, B, C, D, E].
        """
        # Baseline reference line coefficients (IMO MEPC.337(76))
        # CII_ref = a * Capacity^(-c)
        cat = vessel_category.lower()
        if "container" in cat:
            a, c = 1984.0, 0.489
            # Boundaries: d1=0.83, d2=0.94, d3=1.06, d4=1.19
            d = (0.83, 0.94, 1.06, 1.19)
        elif "bulk" in cat:
            a, c = 4745.0, 0.622
            d = (0.86, 0.94, 1.06, 1.18)
        elif "tanker" in cat:
            a, c = 5247.0, 0.610
            d = (0.82, 0.93, 1.08, 1.25)
        else: # Ro-Ro / Ferry
            a, c = 2149.0, 0.428
            d = (0.80, 0.92, 1.08, 1.22)

        cii_ref = a * (capacity_dwt_or_teu ** (-c))

        # Yearly reduction factor Z (2023=5%, 2024=7%, 2025=9%, 2026=11%, 2027=15%)
        z_dict = {2023: 5.0, 2024: 7.0, 2025: 9.0, 2026: 11.0, 2027: 15.0}
        z = z_dict.get(year, 11.0)
        cii_required = cii_ref * (1.0 - z / 100.0)

        # Attained CII = (Total CO2 in grams) / (Capacity * Distance)
        total_co2_grams = annual_fuel_tonnes * fuel_cf * 1_000_000.0
        transport_work = max(1.0, capacity_dwt_or_teu * annual_distance_nm)
        attained_cii = total_co2_grams / transport_work

        # Rating determination
        ratio = attained_cii / max(1e-4, cii_required)
        if ratio <= d[0]:
            rating = "A"
            status = "Major Superior"
            color = "#10b981" # Green
        elif ratio <= d[1]:
            rating = "B"
            status = "Minor Superior"
            color = "#34d399"
        elif ratio <= d[2]:
            rating = "C"
            status = "Moderate / Compliant"
            color = "#facc15" # Yellow
        elif ratio <= d[3]:
            rating = "D"
            status = "Minor Inferior (Corrective Action Required if 3 yrs)"
            color = "#fb923c" # Orange
        else:
            rating = "E"
            status = "Inferior (Immediate Corrective Action Plan Required)"
            color = "#ef4444" # Red

        return {
            "disclaimer": cls.DISCLAIMER,
            "year": year,
            "attained_cii": round(attained_cii, 2),
            "required_cii": round(cii_required, 2),
            "reference_cii": round(cii_ref, 2),
            "cii_ratio": round(ratio, 3),
            "rating": rating,
            "rating_status": status,
            "rating_color": color,
            "boundaries": {
                "superior_A": round(d[0] * cii_required, 2),
                "lower_B": round(d[1] * cii_required, 2),
                "upper_C": round(d[2] * cii_required, 2),
                "inferior_D": round(d[3] * cii_required, 2),
            },
        }

    @classmethod
    def calculate_eu_ets_and_fueleu(
        cls,
        annual_fuel_tonnes: float,
        emission_factor_ttw: float = 3.114,
        emission_factor_wtw: float = 3.664,
        fuel_lcv_mj_per_kg: float = 40.2,
        ets_carbon_price_eur: float = 80.0,
        eu_voyage_share_pct: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Calculates:
        1. EU ETS liability: Scope is 100% of emissions between EU ports, 50% of voyages into/out of EU.
        2. FuelEU Maritime GHG intensity compliance balance (Reference: 91.16 gCO2e/MJ).
        """
        # Scope CO2 emissions
        co2_tonnes = annual_fuel_tonnes * emission_factor_ttw
        applicable_ets_tonnes = co2_tonnes * (eu_voyage_share_pct / 100.0)
        ets_cost_eur = applicable_ets_tonnes * ets_carbon_price_eur

        # FuelEU Maritime Target (2% reduction below 91.16 in 2025-2029 => 89.34 gCO2e/MJ)
        energy_mj = annual_fuel_tonnes * 1000.0 * fuel_lcv_mj_per_kg
        actual_intensity_g_per_mj = (annual_fuel_tonnes * emission_factor_wtw * 1_000_000.0) / max(1.0, energy_mj)
        target_intensity_g_per_mj = 89.34

        intensity_deficit = max(0.0, actual_intensity_g_per_mj - target_intensity_g_per_mj)
        # FuelEU penalty is approx 2400 EUR per tonne VLSFO equivalent energy deficit
        # 1 tonne VLSFO ~ 41,000 MJ
        energy_deficit_tonnes = (intensity_deficit * energy_mj / 1_000_000.0) / 3.114
        fueleu_penalty_eur = energy_deficit_tonnes * 2400.0

        return {
            "disclaimer": cls.DISCLAIMER,
            "applicable_ets_co2_tonnes": round(applicable_ets_tonnes, 1),
            "estimated_ets_cost_eur": round(ets_cost_eur, 2),
            "estimated_ets_cost_usd": round(ets_cost_eur * 1.08, 2),
            "actual_ghg_intensity_g_per_mj": round(actual_intensity_g_per_mj, 2),
            "target_ghg_intensity_g_per_mj": target_intensity_g_per_mj,
            "fueleu_compliant": intensity_deficit == 0.0,
            "estimated_fueleu_penalty_eur": round(fueleu_penalty_eur, 2),
            "total_regulatory_cost_eur": round(ets_cost_eur + fueleu_penalty_eur, 2),
        }
