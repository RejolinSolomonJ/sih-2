"""
API Smoke Tests for GreenFleet Q endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_and_health():
    res = client.get("/")
    assert res.status_code == 200
    assert "GreenFleet Q" in res.json()["service"]

    res_h = client.get("/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "HEALTHY"


def test_config_endpoints():
    res_fuels = client.get("/api/v1/config/fuels")
    assert res_fuels.status_code == 200
    assert len(res_fuels.json()["fuels"]) >= 5

    res_vessels = client.get("/api/v1/config/vessels")
    assert res_vessels.status_code == 200
    assert len(res_vessels.json()["vessels"]) >= 5

    res_routes = client.get("/api/v1/config/routes")
    assert res_routes.status_code == 200
    assert len(res_routes.json()["routes"]) >= 3


def test_data_summary():
    res = client.get("/api/v1/data/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_loaded"] is True
    assert data["total_rows"] >= 5000


def test_prediction_endpoint():
    payload = {
        "vessel_id": "panamax_container",
        "fuel_id": "hfo",
        "speed_knots": 18.0,
        "cargo_load_ratio": 0.85,
        "wave_height_m": 2.0,
        "wind_speed_knots": 12.0,
        "distance_nm": 600.0,
    }
    res = client.post("/api/v1/models/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["predicted_fuel_tonnes"] > 0
    assert data["ci_lower"] <= data["predicted_fuel_tonnes"] <= data["ci_upper"]
    assert len(data["feature_attributions"]) > 0


def test_scenario_fuel_pathways():
    res = client.get("/api/v1/scenarios/fuel-pathways")
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) >= 5


def test_tools_speed_optimizer():
    payload = {
        "vessel_id": "panamax_container",
        "fuel_id": "hfo",
        "distance_nm": 1200.0,
        "target_eta_hours": 72.0,
    }
    res = client.post("/api/v1/tools/speed-optimizer", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["optimal_speed_knots"] > 0
    assert len(data["sensitivity_curve"]) > 5


def test_tools_compliance():
    res = client.get("/api/v1/tools/compliance?vessel_category=container&capacity=5200&annual_fuel_tonnes=18500&annual_distance_nm=85000")
    assert res.status_code == 200
    data = res.json()
    assert data["cii_evaluation"]["rating"] in ["A", "B", "C", "D", "E"]
    assert data["eu_regulatory_impact"]["estimated_ets_cost_usd"] > 0
