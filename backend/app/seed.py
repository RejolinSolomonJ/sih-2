"""
Database, Model Registry, and Demo State Seeder for GreenFleet Q.
Initializes trained quantum-inspired prediction models, baseline models,
and executes an initial benchmark run for immediate out-of-the-box demonstration.
"""

import sys
import time
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np

from backend.app.prediction.preprocessing import MarineDataPipeline
from backend.app.prediction.qiea_fs import QIEAFeatureSelector
from backend.app.prediction.vqc_regressor import SimulatedVQCRegressor
from backend.app.prediction.baselines import get_baseline_models
from backend.app.prediction.evaluator import calculate_metrics
from backend.app.prediction.model_registry import ModelRegistry
from backend.app.services.job_manager import JobManager


def seed_all():
    print("=== Seeding GreenFleet Q Platform ===")
    data_file = ROOT / "data/voyages_50k.csv"
    if not data_file.exists():
        from data.generate import generate_synthetic_voyages
        generate_synthetic_voyages(5000, output_path=str(data_file))

    df = pd.read_csv(data_file)
    print(f"Loaded {len(df)} records from dataset.")

    # Subsample 1500 for ultra-fast seed
    df_sub = df.sample(n=1500, random_state=42).reset_index(drop=True)
    pipeline = MarineDataPipeline()
    X, y = pipeline.fit_transform(df_sub)

    # 1. Train QIEA + XGBoost
    print("Training QIEA-XGBoost model...")
    t0 = time.time()
    selector = QIEAFeatureSelector(n_features=X.shape[1], pop_size=8, max_generations=5, seed=42)
    search_res = selector.search(X, y, pipeline.feature_names_out)
    qiea_model = search_res["model"]
    sel_idx = search_res["selected_indices"]
    preds = qiea_model.predict(X[:, sel_idx])
    y_orig = pipeline.inverse_transform_target(y)
    p_orig = pipeline.inverse_transform_target(preds)
    metrics_qiea = calculate_metrics(y_orig, p_orig, training_time_sec=time.time() - t0)

    ModelRegistry.save_model(
        model_id="qiea_xgboost_v1",
        model_obj=qiea_model,
        pipeline=pipeline,
        metrics=metrics_qiea,
        model_type="Quantum-Inspired Evolutionary Feature Selection + XGBoost",
        feature_names=search_res["selected_features"],
        parameters={"selected_indices": sel_idx, "hyperparameters": search_res["best_params"]},
        notes="Primary surrogate model with Q-bit rotation gate feature selection",
    )
    ModelRegistry.set_active_model("qiea_xgboost_v1")
    print(f"QIEA-XGBoost registered (RMSE: {metrics_qiea['rmse']:.3f}, R2: {metrics_qiea['r2']:.3f})")

    # 2. Train Simulated VQC
    print("Training Simulated Variational Quantum Circuit (VQC)...")
    t0 = time.time()
    vqc = SimulatedVQCRegressor(n_qubits=4, n_layers=2, max_iter=20, seed=42)
    vqc.fit(X, y)
    preds_vqc = vqc.predict(X)
    p_vqc_orig = pipeline.inverse_transform_target(preds_vqc)
    metrics_vqc = calculate_metrics(y_orig, p_vqc_orig, training_time_sec=time.time() - t0)

    ModelRegistry.save_model(
        model_id="simulated_vqc_v1",
        model_obj=vqc,
        pipeline=pipeline,
        metrics=metrics_vqc,
        model_type=SimulatedVQCRegressor.LABEL,
        feature_names=pipeline.feature_names_out,
        parameters={"n_qubits": 4, "n_layers": 2},
        notes="Angle encoding on PCA components with circular CNOT entanglement",
    )
    print(f"Simulated VQC registered (RMSE: {metrics_vqc['rmse']:.3f}, R2: {metrics_vqc['r2']:.3f})")

    # 3. Train Baselines: XGBoost and Ridge
    print("Training classical baselines...")
    baselines = get_baseline_models(seed=42)
    for b_name in ["xgboost_baseline", "ridge", "random_forest"]:
        m = baselines[b_name]
        t0 = time.time()
        m.fit(X, y)
        p_b = pipeline.inverse_transform_target(m.predict(X))
        m_b = calculate_metrics(y_orig, p_b, training_time_sec=time.time() - t0)
        ModelRegistry.save_model(
            model_id=f"{b_name}_v1",
            model_obj=m,
            pipeline=pipeline,
            metrics=m_b,
            model_type=f"Baseline: {b_name.replace('_', ' ').title()}",
            feature_names=pipeline.feature_names_out,
            notes=f"Standard benchmark model {b_name}",
        )
        print(f"{b_name} registered (RMSE: {m_b['rmse']:.3f}, R2: {m_b['r2']:.3f})")

    # 4. Trigger initial sample fleet optimization run
    print("Triggering initial sample fleet optimization job...")
    job_id = JobManager.create_job({
        "algorithm": "QIEA-NSGA",
        "population_size": 16,
        "generations": 12,
        "carbon_price_usd": 85.0,
        "use_surrogate": True,
        "seed": 42,
    })
    JobManager._run_worker(job_id)
    print(f"Initial optimization job {job_id} completed successfully!")
    print("=== Seeding Complete! ===")


if __name__ == "__main__":
    seed_all()
