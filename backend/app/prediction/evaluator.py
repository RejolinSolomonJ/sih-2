"""
Evaluation metrics, explanation generator (SHAP-style attributions),
confidence interval estimation, and residual analysis.
"""

from typing import Dict, Any, List, Optional
import time
import math
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def calculate_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, training_time_sec: float = 0.0
) -> Dict[str, float]:
    """Calculate standard regression metrics: RMSE, MAE, R2, MAPE, and training duration."""
    rmse = float(math.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))

    # MAPE with epsilon protection for near-zero division
    epsilon = 1e-4
    mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), epsilon))) * 100.0)

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "r2": round(r2, 4),
        "mape_pct": round(mape, 2),
        "training_time_sec": round(training_time_sec, 3),
    }


def compute_residuals_and_scatter(
    y_true: np.ndarray, y_pred: np.ndarray, max_points: int = 150
) -> Dict[str, Any]:
    """Generate downsampled data points for scatter and residual plots."""
    n = len(y_true)
    if n > max_points:
        indices = np.linspace(0, n - 1, max_points, dtype=int)
    else:
        indices = np.arange(n)

    scatter_points = [
        {"actual": round(float(y_true[i]), 2), "predicted": round(float(y_pred[i]), 2)}
        for i in indices
    ]

    residuals = [
        {
            "predicted": round(float(y_pred[i]), 2),
            "residual": round(float(y_true[i] - y_pred[i]), 2),
        }
        for i in indices
    ]

    return {
        "scatter_points": scatter_points,
        "residuals": residuals,
    }


def explain_prediction(
    model: Any,
    feature_names: List[str],
    sample_vector: np.ndarray,
    baseline_vector: np.ndarray,
    predicted_val: float,
) -> List[Dict[str, Any]]:
    """
    Compute SHAP-style local marginal feature attributions using marginal perturbation.
    Delta_y_i represents the influence of feature i shifting from baseline to current sample.
    """
    attributions = []
    
    # Feature perturbation attribution
    base_pred = predicted_val
    n_feats = len(feature_names)
    
    # Check if tree model with feature_importances_
    global_importances = getattr(model, "feature_importances_", None)
    
    for i in range(min(n_feats, sample_vector.shape[0])):
        feat_name = feature_names[i]
        val = float(sample_vector[i])
        
        # Perturbed vector replacing feature with baseline
        perturbed = np.copy(sample_vector).reshape(1, -1)
        perturbed[0, i] = baseline_vector[i] if i < len(baseline_vector) else 0.0
        
        try:
            pred_perturbed = float(model.predict(perturbed)[0])
            contrib = base_pred - pred_perturbed
        except Exception:
            # Fallback to normalized tree importance if model prediction fails
            if global_importances is not None and i < len(global_importances):
                contrib = float(global_importances[i] * (val - baseline_vector[i]))
            else:
                contrib = 0.0

        attributions.append({
            "feature": feat_name,
            "value": round(val, 3),
            "attribution": round(contrib, 3),
            "abs_impact": round(abs(contrib), 3),
        })

    # Sort descending by absolute impact
    attributions.sort(key=lambda x: x["abs_impact"], reverse=True)
    return attributions


def predict_with_confidence_interval(
    predicted_value: float,
    model_rmse: float,
    confidence_level: float = 0.95,
) -> Dict[str, float]:
    """
    Calculate confidence intervals using residual standard error.
    For 95% CI, z ~ 1.96.
    """
    z_map = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
    z = z_map.get(confidence_level, 1.960)

    margin = z * model_rmse
    lower_bound = max(0.0, predicted_value - margin)
    upper_bound = predicted_value + margin

    return {
        "predicted_value": round(predicted_value, 3),
        "ci_lower": round(lower_bound, 3),
        "ci_upper": round(upper_bound, 3),
        "ci_level": confidence_level,
        "standard_error": round(model_rmse, 3),
    }
