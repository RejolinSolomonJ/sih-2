"""
Asynchronous background optimization job runner with queue, progress broadcasting (SSE),
and thread-safe state storage.
"""

from typing import Dict, Any, Optional, List
import uuid
import threading
import time
import asyncio
import numpy as np
import yaml
from pathlib import Path

from backend.app.optimization.problem import FleetOptimizationProblem
from backend.app.optimization.qiea import QIEANSGAOptimizer
from backend.app.optimization.qpso import QPSOMultiObjectiveOptimizer
from backend.app.optimization.nsga2 import NSGA2Optimizer
from backend.app.optimization.pso import MOPSOOptimizer
from backend.app.optimization.weighted_ga import WeightedSumGAOptimizer
from backend.app.optimization.topsis import rank_pareto_front_topsis

CONFIG_DIR = Path("config")


class JobManager:
    _jobs: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def create_job(cls, req_data: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())[:8]
        with cls._lock:
            cls._jobs[job_id] = {
                "job_id": job_id,
                "status": "QUEUED",
                "progress": [],
                "result": None,
                "error": None,
                "created_at": time.time(),
                "request": req_data,
            }
        return job_id

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            return cls._jobs.get(job_id)

    @classmethod
    def list_jobs(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            return [
                {
                    "job_id": j["job_id"],
                    "status": j["status"],
                    "algorithm": j["request"].get("algorithm"),
                    "created_at": j["created_at"],
                    "progress_len": len(j["progress"]),
                }
                for j in cls._jobs.values()
            ]

    @classmethod
    def start_optimization_thread(cls, job_id: str):
        thread = threading.Thread(target=cls._run_worker, args=(job_id,), daemon=True)
        thread.start()

    @classmethod
    def _run_worker(cls, job_id: str):
        job = cls.get_job(job_id)
        if not job:
            return

        with cls._lock:
            job["status"] = "RUNNING"

        req = job["request"]
        algo_name = req.get("algorithm", "QIEA-NSGA")
        pop_size = req.get("population_size", 24)
        generations = req.get("generations", 25)
        seed = req.get("seed", 42)
        carbon_price = req.get("carbon_price_usd", 85.0)
        emission_cap = req.get("emission_cap_intensity")
        budget = req.get("fleet_budget_usd")
        topsis_weights = req.get("topsis_weights", [0.33, 0.34, 0.33])
        use_surrogate = req.get("use_surrogate", True)

        try:
            # Load problem configurations
            with open(CONFIG_DIR / "fuels.yaml", "r", encoding="utf-8") as f:
                fuels = yaml.safe_load(f)["fuels"]
            with open(CONFIG_DIR / "vessels.yaml", "r", encoding="utf-8") as f:
                vessels = yaml.safe_load(f)["vessels"]
            with open(CONFIG_DIR / "routes.yaml", "r", encoding="utf-8") as f:
                routes = yaml.safe_load(f)["routes"]

            selected_routes = req.get("selected_route_ids")
            if selected_routes:
                routes = [r for r in routes if r["id"] in selected_routes]
            else:
                routes = routes[:3]  # Default to 3 routes for fast responsive runtime

            problem = FleetOptimizationProblem(
                routes=routes,
                vessels=vessels,
                fuels=fuels,
                carbon_price_usd_per_tonne=carbon_price,
                emission_cap_intensity=emission_cap,
                fleet_budget_usd=budget,
                use_surrogate=use_surrogate,
            )

            def on_progress(stat: Dict[str, Any]):
                with cls._lock:
                    job["progress"].append(stat)

            if algo_name == "QIEA-NSGA":
                optimizer = QIEANSGAOptimizer(problem, pop_size=pop_size, max_generations=generations, seed=seed)
            elif algo_name == "QPSO-MO":
                optimizer = QPSOMultiObjectiveOptimizer(problem, swarm_size=pop_size, max_iterations=generations, seed=seed)
            elif algo_name == "NSGA-II":
                optimizer = NSGA2Optimizer(problem, pop_size=pop_size, max_generations=generations, seed=seed)
            elif algo_name == "MOPSO":
                optimizer = MOPSOOptimizer(problem, swarm_size=pop_size, max_iterations=generations, seed=seed)
            else:
                optimizer = WeightedSumGAOptimizer(problem, pop_size=pop_size, max_generations=generations, seed=seed)

            raw_res = optimizer.optimize(progress_callback=on_progress)
            pareto = raw_res["pareto_solutions"]

            # TOPSIS compromise selection
            if len(pareto) > 0:
                objs = np.array([p["objectives"] for p in pareto])
                best_idx, closeness, _ = rank_pareto_front_topsis(objs, weights=topsis_weights)
            else:
                best_idx = 0
                closeness = np.array([])

            formatted_pareto = []
            for i, p in enumerate(pareto):
                meta = p.get("metadata", {})
                score = float(closeness[i]) if i < len(closeness) else 0.5
                formatted_pareto.append({
                    "solution_id": i,
                    "objectives": p["objectives"],
                    "is_topsis_recommended": (i == best_idx),
                    "topsis_score": round(score, 4),
                    "plan_details": meta.get("plan_details", []),
                    "unpenalized_fuel_tonnes": meta.get("unpenalized_fuel_tonnes", p["objectives"][0]),
                    "unpenalized_cost_usd": meta.get("unpenalized_cost_usd", p["objectives"][1]),
                    "unpenalized_co2e_wtw_tonnes": meta.get("unpenalized_co2e_wtw_tonnes", p["objectives"][2]),
                })

            recommended = formatted_pareto[best_idx] if formatted_pareto else None

            final_result = {
                "job_id": job_id,
                "status": "COMPLETED",
                "algorithm": algo_name,
                "runtime_sec": raw_res["runtime_sec"],
                "final_hypervolume": raw_res["final_hypervolume"],
                "total_pareto_count": len(formatted_pareto),
                "recommended_solution": recommended,
                "pareto_front": formatted_pareto,
                "convergence_history": raw_res["convergence_history"],
            }

            with cls._lock:
                job["status"] = "COMPLETED"
                job["result"] = final_result

        except Exception as e:
            with cls._lock:
                job["status"] = "FAILED"
                job["error"] = str(e)
            print(f"Optimization job {job_id} failed: {e}")
