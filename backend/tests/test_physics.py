"""
Unit tests for MarinePhysicsEngine and Admiralty scaling law.
"""

import pytest
from backend.app.core.physics import MarinePhysicsEngine


@pytest.fixture
def sample_vessel():
    return {
        "id": "panamax_container",
        "name": "Panamax Container",
        "design_speed_knots": 21.0,
        "min_speed_knots": 11.0,
        "max_speed_knots": 23.5,
        "lightship_tonnes": 21000,
        "deadweight_dwt": 65000,
        "displacement_tonnes": 86000,
        "design_draft_m": 13.5,
        "beam_m": 32.3,
        "length_m": 294.0,
        "engine_mcr_kw": 38000,
        "aux_engine_kw": 3500,
        "base_sfoc_g_per_kwh": 172.0,
    }


@pytest.fixture
def sample_fuel():
    return {
        "id": "hfo",
        "name": "Heavy Fuel Oil",
        "lcv_mj_per_kg": 40.2,
        "cost_per_tonne_usd": 580.0,
        "emission_factor_wtw": 3.664,
        "emission_factor_ttw": 3.114,
        "emission_factor_wtt": 0.550,
    }


def test_admiralty_cubic_speed_law(sample_vessel, sample_fuel):
    """Verify that power and fuel consumption scale approximately with speed^3 (cubic law)."""
    p1 = MarinePhysicsEngine.calculate_power_and_fuel(
        sample_vessel, sample_fuel, speed_knots=14.0, hours=24.0, wave_height_m=0.0, wind_speed_knots=0.0, fouling_index=0.0
    )
    p2 = MarinePhysicsEngine.calculate_power_and_fuel(
        sample_vessel, sample_fuel, speed_knots=18.0, hours=24.0, wave_height_m=0.0, wind_speed_knots=0.0, fouling_index=0.0
    )

    ratio_speed = 18.0 / 14.0
    ratio_power = p2["propulsion_power_kw"] / p1["propulsion_power_kw"]
    
    # Power ratio should be roughly ~ (18/14)^3 = 2.12 (between 1.9 and 2.5)
    assert 1.8 < ratio_power < 2.6
    assert p2["total_fuel_tonnes"] > p1["total_fuel_tonnes"]


def test_weather_added_resistance(sample_vessel, sample_fuel):
    """Verify adverse sea states (wave, wind) increase power demand."""
    calm = MarinePhysicsEngine.calculate_power_and_fuel(
        sample_vessel, sample_fuel, speed_knots=16.0, hours=24.0, wave_height_m=0.0, wind_speed_knots=0.0, fouling_index=0.0
    )
    rough = MarinePhysicsEngine.calculate_power_and_fuel(
        sample_vessel, sample_fuel, speed_knots=16.0, hours=24.0, wave_height_m=4.5, wind_speed_knots=30.0, fouling_index=0.0
    )

    assert rough["propulsion_power_kw"] > calm["propulsion_power_kw"]
    assert rough["added_resistance_wave_kw"] > 0
    assert rough["added_resistance_wind_kw"] > 0


def test_fouling_penalty(sample_vessel, sample_fuel):
    """Verify biofouling penalty increases fuel rate."""
    clean = MarinePhysicsEngine.calculate_power_and_fuel(
        sample_vessel, sample_fuel, speed_knots=16.0, fouling_index=0.0
    )
    fouled = MarinePhysicsEngine.calculate_power_and_fuel(
        sample_vessel, sample_fuel, speed_knots=16.0, fouling_index=0.8
    )

    assert fouled["total_fuel_tonnes"] > clean["total_fuel_tonnes"]
    assert fouled["added_resistance_fouling_kw"] > 0
