"""
Benchmarking API Endpoints: Multi-algorithm runner, statistical comparisons,
Wilcoxon signed-rank significance tests, and CSV export.
"""

from typing import Dict, Any, Optional
import io
import pandas as pd
from fastapi import APIRouter, Query, Response
from backend.app.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


@router.get("/run")
def run_benchmark(
    instance_size: str = Query("small", description="small, medium, large"),
    num_runs: int = Query(3, ge=1, le=10),
    seed: int = Query(42),
) -> Dict[str, Any]:
    """Execute multi-algorithm benchmark suite across QIEA-NSGA, QPSO-MO, NSGA-II, MOPSO, and WSGA."""
    return BenchmarkService.run_benchmark_suite(instance_size=instance_size, num_runs=num_runs, base_seed=seed)


@router.get("/export/csv")
def export_benchmark_csv(instance_size: str = Query("small"), num_runs: int = Query(3)) -> Response:
    """Export benchmark summary metrics table as CSV."""
    res = BenchmarkService.run_benchmark_suite(instance_size=instance_size, num_runs=num_runs)
    df = pd.DataFrame(res["summary"])
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=greenfleet_benchmark_{instance_size}.csv"},
    )
