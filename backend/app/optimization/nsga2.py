"""
Standard NSGA-II Baseline Multi-Objective Evolutionary Algorithm.
Implements Simulated Binary Crossover (SBX), Polynomial Mutation,
Fast Non-Dominated Sorting, and Crowding Distance Selection.
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


class NSGA2Optimizer:
    """Standard Elitist NSGA-II Multi-Objective Optimizer."""

    def __init__(
        self,
        problem: FleetOptimizationProblem,
        pop_size: int = 40,
        max_generations: int = 50,
        crossover_prob: float = 0.9,
        mutation_prob: float = 0.1,
        eta_c: float = 20.0,
        eta_m: float = 20.0,
        seed: int = 42,
    ):
        self.problem = problem
        self.pop_size = pop_size
        self.max_generations = max_generations
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.eta_c = eta_c
        self.eta_m = eta_m
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.dims = problem.total_dims
        self.lb = problem.lower_bounds
        self.ub = problem.upper_bounds

        self.population = self.rng.uniform(self.lb, self.ub, size=(self.pop_size, self.dims))
        self.history: List[Dict[str, Any]] = []

    def sbx_crossover(self, p1: np.ndarray, p2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Simulated Binary Crossover (SBX)."""
        c1, c2 = np.copy(p1), np.copy(p2)
        if self.rng.random() > self.crossover_prob:
            return c1, c2

        for i in range(self.dims):
            if abs(p1[i] - p2[i]) > 1e-10:
                y1 = min(p1[i], p2[i])
                y2 = max(p1[i], p2[i])
                yl = self.lb[i]
                yu = self.ub[i]

                rand = self.rng.random()
                beta = 1.0 + (2.0 * (y1 - yl) / (y2 - y1))
                alpha = 2.0 - (beta ** -(self.eta_c + 1.0))
                if rand <= (1.0 / alpha):
                    beta_q = (rand * alpha) ** (1.0 / (self.eta_c + 1.0))
                else:
                    beta_q = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (self.eta_c + 1.0))

                c1[i] = 0.5 * ((y1 + y2) - beta_q * (y2 - y1))
                c2[i] = 0.5 * ((y1 + y2) + beta_q * (y2 - y1))

                c1[i] = np.clip(c1[i], yl, yu)
                c2[i] = np.clip(c2[i], yl, yu)

        return c1, c2

    def polynomial_mutation(self, ind: np.ndarray) -> np.ndarray:
        """Polynomial Mutation."""
        mutated = np.copy(ind)
        for i in range(self.dims):
            if self.rng.random() < self.mutation_prob:
                y = mutated[i]
                yl = self.lb[i]
                yu = self.ub[i]
                delta1 = (y - yl) / max(1e-8, yu - yl)
                delta2 = (yu - y) / max(1e-8, yu - yl)
                rand = self.rng.random()
                mut_pow = 1.0 / (self.eta_m + 1.0)
                if rand < 0.5:
                    xy = 1.0 - delta1
                    val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (self.eta_m + 1.0))
                    delta_q = (val ** mut_pow) - 1.0
                else:
                    xy = 1.0 - delta2
                    val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (self.eta_m + 1.0))
                    delta_q = 1.0 - (val ** mut_pow)

                y += delta_q * (yu - yl)
                mutated[i] = np.clip(y, yl, yu)

        return mutated

    def optimize(
        self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        print(f"Starting NSGA-II: {self.pop_size} population x {self.max_generations} generations...")
        ref_point = np.array([250_000.0, 120_000_000.0, 800_000.0])

        # Evaluate initial population
        pop_objs = np.zeros((self.pop_size, 3))
        pop_meta = []
        for i in range(self.pop_size):
            objs, meta = self.problem.evaluate(self.population[i])
            pop_objs[i] = objs
            pop_meta.append(meta)

        for gen in range(self.max_generations):
            # 1. Generate offspring via tournament, SBX and mutation
            offspring = np.zeros((self.pop_size, self.dims))
            for i in range(0, self.pop_size, 2):
                p1_idx = self.rng.choice(self.pop_size)
                p2_idx = self.rng.choice(self.pop_size)
                c1, c2 = self.sbx_crossover(self.population[p1_idx], self.population[p2_idx])
                offspring[i] = self.polynomial_mutation(c1)
                if i + 1 < self.pop_size:
                    offspring[i + 1] = self.polynomial_mutation(c2)

            # Evaluate offspring
            off_objs = np.zeros((self.pop_size, 3))
            off_meta = []
            for i in range(self.pop_size):
                objs, meta = self.problem.evaluate(offspring[i])
                off_objs[i] = objs
                off_meta.append(meta)

            # 2. Merge parent and offspring: 2N pool
            combined_pop = np.vstack([self.population, offspring])
            combined_objs = np.vstack([pop_objs, off_objs])
            combined_meta = pop_meta + off_meta

            # 3. Fast non-dominated sort on 2N pool
            fronts = fast_non_dominated_sort(combined_objs)

            # 4. Select N best individuals
            new_pop_indices = []
            for front in fronts:
                if len(new_pop_indices) + len(front) <= self.pop_size:
                    new_pop_indices.extend(front)
                else:
                    needed = self.pop_size - len(new_pop_indices)
                    cd = calculate_crowding_distance(combined_objs, front)
                    sorted_by_cd = np.argsort(cd)[::-1]
                    new_pop_indices.extend([front[idx] for idx in sorted_by_cd[:needed]])
                    break

            self.population = combined_pop[new_pop_indices]
            pop_objs = combined_objs[new_pop_indices]
            pop_meta = [combined_meta[idx] for idx in new_pop_indices]

            # 5. Pareto front metrics
            front0_indices = fronts[0]
            front0_objs = combined_objs[front0_indices]
            hv = calculate_hypervolume(front0_objs, ref_point)

            stat = {
                "generation": gen + 1,
                "hypervolume": round(hv, 2),
                "archive_size": len(front0_indices),
                "best_fuel_tonnes": round(float(np.min(pop_objs[:, 0])), 1),
                "best_cost_usd": round(float(np.min(pop_objs[:, 1])), 2),
                "best_co2e_tonnes": round(float(np.min(pop_objs[:, 2])), 1),
                "elapsed_sec": round(time.time() - start_time, 2),
            }
            self.history.append(stat)

            if progress_callback is not None:
                progress_callback(stat)

        runtime = time.time() - start_time
        final_fronts = fast_non_dominated_sort(pop_objs)
        pareto_solutions = [
            {
                "x": self.population[idx].tolist(),
                "objectives": pop_objs[idx].tolist(),
                "metadata": pop_meta[idx],
            }
            for idx in final_fronts[0]
        ]

        return {
            "algorithm": "NSGA-II",
            "runtime_sec": round(runtime, 2),
            "final_hypervolume": self.history[-1]["hypervolume"],
            "pareto_solutions": pareto_solutions,
            "convergence_history": self.history,
        }
