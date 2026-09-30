"""
Classical machine learning baseline models for fuel consumption prediction:
- Linear / Ridge Regression
- Random Forest Regressor
- XGBoost Regressor
- Multi-Layer Perceptron (MLP) Regressor
"""

from typing import Dict, Any
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
import xgboost as xgb


def get_baseline_models(seed: int = 42) -> Dict[str, Any]:
    """Returns initialized standard baseline regressors for benchmarking."""
    return {
        "ridge": Ridge(alpha=1.0, random_state=seed),
        "random_forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_leaf=3,
            random_state=seed,
            n_jobs=-1,
        ),
        "xgboost_baseline": xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.08,
            random_state=seed,
            n_jobs=-1,
        ),
        "mlp": MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            max_iter=200,
            alpha=0.01,
            random_state=seed,
            early_stopping=True,
        ),
    }
