"""
Specialized Maritime Tools API:
1. What-If Single Voyage Speed Optimizer
2. Regulatory Compliance Panel (IMO CII Rating & EU ETS / FuelEU Maritime Costs)
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from backend.app.services.speed_optimizer import SpeedOptimizerService
from backend.app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/tools", tags=["Maritime Tools"])


class SpeedOptimizeRequest(BaseModel):
    vessel_id: str = "panamax_container"
    fuel_id: str = "hfo"
    distance_nm: float = 4500.0
    target_eta_hours: float = 240.0
    fuel_price_override: float = 0.0
    cargo_load_ratio: float = 0.85
    wave_height_m: float = 1.8
    wind_speed_knots: float = 12.0
    delay_penalty_per_hour_usd: float = 1200.0


@router.post("/speed-optimizer")
def optimize_voyage_speed(req: SpeedOptimizeRequest) -> Dict[str, Any]:
    """Calculate optimal voyage speed given target ETA window and fuel/charter costs."""
    return SpeedOptimizerService.optimize_voyage_speed(
        vessel_id=req.vessel_id,
        fuel_id=req.fuel_id,
        distance_nm=req.distance_nm,
        target_eta_hours=req.target_eta_hours,
        fuel_price_override=req.fuel_price_override,
        cargo_load_ratio=req.cargo_load_ratio,
        wave_height_m=req.wave_height_m,
        wind_speed_knots=req.wind_speed_knots,
        delay_penalty_per_hour_usd=req.delay_penalty_per_hour_usd,
    )


@router.get("/compliance")
def get_compliance_estimates(
    vessel_category: str = Query("container"),
    capacity: float = Query(5200.0, description="TEU or DWT"),
    annual_fuel_tonnes: float = Query(18500.0),
    annual_distance_nm: float = Query(85000.0),
    carbon_price_eur: float = Query(80.0),
    year: int = Query(2026),
) -> Dict[str, Any]:
    """Calculate IMO CII Rating (A-E) and EU ETS / FuelEU Maritime compliance indicators."""
    cii_res = ComplianceService.calculate_cii_rating(
        vessel_category=vessel_category,
        capacity_dwt_or_teu=capacity,
        annual_fuel_tonnes=annual_fuel_tonnes,
        annual_distance_nm=annual_distance_nm,
        year=year,
    )

    eu_res = ComplianceService.calculate_eu_ets_and_fueleu(
        annual_fuel_tonnes=annual_fuel_tonnes,
        ets_carbon_price_eur=carbon_price_eur,
    )

    return {
        "cii_evaluation": cii_res,
        "eu_regulatory_impact": eu_res,
    }
