"""
TOPSIS Multi-Criteria Decision Making (Compromise Solution Ranker).
Finds the balanced optimal compromise on a Pareto front given user-adjustable objective weights.
"""

from typing import List, Dict, Any, Tuple
import numpy as np


def rank_pareto_front_topsis(
    objectives: np.ndarray,
    weights: List[float] = [0.33, 0.34, 0.33],
) -> Tuple[int, np.ndarray, np.ndarray]:
    """
    Apply TOPSIS to rank solutions in a Pareto front for minimization objectives.
    
    Args:
        objectives: Array of shape (N, M) for N solutions and M objectives to minimize.
        weights: List of M weights.
        
    Returns:
        best_index: Index of the top-ranked compromise solution.
        closeness_scores: Array of closeness scores C_i in [0, 1] (higher is better).
        rankings: Sorted indices from best to worst.
    """
    n, m = objectives.shape
    if n == 0:
        return 0, np.array([]), np.array([])
    if n == 1:
        return 0, np.array([1.0]), np.array([0])

    w = np.array(weights, dtype=np.float64)
    w = w / np.sum(w)  # Normalize weights

    # 1. Normalize decision matrix
    norms = np.sqrt(np.sum(objectives ** 2, axis=0))
    # Protect against zero division
    norms[norms == 0] = 1.0
    r_matrix = objectives / norms

    # 2. Weighted normalized matrix
    v_matrix = r_matrix * w

    # 3. Ideal best A* (minima since minimizing) and Anti-ideal worst A- (maxima)
    ideal_best = np.min(v_matrix, axis=0)
    ideal_worst = np.max(v_matrix, axis=0)

    # 4. Euclidean separation distances
    dist_best = np.sqrt(np.sum((v_matrix - ideal_best) ** 2, axis=1))
    dist_worst = np.sqrt(np.sum((v_matrix - ideal_worst) ** 2, axis=1))

    # 5. Closeness to ideal solution C_i = dist_worst / (dist_best + dist_worst)
    denom = dist_best + dist_worst
    denom[denom == 0] = 1e-9
    closeness = dist_worst / denom

    rankings = np.argsort(closeness)[::-1]  # Highest closeness first
    best_index = int(rankings[0])

    return best_index, closeness, rankings
