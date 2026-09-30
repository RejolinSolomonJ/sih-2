"""
Unit tests for multi-objective optimization algorithms, Pareto sorting,
Hypervolume, TOPSIS, and constraint handling.
"""

import numpy as np
import pytest
from backend.app.optimization.metrics import (
    dominates,
    fast_non_dominated_sort,
    calculate_hypervolume_2d,
    calculate_crowding_distance,
    calculate_spread,
)
from backend.app.optimization.topsis import rank_pareto_front_topsis
from backend.app.optimization.problem import FleetOptimizationProblem
from backend.app.optimization.qiea import QIEANSGAOptimizer


def test_pareto_dominance():
    # Minimization
    sol_a = np.array([10.0, 20.0, 30.0])
    sol_b = np.array([12.0, 25.0, 35.0])
    sol_c = np.array([10.0, 20.0, 30.0])
    sol_d = np.array([8.0, 22.0, 30.0])

    assert dominates(sol_a, sol_b) is True
    assert dominates(sol_b, sol_a) is False
    assert dominates(sol_a, sol_c) is False  # identical is not strictly better in at least one
    assert dominates(sol_d, sol_a) is False  # incomparable
    assert dominates(sol_a, sol_d) is False


def test_fast_non_dominated_sort():
    objs = np.array([
        [1.0, 9.0], # A (non-dominated)
        [2.0, 7.0], # B (non-dominated)
        [3.0, 4.0], # C (non-dominated)
        [4.0, 8.0], # D (dominated by C and B)
        [5.0, 5.0], # E (dominated by C)
    ])
    fronts = fast_non_dominated_sort(objs)
    assert len(fronts) >= 2
    assert set(fronts[0]) == {0, 1, 2}
    assert 3 in fronts[1] or 4 in fronts[1]


def test_hypervolume_2d():
    front = np.array([
        [2.0, 8.0],
        [4.0, 5.0],
        [7.0, 3.0],
    ])
    ref_point = np.array([10.0, 10.0])
    hv = calculate_hypervolume_2d(front, ref_point)
    assert hv > 0.0
    # True theoretical 2D volume union calculation:
    # From y=10 down to 8: height 2, width (10 - 2) = 16
    # From y=8 down to 5: height 3, width (10 - 4) = 18
    # From y=5 down to 3: height 2, width (10 - 7) = 6
    # Total = 16 + 18 + 6 = 40.0
    assert pytest.approx(hv, abs=1e-3) == 40.0


def test_topsis_ranking():
    objs = np.array([
        [100.0, 500.0, 300.0],
        [200.0, 400.0, 250.0],
        [150.0, 450.0, 280.0],
    ])
    best_idx, closeness, rankings = rank_pareto_front_topsis(objs, weights=[0.33, 0.34, 0.33])
    assert 0 <= best_idx < len(objs)
    assert len(closeness) == len(objs)
    assert np.all(closeness >= 0.0) and np.all(closeness <= 1.0)


def test_constraint_repair_and_evaluation():
    vessels = [{
        "id": "container_feeder",
        "name": "Container Feeder",
        "capacity": 1800,
        "lightship_tonnes": 8500,
        "deadweight_dwt": 22000,
        "displacement_tonnes": 30500,
        "design_speed_knots": 17.5,
        "min_speed_knots": 10.0,
        "max_speed_knots": 20.0,
        "engine_mcr_kw": 12500,
        "aux_engine_kw": 1800,
        "base_sfoc_g_per_kwh": 178.0,
        "compatible_fuels": ["hfo", "mgo"],
        "capex_usd": 35000000,
        "opex_usd_per_day": 6200,
        "shore_power_equipped": False,
    }]
    fuels = [
        {"id": "hfo", "name": "HFO", "lcv_mj_per_kg": 40.2, "cost_per_tonne_usd": 580.0, "emission_factor_wtw": 3.664, "emission_factor_ttw": 3.114, "emission_factor_wtt": 0.55},
        {"id": "ammonia_green", "name": "Ammonia", "lcv_mj_per_kg": 18.6, "cost_per_tonne_usd": 890.0, "emission_factor_wtw": 0.22, "emission_factor_ttw": 0.0, "emission_factor_wtt": 0.22}
    ]
    routes = [{
        "id": "r1",
        "name": "Short Feeder",
        "distance_nm": 600,
        "demand_per_quarter": 12000,
        "service_window_days": 10,
        "port_time_days": 1.5,
        "shore_power_origin": False,
        "shore_power_dest": False,
    }]

    problem = FleetOptimizationProblem(routes=routes, vessels=vessels, fuels=fuels, use_surrogate=False)
    
    # Candidate tries to pick ammonia (index 1) which is INCOMPATIBLE with feeder, and shore power (1) which is unavailable
    x = np.array([0.0, 2.0, 0.85, 14.0, 1.0, 1.0])
    plan = problem.decode_and_repair(x)

    # Must repair to compatible fuel "hfo"
    assert plan[0]["fuel_id"] == "hfo"
    # Must repair shore power to 0
    assert plan[0]["shore_power_use"] == 0

    objs, meta = problem.evaluate(x)
    assert len(objs) == 3
    assert objs[0] > 0
    assert objs[1] > 0
    assert objs[2] > 0


def test_qiea_nsga_smoke():
    """Smoke test ensuring QIEA-NSGA executes full optimization iterations cleanly."""
    vessels = [{
        "id": "feeder",
        "name": "Feeder",
        "capacity": 1500,
        "lightship_tonnes": 8000,
        "deadweight_dwt": 20000,
        "displacement_tonnes": 28000,
        "design_speed_knots": 16.0,
        "min_speed_knots": 10.0,
        "max_speed_knots": 18.0,
        "engine_mcr_kw": 10000,
        "aux_engine_kw": 1500,
        "base_sfoc_g_per_kwh": 175.0,
        "compatible_fuels": ["hfo"],
        "capex_usd": 30000000,
        "opex_usd_per_day": 5000,
        "shore_power_equipped": True,
    }]
    fuels = [{"id": "hfo", "name": "HFO", "lcv_mj_per_kg": 40.2, "cost_per_tonne_usd": 580.0, "emission_factor_wtw": 3.664, "emission_factor_ttw": 3.114, "emission_factor_wtt": 0.55}]
    routes = [{
        "id": "r1",
        "name": "Route A",
        "distance_nm": 400,
        "demand_per_quarter": 8000,
        "service_window_days": 7,
        "port_time_days": 1.0,
        "shore_power_origin": True,
        "shore_power_dest": True,
    }]

    prob = FleetOptimizationProblem(routes=routes, vessels=vessels, fuels=fuels, use_surrogate=False)
    opt = QIEANSGAOptimizer(problem=prob, pop_size=6, max_generations=2, seed=42)
    res = opt.optimize()

    assert res["algorithm"] == "QIEA-NSGA"
    assert len(res["pareto_solutions"]) > 0
    assert len(res["convergence_history"]) == 2
