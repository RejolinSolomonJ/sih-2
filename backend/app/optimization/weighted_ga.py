"""
Weighted-Sum Genetic Algorithm (WSGA) baseline.
Transforms the 3-objective problem into a scalar fitness using diverse weight vectors
across the population, maintaining an archive of non-dominated solutions.
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


class WeightedSumGAOptimizer:
    """Weighted-Sum Multi-Objective Genetic Algorithm."""

    def __init__(
        self,
        problem: FleetOptimizationProblem,
        pop_size: int = 40,
        max_generations: int = 50,
        seed: int = 42,
    ):
        self.problem = problem
        self.pop_size = pop_size
        self.max_generations = max_generations
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.dims = problem.total_dims
        self.lb = problem.lower_bounds
        self.ub = problem.upper_bounds

        self.population = self.rng.uniform(self.lb, self.ub, size=(self.pop_size, self.dims))
        # Uniform weight vectors spanning [w_fuel, w_cost, w_ghg]
        raw_weights = self.rng.uniform(0.1, 1.0, size=(self.pop_size, 3))
        self.weights = raw_weights / np.sum(raw_weights, axis=1, keepdims=True)

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
        print(f"Starting Weighted-Sum GA: {self.pop_size} pop x {self.max_generations} gen...")
        ref_point = np.array([250_000.0, 120_000_000.0, 800_000.0])

        for gen in range(self.max_generations):
            candidates = []
            scalar_fitnesses = np.zeros(self.pop_size)

            for i in range(self.pop_size):
                pos = self.population[i]
                objs, meta = self.problem.evaluate(pos)

                # Normalized scalarization: scale objectives roughly to same magnitude
                norm_objs = objs / np.array([10_000.0, 50_000_000.0, 50_000.0])
                scalar_fitnesses[i] = np.dot(self.weights[i], norm_objs)

                candidates.append({
                    "x": pos.tolist(),
                    "objectives": objs.tolist(),
                    "metadata": meta,
                })

            self.update_archive(candidates)

            # Crossover and Mutation based on scalar fitness
            new_pop = np.zeros_like(self.population)
            # Tournament selection (lower scalar fitness is better)
            for i in range(self.pop_size):
                i1, i2 = self.rng.choice(self.pop_size, size=2, replace=False)
                parent1 = self.population[i1 if scalar_fitnesses[i1] < scalar_fitnesses[i2] else i2]

                i3, i4 = self.rng.choice(self.pop_size, size=2, replace=False)
                parent2 = self.population[i3 if scalar_fitnesses[i3] < scalar_fitnesses[i4] else i4]

                # Uniform crossover
                mask = self.rng.random(self.dims) < 0.5
                child = np.where(mask, parent1, parent2)

                # Gaussian mutation
                if self.rng.random() < 0.25:
                    child += self.rng.normal(0, 0.05 * (self.ub - self.lb), size=self.dims)

                new_pop[i] = np.clip(child, self.lb, self.ub)

            self.population = new_pop

            arch_objs = np.array([item["objectives"] for item in self.archive])
            hv = calculate_hypervolume(arch_objs, ref_point)

            stat = {
                "generation": gen + 1,
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
            "algorithm": "Weighted-Sum GA",
            "runtime_sec": round(runtime, 2),
            "final_hypervolume": self.history[-1]["hypervolume"],
            "pareto_solutions": self.archive,
            "convergence_history": self.history,
        }
