"""
Fleet Optimization Endpoints: Background job execution, SSE live streaming,
Pareto front explorer, and TOPSIS compromise plan.
"""

from typing import Dict, Any, Optional
import json
import asyncio
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.app.schemas.optimization import (
    OptimizeFleetRequest,
    OptimizationJobResult,
)
from backend.app.services.job_manager import JobManager

router = APIRouter(prefix="/optimize", tags=["Fleet Optimization"])


@router.post("/run")
def start_optimization_job(req: OptimizeFleetRequest) -> Dict[str, Any]:
    """Start an asynchronous multi-objective fleet optimization run."""
    job_id = JobManager.create_job(req.model_dump())
    JobManager.start_optimization_thread(job_id)
    return {
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Optimization job started in background.",
    }


@router.get("/{job_id}/status")
def get_job_status(job_id: str) -> Dict[str, Any]:
    """Check current execution status and latest convergence progress."""
    job = JobManager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    latest_stat = job["progress"][-1] if job["progress"] else None
    return {
        "job_id": job_id,
        "status": job["status"],
        "error": job.get("error"),
        "latest_stat": latest_stat,
        "total_generations_done": len(job["progress"]),
    }


@router.get("/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """Server-Sent Events (SSE) endpoint for real-time generation and hypervolume streaming."""
    job = JobManager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_generator():
        sent_index = 0
        while True:
            current_job = JobManager.get_job(job_id)
            if not current_job:
                break

            progress_list = current_job["progress"]
            while sent_index < len(progress_list):
                stat = progress_list[sent_index]
                sent_index += 1
                yield f"data: {json.dumps(stat)}\n\n"

            if current_job["status"] in ["COMPLETED", "FAILED"]:
                final_event = {
                    "done": True,
                    "status": current_job["status"],
                    "error": current_job.get("error"),
                }
                yield f"data: {json.dumps(final_event)}\n\n"
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{job_id}/result", response_model=OptimizationJobResult)
def get_job_result(job_id: str) -> OptimizationJobResult:
    """Retrieve full Pareto front, TOPSIS compromise plan, and convergence history."""
    job = JobManager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["status"] == "FAILED":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.get('error')}")

    if job["status"] != "COMPLETED" or not job["result"]:
        raise HTTPException(status_code=202, detail="Job is still running. Please poll or stream.")

    return OptimizationJobResult(**job["result"])


@router.get("/jobs")
def list_optimization_jobs() -> Dict[str, Any]:
    """List recent optimization jobs and their statuses."""
    return {"jobs": JobManager.list_jobs()}
