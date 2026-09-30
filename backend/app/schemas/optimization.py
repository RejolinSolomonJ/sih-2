"""
Pydantic V2 schemas for fleet optimization execution, progress, and results.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class OptimizeFleetRequest(BaseModel):
    algorithm: str = Field("QIEA-NSGA", description="QIEA-NSGA, QPSO-MO, NSGA-II, MOPSO, Weighted-Sum GA")
    population_size: int = Field(24, ge=8, le=100)
    generations: int = Field(25, ge=5, le=150)
    selected_route_ids: Optional[List[str]] = None
    carbon_price_usd: float = Field(85.0, ge=0.0)
    emission_cap_intensity: Optional[float] = None
    fleet_budget_usd: Optional[float] = None
    topsis_weights: List[float] = Field(default=[0.33, 0.34, 0.33], min_length=3, max_length=3)
    seed: int = Field(42)
    use_surrogate: bool = Field(True)


class ProgressUpdate(BaseModel):
    generation: int
    hypervolume: float
    archive_size: int
    best_fuel_tonnes: float
    best_cost_usd: float
    best_co2e_tonnes: float
    elapsed_sec: float


class RoutePlanSlot(BaseModel):
    route_id: str
    route_name: str
    vessel_name: str
    vessel_count: int
    speed_knots: float
    fuel_name: str
    shore_power_use: int
    cargo_transported: float
    cargo_demand: float
    cycles_per_vessel: float
    quarter_fuel_tonnes: float
    quarter_cost_usd: float
    quarter_co2e_tonnes: float


class ParetoSolution(BaseModel):
    solution_id: int
    objectives: List[float] # [fuel, cost, co2e]
    is_topsis_recommended: bool
    topsis_score: float
    plan_details: List[RoutePlanSlot]
    unpenalized_fuel_tonnes: float
    unpenalized_cost_usd: float
    unpenalized_co2e_wtw_tonnes: float


class OptimizationJobResult(BaseModel):
    job_id: str
    status: str
    algorithm: str
    runtime_sec: float
    final_hypervolume: float
    total_pareto_count: int
    recommended_solution: Optional[ParetoSolution] = None
    pareto_front: List[ParetoSolution]
    convergence_history: List[ProgressUpdate]
