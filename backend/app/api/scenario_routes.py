"""
Scenario Analysis API Endpoints:
Fuel pathways, carbon price sensitivity, and slow steaming.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query
from backend.app.services.scenario_service import ScenarioService

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.get("/fuel-pathways")
def get_fuel_pathways(routes: Optional[str] = Query(None, description="Comma-separated route IDs")) -> Dict[str, Any]:
    """Compare baseline HFO fleet vs LNG, Green Methanol, Ammonia, Hydrogen, and Shore Power."""
    route_list = [r.strip() for r in routes.split(",")] if routes else None
    return ScenarioService.run_fuel_pathway_comparison(route_list)


@router.get("/carbon-price-sensitivity")
def get_carbon_sensitivity() -> Dict[str, Any]:
    """Retrieve cost trajectories from $0 to $300 / tonne and break-even carbon price."""
    return ScenarioService.run_carbon_price_sensitivity()


@router.get("/slow-steaming")
def get_slow_steaming(vessel_id: str = Query("panamax_container")) -> List[Dict[str, Any]]:
    """Analyze fuel savings and voyage duration across speed spectrum."""
    return ScenarioService.run_slow_steaming_analysis(vessel_id)
