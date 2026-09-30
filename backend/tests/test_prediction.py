"""
Unit tests for QIEA feature selector, Simulated VQC regressor, and evaluation metrics.
"""

import numpy as np
import pytest
from backend.app.prediction.vqc_regressor import SimulatedVQCRegressor
from backend.app.prediction.evaluator import calculate_metrics, predict_with_confidence_interval
from backend.app.prediction.qiea_fs import QIEAFeatureSelector


def test_vqc_regressor_fit_predict():
    """Verify simulated variational quantum circuit runs, trains, and outputs finite predictions."""
    rng = np.random.default_rng(42)
    X = rng.normal(size=(50, 8))
    # Simple non-linear relation
    y = 2.0 * X[:, 0] - 1.5 * (X[:, 1] ** 2) + rng.normal(0, 0.1, size=50)

    vqc = SimulatedVQCRegressor(n_qubits=4, n_layers=2, max_iter=25, seed=42)
    vqc.fit(X, y)
    preds = vqc.predict(X)

    assert len(preds) == len(y)
    assert not np.isnan(preds).any()
    metrics = calculate_metrics(y, preds)
    assert metrics["rmse"] >= 0.0


def test_qiea_rotation_gate_normalization():
    """Verify that QIEA Q-bit amplitude normalization |alpha|^2 + |beta|^2 = 1 is preserved."""
    qiea = QIEAFeatureSelector(n_features=6, pop_size=4, max_generations=2, seed=42)
    individual = qiea.q_pop[0]
    
    classical_x = np.ones(qiea.total_qbits, dtype=int)
    best_x = np.zeros(qiea.total_qbits, dtype=int)
    
    updated = qiea.apply_rotation_gate(individual, classical_x, best_x, current_fitness=10.0, best_fitness=5.0)
    
    for j in range(qiea.total_qbits):
        alpha, beta = updated[j, 0], updated[j, 1]
        norm_sq = alpha**2 + beta**2
        assert pytest.approx(norm_sq, abs=1e-5) == 1.0


def test_confidence_interval():
    """Verify confidence interval bounds around point prediction."""
    res = predict_with_confidence_interval(predicted_value=100.0, model_rmse=5.0, confidence_level=0.95)
    assert res["predicted_value"] == 100.0
    assert res["ci_lower"] < 100.0
    assert res["ci_upper"] > 100.0
    assert round(res["ci_upper"] - 100.0, 1) == round(100.0 - res["ci_lower"], 1)
