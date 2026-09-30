"""
Pydantic V2 schemas for prediction training, inference, and explainability.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TrainModelRequest(BaseModel):
    model_type: str = Field("qiea_xgboost", description="qiea_xgboost, simulated_vqc, ridge, random_forest, xgboost_baseline, mlp")
    samples_limit: Optional[int] = Field(5000, description="Max samples for training to ensure responsive latency")
    qiea_generations: Optional[int] = Field(15, description="Generations for QIEA feature search")
    qiea_pop_size: Optional[int] = Field(12, description="Population size for QIEA")
    seed: int = Field(42, description="Reproducibility random seed")


class SinglePredictionRequest(BaseModel):
    vessel_id: str = "panamax_container"
    fuel_id: str = "hfo"
    speed_knots: float = 18.5
    speed_stw_knots: Optional[float] = 18.5
    draft_m: float = 13.0
    cargo_load_ratio: float = 0.85
    cargo_tonnes: Optional[float] = 55000.0
    wave_height_m: float = 2.0
    wind_speed_knots: float = 14.0
    wind_direction_deg: float = 0.0
    current_knots: float = 0.0
    fouling_index: float = 0.10
    distance_nm: float = 500.0
    engine_load_fraction: Optional[float] = 0.78
    sfoc_g_per_kwh: Optional[float] = 175.0
    added_resistance_wind_kw: Optional[float] = 120.0
    added_resistance_wave_kw: Optional[float] = 250.0
    added_resistance_fouling_kw: Optional[float] = 80.0
    confidence_level: float = 0.95


class FeatureAttribution(BaseModel):
    feature: str
    value: float
    attribution: float
    abs_impact: float


class PredictionResponse(BaseModel):
    model_id: str
    model_type: str
    predicted_fuel_tonnes: float
    ci_lower: float
    ci_upper: float
    ci_level: float
    standard_error: float
    predicted_co2e_wtw_tonnes: float
    estimated_fuel_cost_usd: float
    physics_baseline_comparison: Dict[str, Any]
    feature_attributions: List[FeatureAttribution]
