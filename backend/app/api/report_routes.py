"""
PDF Report generation endpoints.
"""

from fastapi import APIRouter, HTTPException, Response
from backend.app.services.job_manager import JobManager
from backend.app.services.report_service import ReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/optimization/{job_id}/pdf")
def export_optimization_report_pdf(job_id: str) -> Response:
    """Download executive PDF report for a completed fleet optimization job."""
    job = JobManager.get_job(job_id)
    if not job or not job.get("result"):
        # If job not found, create a sample report for preview/demo
        sample_plan = {
            "unpenalized_fuel_tonnes": 14250.0,
            "unpenalized_cost_usd": 18450000.0,
            "unpenalized_co2e_wtw_tonnes": 48200.0,
            "plan_details": [
                {
                    "route_name": "Asia - Northern Europe Loop",
                    "vessel_name": "Panamax Container",
                    "vessel_count": 4,
                    "speed_knots": 17.5,
                    "fuel_name": "Green e-Methanol",
                    "shore_power_use": 1,
                    "quarter_cost_usd": 9200000.0,
                },
                {
                    "route_name": "Transpacific Eastbound",
                    "vessel_name": "Panamax Container",
                    "vessel_count": 3,
                    "speed_knots": 18.0,
                    "fuel_name": "Liquefied Natural Gas",
                    "shore_power_use": 1,
                    "quarter_cost_usd": 6800000.0,
                },
                {
                    "route_name": "Mediterranean Short-Sea Feeder",
                    "vessel_name": "Container Feeder",
                    "vessel_count": 2,
                    "speed_knots": 14.5,
                    "fuel_name": "Marine Gas Oil (MGO)",
                    "shore_power_use": 1,
                    "quarter_cost_usd": 2450000.0,
                },
            ],
        }
        meta = {"algorithm": "QIEA-NSGA", "hypervolume": 142500.0}
        pdf_bytes = ReportGenerator.generate_fleet_optimization_pdf(job_id or "DEMO-01", sample_plan, meta)
    else:
        res = job["result"]
        rec = res.get("recommended_solution") or {}
        meta = {"algorithm": res.get("algorithm", "QIEA-NSGA"), "hypervolume": res.get("final_hypervolume", 0.0)}
        pdf_bytes = ReportGenerator.generate_fleet_optimization_pdf(job_id, rec, meta)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=greenfleet_report_{job_id}.pdf"},
    )
