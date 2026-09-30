"""
Quantum-Inspired Evolutionary Algorithm for Feature Selection and Hyperparameter Tuning (QIEA-FS).
Uses Q-bit chromosomes, rotation gates, and quantum mutation to discover optimal sparse feature subsets
and gradient boosting hyperparameters for vessel fuel consumption prediction.
"""

from typing import List, Dict, Any, Tuple, Optional
import math
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import HistGradientBoostingRegressor
import xgboost as xgb


class QIEAFeatureSelector:
    """
    Quantum-Inspired Evolutionary Algorithm (QIEA) for simultaneous
    feature subset selection and hyperparameter optimization.
    """

    def __init__(
        self,
        n_features: int,
        pop_size: int = 16,
        max_generations: int = 20,
        rotation_angle_step: float = 0.05 * math.pi,
        mutation_rate: float = 0.04,
        seed: int = 42,
    ):
        self.n_features = n_features
        # Hyperparameter dimensions:
        # 3 bits for max_depth [3, 4, 5, 6, 7, 8, 9, 10]
        # 3 bits for learning_rate [0.01, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3]
        # 2 bits for l2_regularization [0.0, 0.1, 1.0, 10.0]
        self.n_hp_bits = 8
        self.total_qbits = self.n_features + self.n_hp_bits

        self.pop_size = pop_size
        self.max_generations = max_generations
        self.rotation_angle_step = rotation_angle_step
        self.mutation_rate = mutation_rate
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Initialize Q-bit population in equal superposition |psi> = 1/sqrt(2)|0> + 1/sqrt(2)|1>
        # Shape: (pop_size, total_qbits, 2) where [..., 0] is alpha and [..., 1] is beta
        self.q_pop = np.full(
            (self.pop_size, self.total_qbits, 2),
            1.0 / math.sqrt(2.0),
            dtype=np.float64,
        )

        self.best_individual: Optional[np.ndarray] = None
        self.best_fitness: float = float("inf")
        self.best_params: Dict[str, Any] = {}
        self.best_selected_mask: Optional[np.ndarray] = None
        self.history: List[Dict[str, Any]] = []

    def observe(self, q_state: np.ndarray) -> np.ndarray:
        """
        Quantum measurement (collapse) of Q-bit chromosome into classical bit string.
        P(bit=1) = |beta|^2
        """
        beta_squared = q_state[:, 1] ** 2
        rand_vals = self.rng.random(self.total_qbits)
        classical = (rand_vals < beta_squared).astype(int)

        # Ensure at least 3 features are selected to avoid degeneracies
        feature_bits = classical[: self.n_features]
        if np.sum(feature_bits) < 3:
            indices = self.rng.choice(self.n_features, size=3, replace=False)
            feature_bits[indices] = 1
            classical[: self.n_features] = feature_bits

        return classical

    def decode_hyperparameters(self, hp_bits: np.ndarray) -> Dict[str, Any]:
        """Decode hyperparameter bits into concrete estimator configurations."""
        # 3 bits -> max_depth 3..10
        depth_val = hp_bits[0] * 4 + hp_bits[1] * 2 + hp_bits[2]
        max_depth = 3 + int(depth_val)

        # 3 bits -> learning rate
        lr_options = [0.02, 0.04, 0.06, 0.08, 0.10, 0.14, 0.18, 0.25]
        lr_idx = hp_bits[3] * 4 + hp_bits[4] * 2 + hp_bits[5]
        learning_rate = lr_options[int(lr_idx)]

        # 2 bits -> l2 penalty
        l2_options = [0.0, 0.05, 0.5, 2.0]
        l2_idx = hp_bits[6] * 2 + hp_bits[7]
        l2_reg = l2_options[int(l2_idx)]

        return {
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "l2_regularization": l2_reg,
            "max_iter": 120,
        }

    def apply_rotation_gate(
        self,
        q_individual: np.ndarray,
        classical_x: np.ndarray,
        best_x: np.ndarray,
        current_fitness: float,
        best_fitness: float,
    ) -> np.ndarray:
        """
        Quantum rotation gate update rule:
        [alpha']   [cos(theta)  -sin(theta)] [alpha]
        [beta' ] = [sin(theta)   cos(theta)] [beta ]
        Steers amplitudes towards the best solution while preserving normalization |a|^2 + |b|^2 = 1.
        """
        updated_q = np.copy(q_individual)

        for j in range(self.total_qbits):
            x_j = classical_x[j]
            b_j = best_x[j]

            # Determine rotation direction delta_theta
            if current_fitness > best_fitness:
                # Steer towards best_x[j]
                if x_j == 0 and b_j == 1:
                    d_theta = self.rotation_angle_step
                elif x_j == 1 and b_j == 0:
                    d_theta = -self.rotation_angle_step
                else:
                    d_theta = 0.0
            else:
                d_theta = 0.0

            if d_theta != 0.0:
                alpha = updated_q[j, 0]
                beta = updated_q[j, 1]

                # Sign adjustment based on quadrants
                if alpha * beta < 0:
                    d_theta = -d_theta

                cos_t = math.cos(d_theta)
                sin_t = math.sin(d_theta)

                new_alpha = cos_t * alpha - sin_t * beta
                new_beta = sin_t * alpha + cos_t * beta

                # Re-normalize to prevent numerical drift
                norm = math.sqrt(new_alpha ** 2 + new_beta ** 2)
                updated_q[j, 0] = new_alpha / norm
                updated_q[j, 1] = new_beta / norm

        return updated_q

    def quantum_mutation(self, q_individual: np.ndarray) -> np.ndarray:
        """Apply quantum NOT gate with probability mutation_rate for exploration."""
        mutated = np.copy(q_individual)
        for j in range(self.total_qbits):
            if self.rng.random() < self.mutation_rate:
                # Swap alpha and beta (Quantum NOT gate X = [[0, 1], [1, 0]])
                mutated[j, 0], mutated[j, 1] = mutated[j, 1], mutated[j, 0]
        return mutated

    def evaluate_fitness(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_mask: np.ndarray,
        hp_params: Dict[str, Any],
        cv_splits: int = 3,
    ) -> float:
        """
        Evaluate CV RMSE with parsimony penalty for feature count.
        """
        selected_cols = np.where(feature_mask == 1)[0]
        if len(selected_cols) == 0:
            return float("inf")

        X_sub = X[:, selected_cols]
        kf = KFold(n_splits=cv_splits, shuffle=True, random_state=self.seed)
        fold_rmses = []

        for train_idx, val_idx in kf.split(X_sub):
            X_tr, X_val = X_sub[train_idx], X_sub[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]

            model = HistGradientBoostingRegressor(
                max_depth=hp_params["max_depth"],
                learning_rate=hp_params["learning_rate"],
                l2_regularization=hp_params["l2_regularization"],
                max_iter=hp_params["max_iter"],
                random_state=self.seed,
            )
            model.fit(X_tr, y_tr)
            preds = model.predict(X_val)
            rmse = math.sqrt(mean_squared_error(y_val, preds))
            fold_rmses.append(rmse)

        mean_rmse = float(np.mean(fold_rmses))
        # Small sparsity regularization reward: encourage fewer active sensors
        sparsity_penalty = 0.002 * (len(selected_cols) / self.n_features)
        return mean_rmse + sparsity_penalty

    def search(
        self, X: np.ndarray, y: np.ndarray, feature_names: List[str]
    ) -> Dict[str, Any]:
        """
        Run the QIEA search loop over generations.
        """
        print(f"Starting QIEA-FS on {self.n_features} features across {self.max_generations} generations...")
        
        classical_pop = np.zeros((self.pop_size, self.total_qbits), dtype=int)
        fitnesses = np.full(self.pop_size, float("inf"))

        for gen in range(self.max_generations):
            gen_best_fitness = float("inf")

            for i in range(self.pop_size):
                # 1. Observe Q-state
                classical_pop[i] = self.observe(self.q_pop[i])
                feat_mask = classical_pop[i, : self.n_features]
                hp_bits = classical_pop[i, self.n_features :]
                hp_params = self.decode_hyperparameters(hp_bits)

                # 2. Evaluate fitness
                fit = self.evaluate_fitness(X, y, feat_mask, hp_params)
                fitnesses[i] = fit

                if fit < gen_best_fitness:
                    gen_best_fitness = fit

                if fit < self.best_fitness:
                    self.best_fitness = fit
                    self.best_individual = np.copy(classical_pop[i])
                    self.best_selected_mask = np.copy(feat_mask)
                    self.best_params = hp_params

            # 3. Update Q-bits with rotation gates and quantum mutation
            for i in range(self.pop_size):
                self.q_pop[i] = self.apply_rotation_gate(
                    self.q_pop[i],
                    classical_pop[i],
                    self.best_individual,
                    fitnesses[i],
                    self.best_fitness,
                )
                self.q_pop[i] = self.quantum_mutation(self.q_pop[i])

            active_feat_count = int(np.sum(self.best_selected_mask))
            self.history.append({
                "generation": gen + 1,
                "best_cv_rmse": round(self.best_fitness, 4),
                "active_features_count": active_feat_count,
            })
            print(f"Gen {gen + 1}/{self.max_generations}: Best CV RMSE = {self.best_fitness:.4f}, Features = {active_feat_count}")

        # Train final estimator on full dataset with selected features and tuned params
        selected_indices = np.where(self.best_selected_mask == 1)[0]
        selected_feature_names = [feature_names[idx] for idx in selected_indices]
        
        X_selected = X[:, selected_indices]
        final_model = xgb.XGBRegressor(
            max_depth=self.best_params["max_depth"],
            learning_rate=self.best_params["learning_rate"],
            reg_lambda=self.best_params["l2_regularization"],
            n_estimators=self.best_params["max_iter"],
            random_state=self.seed,
            n_jobs=-1,
        )
        final_model.fit(X_selected, y)

        return {
            "model": final_model,
            "selected_indices": selected_indices.tolist(),
            "selected_features": selected_feature_names,
            "best_params": self.best_params,
            "best_cv_rmse": self.best_fitness,
            "history": self.history,
        }
