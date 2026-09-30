"""
Configuration and Domain Model Endpoints:
Vessels, fuels, routes, emission factors, and defaults.
"""

from typing import Dict, Any, List
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/config", tags=["Configuration"])
CONFIG_DIR = Path("config")


@router.get("/fuels")
def get_fuels() -> Dict[str, Any]:
    with open(CONFIG_DIR / "fuels.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@router.get("/vessels")
def get_vessels() -> Dict[str, Any]:
    with open(CONFIG_DIR / "vessels.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@router.get("/routes")
def get_routes() -> Dict[str, Any]:
    with open(CONFIG_DIR / "routes.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@router.get("/defaults")
def get_defaults() -> Dict[str, Any]:
    return {
        "carbon_price_usd_per_tonne": 85.0,
        "service_year": 2026,
        "default_algorithm": "QIEA-NSGA",
        "default_population": 24,
        "default_generations": 25,
        "topsis_weights": [0.33, 0.34, 0.33],
        "cii_reduction_pct_2026": 11.0,
    }
