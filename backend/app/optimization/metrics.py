"""
Multi-objective optimization metrics: Pareto dominance, fast non-dominated sorting,
crowding distance, Hypervolume (HV), Inverted Generational Distance (IGD), and Spread (Delta).
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np


def dominates(obj_a: np.ndarray, obj_b: np.ndarray) -> bool:
    """True if vector obj_a weakly dominates obj_b and is strictly better in at least one objective."""
    return bool(np.all(obj_a <= obj_b) and np.any(obj_a < obj_b))


def fast_non_dominated_sort(objectives: np.ndarray) -> List[List[int]]:
    """
    Deb's fast non-dominated sorting algorithm.
    Returns list of Pareto fronts where fronts[0] is the primary non-dominated front.
    """
    n = len(objectives)
    domination_counts = np.zeros(n, dtype=int)
    dominated_solutions = [[] for _ in range(n)]
    fronts: List[List[int]] = [[]]

    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if dominates(objectives[p], objectives[q]):
                dominated_solutions[p].append(q)
            elif dominates(objectives[q], objectives[p]):
                domination_counts[p] += 1

        if domination_counts[p] == 0:
            fronts[0].append(p)

    i = 0
    while len(fronts[i]) > 0:
        next_front = []
        for p in fronts[i]:
            for q in dominated_solutions[p]:
                domination_counts[q] -= 1
                if domination_counts[q] == 0:
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    if len(fronts[-1]) == 0:
        fronts.pop()

    return fronts


def calculate_crowding_distance(objectives: np.ndarray, front_indices: List[int]) -> np.ndarray:
    """Calculate crowding distance for individuals in a given Pareto front."""
    l = len(front_indices)
    distances = np.zeros(l, dtype=np.float64)
    if l <= 2:
        distances[:] = float("inf")
        return distances

    num_objectives = objectives.shape[1]
    front_objs = objectives[front_indices]

    for m in range(num_objectives):
        sorted_order = np.argsort(front_objs[:, m])
        distances[sorted_order[0]] = float("inf")
        distances[sorted_order[-1]] = float("inf")

        obj_min = front_objs[sorted_order[0], m]
        obj_max = front_objs[sorted_order[-1], m]
        norm = max(1e-8, obj_max - obj_min)

        for i in range(1, l - 1):
            distances[sorted_order[i]] += (
                front_objs[sorted_order[i + 1], m] - front_objs[sorted_order[i - 1], m]
            ) / norm

    return distances


def calculate_hypervolume_2d(front: np.ndarray, ref_point: np.ndarray) -> float:
    """
    Calculate 2D Hypervolume bounded by ref_point.
    Assumes minimization: front objectives must be <= ref_point.
    """
    if len(front) == 0:
        return 0.0

    valid_mask = np.all(front <= ref_point, axis=1)
    valid_points = front[valid_mask]
    if len(valid_points) == 0:
        return 0.0

    # Sort ascending by first objective
    sorted_pts = valid_points[np.argsort(valid_points[:, 0])]

    hv = 0.0
    current_y = ref_point[1]

    for pt in sorted_pts:
        width = ref_point[0] - pt[0]
        height = max(0.0, current_y - pt[1])
        hv += width * height
        current_y = min(current_y, pt[1])

    return float(hv)


def calculate_hypervolume(front: np.ndarray, ref_point: np.ndarray) -> float:
    """
    Compute Hypervolume (exact for 2D, Monte Carlo approximation for 3D+).
    Assumes minimization.
    """
    if len(front) == 0:
        return 0.0

    m = front.shape[1]
    if m == 2:
        return calculate_hypervolume_2d(front, ref_point)

    # 3D Monte Carlo integration for fast real-time performance
    n_samples = 4000
    valid_mask = np.all(front <= ref_point, axis=1)
    pts = front[valid_mask]
    if len(pts) == 0:
        return 0.0

    mins = np.min(pts, axis=0)
    # Bounding box volume
    box_vol = np.prod(ref_point - mins)
    if box_vol <= 0:
        return 0.0

    rng = np.random.default_rng(42)
    samples = rng.uniform(mins, ref_point, size=(n_samples, m))

    # Point is dominated if any front point <= sample
    dominated_count = 0
    for s in samples:
        if np.any(np.all(pts <= s, axis=1)):
            dominated_count += 1

    return float((dominated_count / n_samples) * box_vol)


def calculate_igd(front: np.ndarray, reference_front: np.ndarray) -> float:
    """
    Inverted Generational Distance (IGD):
    Average Euclidean distance from each point in the reference front to the closest point in front.
    Lower is better (0 = perfect convergence and coverage).
    """
    if len(front) == 0 or len(reference_front) == 0:
        return float("inf")

    # Min distances from ref points to front
    dists = []
    for r_pt in reference_front:
        d = np.min(np.linalg.norm(front - r_pt, axis=1))
        dists.append(d)

    return float(np.mean(dists))


def calculate_spread(front: np.ndarray) -> float:
    """
    Spread metric Delta (diversity across Pareto front).
    0 = ideal uniform distribution.
    """
    if len(front) <= 2:
        return 0.0

    # Sort by first objective
    sorted_front = front[np.argsort(front[:, 0])]
    dists = np.linalg.norm(sorted_front[1:] - sorted_front[:-1], axis=1)
    d_mean = np.mean(dists)
    if d_mean < 1e-9:
        return 0.0

    d_first = dists[0]
    d_last = dists[-1]
    numerator = d_first + d_last + np.sum(np.abs(dists - d_mean))
    denominator = d_first + d_last + len(dists) * d_mean
    return float(numerator / max(1e-8, denominator))
