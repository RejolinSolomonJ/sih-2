"""
Quantum-Inspired Evolutionary Algorithm for Multi-Objective Optimization (QIEA-NSGA).
Uses Q-bit angle representation, quantum rotation gates guided by an external Pareto archive,
quantum catastrophe operators for diversity preservation, and non-dominated sorting with crowding distance.
"""

from typing import List, Dict, Any, Tuple, Optional, Callable
import time
import math
import numpy as np
from backend.app.optimization.metrics import (
    fast_non_dominated_sort,
    calculate_crowding_distance,
    calculate_hypervolume,
    dominates,
)
from backend.app.optimization.problem import FleetOptimizationProblem


class QIEANSGAOptimizer:
    """
    QIEA-NSGA: Quantum-Inspired Evolutionary Multi-Objective Optimization Algorithm.
    """

    def __init__(
        self,
        problem: FleetOptimizationProblem,
        pop_size: int = 40,
        max_generations: int = 50,
        rotation_angle: float = 0.04 * math.pi,
        catastrophe_threshold: float = 0.015,
        seed: int = 42,
    ):
        self.problem = problem
        self.pop_size = pop_size
        self.max_generations = max_generations
        self.rotation_angle = rotation_angle
        self.catastrophe_threshold = catastrophe_threshold
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.dims = problem.total_dims
        self.lb = problem.lower_bounds
        self.ub = problem.upper_bounds

        # Q-state representation: phase angles theta in [0, pi/2] where
        # alpha = cos(theta), beta = sin(theta)
        # Prob(1) = sin^2(theta)
        self.theta_pop = np.full(
            (self.pop_size, self.dims), math.pi / 4.0, dtype=np.float64
        )

        # External Pareto Archive: list of (x, objectives, metadata)
        self.archive: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []

    def observe(self, theta_ind: np.ndarray) -> np.ndarray:
        """
        Quantum measurement: sample random continuous values within [lb, ub]
        modulated by quantum probability amplitude sin^2(theta).
        """
        sin2 = np.sin(theta_ind) ** 2
        # Center around normalized expectation with quantum variance
        r = self.rng.normal(loc=sin2, scale=0.10)
        norm_val = np.clip(r, 0.0, 1.0)
        return self.lb + norm_val * (self.ub - self.lb)

    def update_archive(self, candidates: List[Dict[str, Any]]):
        """Update external non-dominated Pareto archive with new candidate solutions."""
        combined = self.archive + candidates
        if len(combined) == 0:
            return

        objs = np.array([item["objectives"] for item in combined])
        fronts = fast_non_dominated_sort(objs)
        first_front_indices = fronts[0]

        # Filter strictly non-dominated solutions
        new_archive = [combined[i] for i in first_front_indices]

        # Prune duplicate/nearly identical solutions
        unique_archive = []
        seen_objs = set()
        for item in new_archive:
            key = tuple(np.round(item["objectives"], 1))
            if key not in seen_objs:
                seen_objs.add(key)
                unique_archive.append(item)

        # Cap archive size to 100 using crowding distance if needed
        max_archive_size = 100
        if len(unique_archive) > max_archive_size:
            arch_objs = np.array([it["objectives"] for it in unique_archive])
            cd = calculate_crowding_distance(arch_objs, list(range(len(unique_archive))))
            sorted_indices = np.argsort(cd)[::-1]
            unique_archive = [unique_archive[idx] for idx in sorted_indices[:max_archive_size]]

        self.archive = unique_archive

    def apply_rotation_gate(
        self, theta_ind: np.ndarray, current_x: np.ndarray, guide_x: np.ndarray
    ) -> np.ndarray:
        """Rotate quantum phase angles towards the guide non-dominated solution."""
        updated = np.copy(theta_ind)
        # Normalized target position
        norm_guide = (guide_x - self.lb) / (self.ub - self.lb)
        target_theta = np.arcsin(np.sqrt(np.clip(norm_guide, 0.0, 1.0)))

        for d in range(self.dims):
            diff = target_theta[d] - updated[d]
            if abs(diff) > 1e-4:
                direction = 1.0 if diff > 0 else -1.0
                updated[d] += direction * min(abs(diff), self.rotation_angle)
                # Keep in first quadrant [0.01, pi/2 - 0.01]
                updated[d] = np.clip(updated[d], 0.01, (math.pi / 2.0) - 0.01)

        return updated

    def quantum_catastrophe(self):
        """Catastrophe operator: reset 25% of population to maximal superposition to escape stagnation."""
        num_reset = max(1, self.pop_size // 4)
        indices = self.rng.choice(self.pop_size, size=num_reset, replace=False)
        for idx in indices:
            self.theta_pop[idx] = (math.pi / 4.0) + self.rng.normal(0, 0.15, size=self.dims)
            self.theta_pop[idx] = np.clip(self.theta_pop[idx], 0.01, (math.pi / 2.0) - 0.01)

    def optimize(
        self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Execute QIEA-NSGA optimization loop."""
        start_time = time.time()
        print(f"Starting QIEA-NSGA optimization: {self.pop_size} population x {self.max_generations} generations...")

        # Dynamically set reference point based on problem scale
        ref_point = np.array([250_000.0, 120_000_000.0, 800_000.0])

        for gen in range(self.max_generations):
            gen_candidates = []

            # 1. Observation
            pop_x = np.zeros((self.pop_size, self.dims))
            pop_objs = np.zeros((self.pop_size, 3))
            pop_meta = []

            for i in range(self.pop_size):
                x = self.observe(self.theta_pop[i])
                objs, meta = self.problem.evaluate(x)
                pop_x[i] = x
                pop_objs[i] = objs
                pop_meta.append(meta)

                gen_candidates.append({
                    "x": x.tolist(),
                    "objectives": objs.tolist(),
                    "metadata": meta,
                })

            # 2. Update Archive
            self.update_archive(gen_candidates)

            # 3. Non-dominated sort on current generation
            fronts = fast_non_dominated_sort(pop_objs)

            # 4. Check diversity & catastrophe trigger
            diversity = float(np.mean(np.var(self.theta_pop, axis=0)))
            if diversity < self.catastrophe_threshold:
                self.quantum_catastrophe()

            # 5. Quantum rotation updates towards archive guides
            for i in range(self.pop_size):
                if len(self.archive) > 0:
                    # Tournament selection from archive
                    idx1, idx2 = self.rng.choice(len(self.archive), size=2, replace=True)
                    g1 = np.array(self.archive[idx1]["x"])
                    g2 = np.array(self.archive[idx2]["x"])
                    guide = g1 if self.rng.random() < 0.5 else g2
                else:
                    best_curr_idx = fronts[0][0]
                    guide = pop_x[best_curr_idx]

                self.theta_pop[i] = self.apply_rotation_gate(
                    self.theta_pop[i], pop_x[i], guide
                )

            # Metrics for monitoring
            arch_objs = np.array([item["objectives"] for item in self.archive])
            hv = calculate_hypervolume(arch_objs, ref_point)
            best_fuel = float(np.min(arch_objs[:, 0]))
            best_cost = float(np.min(arch_objs[:, 1]))
            best_co2e = float(np.min(arch_objs[:, 2]))

            stat = {
                "generation": gen + 1,
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
        print(f"QIEA-NSGA completed in {runtime:.2f}s with {len(self.archive)} non-dominated Pareto solutions.")

        return {
            "algorithm": "QIEA-NSGA",
            "runtime_sec": round(runtime, 2),
            "final_hypervolume": self.history[-1]["hypervolume"],
            "pareto_solutions": self.archive,
            "convergence_history": self.history,
        }
