"""
Standard Multi-Objective Particle Swarm Optimization (MOPSO) baseline.
Uses inertia weight decay, cognitive and social velocity acceleration,
and an external Pareto repository.
"""

from typing import List, Dict, Any, Tuple, Optional, Callable
import time
import numpy as np
from backend.app.optimization.metrics import (
    fast_non_dominated_sort,
    calculate_crowding_distance,
    calculate_hypervolume,
)
from backend.app.optimization.problem import FleetOptimizationProblem


class MOPSOOptimizer:
    """Standard Multi-Objective Particle Swarm Optimizer (MOPSO)."""

    def __init__(
        self,
        problem: FleetOptimizationProblem,
        swarm_size: int = 40,
        max_iterations: int = 50,
        w: float = 0.6,
        c1: float = 1.6,
        c2: float = 1.6,
        seed: int = 42,
    ):
        self.problem = problem
        self.swarm_size = swarm_size
        self.max_iterations = max_iterations
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.dims = problem.total_dims
        self.lb = problem.lower_bounds
        self.ub = problem.upper_bounds

        self.positions = self.rng.uniform(self.lb, self.ub, size=(self.swarm_size, self.dims))
        v_max = (self.ub - self.lb) * 0.15
        self.velocities = self.rng.uniform(-v_max, v_max, size=(self.swarm_size, self.dims))
        self.v_max = v_max

        self.pbest_positions = np.copy(self.positions)
        self.pbest_objectives = np.full((self.swarm_size, 3), float("inf"))

        self.archive: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []

    def update_archive(self, candidates: List[Dict[str, Any]]):
        combined = self.archive + candidates
        if len(combined) == 0:
            return

        objs = np.array([item["objectives"] for item in combined])
        fronts = fast_non_dominated_sort(objs)
        first_front = [combined[i] for i in fronts[0]]

        unique = []
        seen = set()
        for item in first_front:
            k = tuple(np.round(item["objectives"], 1))
            if k not in seen:
                seen.add(k)
                unique.append(item)

        if len(unique) > 100:
            arch_objs = np.array([it["objectives"] for it in unique])
            cd = calculate_crowding_distance(arch_objs, list(range(len(unique))))
            sorted_idx = np.argsort(cd)[::-1]
            unique = [unique[idx] for idx in sorted_idx[:100]]

        self.archive = unique

    def optimize(
        self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        print(f"Starting MOPSO: {self.swarm_size} particles x {self.max_iterations} iterations...")
        ref_point = np.array([250_000.0, 120_000_000.0, 800_000.0])

        for it in range(self.max_iterations):
            candidates = []

            for i in range(self.swarm_size):
                pos = self.positions[i]
                objs, meta = self.problem.evaluate(pos)

                prev = self.pbest_objectives[i]
                if np.all(objs <= prev) and np.any(objs < prev):
                    self.pbest_objectives[i] = objs
                    self.pbest_positions[i] = np.copy(pos)
                elif not (np.all(prev <= objs) and np.any(prev < objs)):
                    if self.rng.random() < 0.5:
                        self.pbest_objectives[i] = objs
                        self.pbest_positions[i] = np.copy(pos)

                candidates.append({
                    "x": pos.tolist(),
                    "objectives": objs.tolist(),
                    "metadata": meta,
                })

            self.update_archive(candidates)

            # Update velocities and positions
            for i in range(self.swarm_size):
                if len(self.archive) > 0:
                    leader_idx = self.rng.choice(len(self.archive))
                    gbest = np.array(self.archive[leader_idx]["x"])
                else:
                    gbest = self.pbest_positions[i]

                r1 = self.rng.uniform(0.0, 1.0, size=self.dims)
                r2 = self.rng.uniform(0.0, 1.0, size=self.dims)

                new_v = (
                    self.w * self.velocities[i]
                    + self.c1 * r1 * (self.pbest_positions[i] - self.positions[i])
                    + self.c2 * r2 * (gbest - self.positions[i])
                )
                self.velocities[i] = np.clip(new_v, -self.v_max, self.v_max)
                new_pos = self.positions[i] + self.velocities[i]
                self.positions[i] = np.clip(new_pos, self.lb, self.ub)

            arch_objs = np.array([item["objectives"] for item in self.archive])
            hv = calculate_hypervolume(arch_objs, ref_point)

            stat = {
                "generation": it + 1,
                "hypervolume": round(hv, 2),
                "archive_size": len(self.archive),
                "best_fuel_tonnes": round(float(np.min(arch_objs[:, 0])), 1),
                "best_cost_usd": round(float(np.min(arch_objs[:, 1])), 2),
                "best_co2e_tonnes": round(float(np.min(arch_objs[:, 2])), 1),
                "elapsed_sec": round(time.time() - start_time, 2),
            }
            self.history.append(stat)

            if progress_callback is not None:
                progress_callback(stat)

        runtime = time.time() - start_time
        return {
            "algorithm": "MOPSO",
            "runtime_sec": round(runtime, 2),
            "final_hypervolume": self.history[-1]["hypervolume"],
            "pareto_solutions": self.archive,
            "convergence_history": self.history,
        }
