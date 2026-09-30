"""
Quantum-Behaved Multi-Objective Particle Swarm Optimization (QPSO-MO).
In quantum mechanics, particles have no deterministic trajectory; instead,
they appear with probability density according to a delta potential well.
Uses mean best position (mbest), local stochastic attractor, and an external Pareto archive.
"""

from typing import List, Dict, Any, Tuple, Optional, Callable
import time
import math
import numpy as np
from backend.app.optimization.metrics import (
    fast_non_dominated_sort,
    calculate_crowding_distance,
    calculate_hypervolume,
)
from backend.app.optimization.problem import FleetOptimizationProblem


class QPSOMultiObjectiveOptimizer:
    """
    Quantum-behaved Particle Swarm Optimization (QPSO) with external Pareto archive.
    """

    def __init__(
        self,
        problem: FleetOptimizationProblem,
        swarm_size: int = 40,
        max_iterations: int = 50,
        alpha_start: float = 1.0,
        alpha_end: float = 0.5,
        seed: int = 42,
    ):
        self.problem = problem
        self.swarm_size = swarm_size
        self.max_iterations = max_iterations
        self.alpha_start = alpha_start
        self.alpha_end = alpha_end
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.dims = problem.total_dims
        self.lb = problem.lower_bounds
        self.ub = problem.upper_bounds

        # Swarm positions
        self.positions = self.rng.uniform(self.lb, self.ub, size=(self.swarm_size, self.dims))
        # Personal best positions and objectives
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
        first_front_indices = fronts[0]

        new_archive = [combined[i] for i in first_front_indices]
        unique_archive = []
        seen = set()
        for item in new_archive:
            k = tuple(np.round(item["objectives"], 1))
            if k not in seen:
                seen.add(k)
                unique_archive.append(item)

        max_archive_size = 100
        if len(unique_archive) > max_archive_size:
            arch_objs = np.array([it["objectives"] for it in unique_archive])
            cd = calculate_crowding_distance(arch_objs, list(range(len(unique_archive))))
            sorted_indices = np.argsort(cd)[::-1]
            unique_archive = [unique_archive[idx] for idx in sorted_indices[:max_archive_size]]

        self.archive = unique_archive

    def optimize(
        self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        print(f"Starting QPSO-MO: {self.swarm_size} particles x {self.max_iterations} iterations...")
        ref_point = np.array([250_000.0, 120_000_000.0, 800_000.0])

        for it in range(self.max_iterations):
            # Dynamic contraction-expansion coefficient alpha
            alpha = self.alpha_start - (self.alpha_start - self.alpha_end) * (it / max(1, self.max_iterations - 1))

            candidates = []

            # 1. Evaluate particles
            for i in range(self.swarm_size):
                pos = self.positions[i]
                objs, meta = self.problem.evaluate(pos)

                # Check pbest update (weak dominance or random if incomparable)
                prev_objs = self.pbest_objectives[i]
                if np.all(objs <= prev_objs) and np.any(objs < prev_objs):
                    self.pbest_objectives[i] = objs
                    self.pbest_positions[i] = np.copy(pos)
                elif not (np.all(prev_objs <= objs) and np.any(prev_objs < objs)):
                    # Incomparable: 50% chance to update
                    if self.rng.random() < 0.5:
                        self.pbest_objectives[i] = objs
                        self.pbest_positions[i] = np.copy(pos)

                candidates.append({
                    "x": pos.tolist(),
                    "objectives": objs.tolist(),
                    "metadata": meta,
                })

            # 2. Update Pareto Archive
            self.update_archive(candidates)

            # 3. Calculate Mean Best Position (mbest) of the swarm
            mbest = np.mean(self.pbest_positions, axis=0)

            # 4. Quantum state position update for each particle
            for i in range(self.swarm_size):
                # Select gbest from external archive via roulette/tournament on crowding distance
                if len(self.archive) > 0:
                    g_idx = self.rng.choice(len(self.archive))
                    gbest = np.array(self.archive[g_idx]["x"])
                else:
                    gbest = self.pbest_positions[i]

                # Stochastic local attractor: p_i = phi * pbest + (1 - phi) * gbest
                phi = self.rng.uniform(0.0, 1.0, size=self.dims)
                local_attractor = phi * self.pbest_positions[i] + (1.0 - phi) * gbest

                # Quantum delta-potential well wave-function position collapse
                u = self.rng.uniform(0.0001, 0.9999, size=self.dims)
                sign = np.where(self.rng.random(self.dims) < 0.5, 1.0, -1.0)
                
                # Update equation: x = p +/- alpha * |mbest - x| * ln(1/u)
                step = alpha * np.abs(mbest - self.positions[i]) * np.log(1.0 / u)
                new_pos = local_attractor + sign * step

                # Boundary clamping
                self.positions[i] = np.clip(new_pos, self.lb, self.ub)

            arch_objs = np.array([item["objectives"] for item in self.archive])
            hv = calculate_hypervolume(arch_objs, ref_point)
            best_fuel = float(np.min(arch_objs[:, 0]))
            best_cost = float(np.min(arch_objs[:, 1]))
            best_co2e = float(np.min(arch_objs[:, 2]))

            stat = {
                "generation": it + 1,
                "hypervolume": round(hv, 2),
                "archive_size": len(self.archive),
                "best_fuel_tonnes": round(best_fuel, 1),
                "best_cost_usd": round(best_cost, 2),
                "best_co2e_tonnes": round(best_co2e, 1),
                "elapsed_sec": round(time.time() - start_time, 2),
            }
            self.history.append(stat)

            if progress_callback is not None:
                progress_callback(stat)

        runtime = time.time() - start_time
        return {
            "algorithm": "QPSO-MO",
            "runtime_sec": round(runtime, 2),
            "final_hypervolume": self.history[-1]["hypervolume"],
            "pareto_solutions": self.archive,
            "convergence_history": self.history,
        }
