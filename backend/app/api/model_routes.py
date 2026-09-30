"""
Machine Learning and Quantum-Inspired Prediction Routes:
Training, inference, model comparison, and explainability.
"""

from typing import Dict, Any, List, Optional
import time
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.prediction import (
    TrainModelRequest,
    SinglePredictionRequest,
    PredictionResponse,
    FeatureAttribution,
)
from backend.app.prediction.preprocessing import MarineDataPipeline
from backend.app.prediction.qiea_fs import QIEAFeatureSelector
from backend.app.prediction.vqc_regressor import SimulatedVQCRegressor
from backend.app.prediction.baselines import get_baseline_models
from backend.app.prediction.evaluator import (
    calculate_metrics,
    compute_residuals_and_scatter,
    explain_prediction,
    predict_with_confidence_interval,
)
from backend.app.prediction.model_registry import ModelRegistry
from backend.app.core.physics import MarinePhysicsEngine
import yaml

router = APIRouter(prefix="/models", tags=["Prediction"])
DATA_PATH = Path("data/voyages_50k.csv")
CONFIG_DIR = Path("config")


def _get_dataset(limit: int = 5000) -> pd.DataFrame:
    if not DATA_PATH.exists():
        from data.generate import generate_synthetic_voyages
        generate_synthetic_voyages(n_samples=5000, output_path=str(DATA_PATH))
    df = pd.read_csv(DATA_PATH)
    if len(df) > limit:
        df = df.sample(n=limit, random_state=42).reset_index(drop=True)
    return df


@router.post("/train")
def train_model(req: TrainModelRequest) -> Dict[str, Any]:
    """Train a selected model architecture (QIEA-XGBoost, Simulated VQC, or Baselines)."""
    df = _get_dataset(limit=req.samples_limit or 5000)
    pipeline = MarineDataPipeline()
    X, y = pipeline.fit_transform(df)

    start_time = time.time()
    model_type = req.model_type.lower()
    model_id = f"{model_type}_{int(time.time())}"

    if model_type in ["qiea_xgboost", "qiea_fs"]:
        # Run Quantum-Inspired Evolutionary Feature Selection
        selector = QIEAFeatureSelector(
            n_features=X.shape[1],
            pop_size=req.qiea_pop_size or 12,
            max_generations=req.qiea_generations or 15,
            seed=req.seed,
        )
        search_res = selector.search(X, y, pipeline.feature_names_out)
        model = search_res["model"]
        selected_idx = search_res["selected_indices"]
        selected_features = search_res["selected_features"]

        preds = model.predict(X[:, selected_idx])
        y_orig = pipeline.inverse_transform_target(y)
        preds_orig = pipeline.inverse_transform_target(preds)

        duration = time.time() - start_time
        metrics = calculate_metrics(y_orig, preds_orig, training_time_sec=duration)
        plots = compute_residuals_and_scatter(y_orig, preds_orig)

        saved = ModelRegistry.save_model(
            model_id=model_id,
            model_obj=model,
            pipeline=pipeline,
            metrics=metrics,
            model_type="Quantum-Inspired Evolutionary Feature Selection + Gradient Boosting",
            feature_names=selected_features,
            parameters={
                "selected_indices": selected_idx,
                "hyperparameters": search_res["best_params"],
                "qiea_history": search_res["history"],
            },
            notes="Q-bit rotation-gate evolutionary feature selection with XGBoost",
        )

        return {
            "model_id": model_id,
            "status": "TRAINED",
            "metrics": metrics,
            "selected_features": selected_features,
            "plots": plots,
            "qiea_convergence": search_res["history"],
        }

    elif model_type in ["simulated_vqc", "vqc"]:
        # Simulated Variational Quantum Circuit Regressor
        vqc = SimulatedVQCRegressor(n_qubits=4, n_layers=2, max_iter=40, seed=req.seed)
        vqc.fit(X, y)
        preds = vqc.predict(X)
        y_orig = pipeline.inverse_transform_target(y)
        preds_orig = pipeline.inverse_transform_target(preds)

        duration = time.time() - start_time
        metrics = calculate_metrics(y_orig, preds_orig, training_time_sec=duration)
        plots = compute_residuals_and_scatter(y_orig, preds_orig)

        saved = ModelRegistry.save_model(
            model_id=model_id,
            model_obj=vqc,
            pipeline=pipeline,
            metrics=metrics,
            model_type=SimulatedVQCRegressor.LABEL,
            feature_names=pipeline.feature_names_out,
            parameters={"n_qubits": 4, "n_layers": 2},
            notes="Simulated Variational Quantum Circuit with angle encoding and Pauli-Z measurement",
        )

        return {
            "model_id": model_id,
            "status": "TRAINED",
            "metrics": metrics,
            "plots": plots,
        }

    else:
        # Classical Baselines
        baselines = get_baseline_models(seed=req.seed)
        key = "xgboost_baseline" if "xgb" in model_type else ("ridge" if "ridge" in model_type else ("mlp" if "mlp" in model_type else "random_forest"))
        est = baselines[key]
        est.fit(X, y)

        preds = est.predict(X)
        y_orig = pipeline.inverse_transform_target(y)
        preds_orig = pipeline.inverse_transform_target(preds)

        duration = time.time() - start_time
        metrics = calculate_metrics(y_orig, preds_orig, training_time_sec=duration)
        plots = compute_residuals_and_scatter(y_orig, preds_orig)

        saved = ModelRegistry.save_model(
            model_id=model_id,
            model_obj=est,
            pipeline=pipeline,
            metrics=metrics,
            model_type=f"Baseline: {key.upper()}",
            feature_names=pipeline.feature_names_out,
            notes=f"Classical benchmark model {key}",
        )

        return {
            "model_id": model_id,
            "status": "TRAINED",
            "metrics": metrics,
            "plots": plots,
        }


@router.get("")
def list_models() -> List[Dict[str, Any]]:
    """List all registered models with their performance metrics."""
    return ModelRegistry.list_models()


@router.post("/{model_id}/activate")
def activate_model(model_id: str) -> Dict[str, Any]:
    """Designate this model as the active surrogate evaluator for fleet optimization."""
    ok = ModelRegistry.set_active_model(model_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found.")
    return {"status": "SUCCESS", "active_model_id": model_id}


@router.post("/predict")
def predict_single(req: SinglePredictionRequest, model_id: Optional[str] = None) -> PredictionResponse:
    """
    Generate fuel consumption prediction with confidence intervals,
    physics comparison, and SHAP-style local feature attributions.
    """
    # Load model
    if model_id:
        record = ModelRegistry.get_model(model_id)
    else:
        record = ModelRegistry.get_active_model()

    # Load vessel and fuel config for physics comparison
    with open(CONFIG_DIR / "vessels.yaml", "r", encoding="utf-8") as f:
        vessels = yaml.safe_load(f)["vessels"]
    with open(CONFIG_DIR / "fuels.yaml", "r", encoding="utf-8") as f:
        fuels = yaml.safe_load(f)["fuels"]

    vessel = next((v for v in vessels if v["id"] == req.vessel_id), vessels[0])
    fuel = next((f for f in fuels if f["id"] == req.fuel_id), fuels[0])

    phys = MarinePhysicsEngine.calculate_power_and_fuel(
        vessel_config=vessel,
        fuel_config=fuel,
        speed_knots=req.speed_knots,
        cargo_load_ratio=req.cargo_load_ratio,
        wave_height_m=req.wave_height_m,
        wind_speed_knots=req.wind_speed_knots,
        wind_direction_deg=req.wind_direction_deg,
        current_knots=req.current_knots,
        fouling_index=req.fouling_index,
        distance_nm=req.distance_nm,
    )

    if record:
        model = record["model"]
        pipeline = record["pipeline"]
        info = record["info"]
        m_id = info["model_id"]
        m_type = info["model_type"]
        rmse = info["metrics"].get("rmse", 2.5)

        # Build feature dataframe
        input_data = pd.DataFrame([{
            "speed_knots": req.speed_knots,
            "speed_stw_knots": req.speed_stw_knots or req.speed_knots,
            "draft_m": req.draft_m,
            "cargo_load_ratio": req.cargo_load_ratio,
            "cargo_tonnes": req.cargo_tonnes or 40000.0,
            "wave_height_m": req.wave_height_m,
            "wind_speed_knots": req.wind_speed_knots,
            "wind_direction_deg": req.wind_direction_deg,
            "current_knots": req.current_knots,
            "fouling_index": req.fouling_index,
            "distance_nm": req.distance_nm,
            "engine_load_fraction": req.engine_load_fraction or 0.75,
            "sfoc_g_per_kwh": req.sfoc_g_per_kwh or 175.0,
            "added_resistance_wind_kw": req.added_resistance_wind_kw or 100.0,
            "added_resistance_wave_kw": req.added_resistance_wave_kw or 200.0,
            "added_resistance_fouling_kw": req.added_resistance_fouling_kw or 50.0,
            "vessel_id": req.vessel_id,
            "fuel_id": req.fuel_id,
        }])

        X_transformed = pipeline.transform(input_data)
        
        # Check if QIEA feature selection mask exists
        params = info.get("parameters", {})
        if "selected_indices" in params:
            sel_idx = params["selected_indices"]
            X_eval = X_transformed[:, sel_idx]
            feature_names = info.get("feature_names", pipeline.feature_names_out)
        else:
            X_eval = X_transformed
            feature_names = pipeline.feature_names_out

        pred_scaled = model.predict(X_eval)
        pred_val = float(pipeline.inverse_transform_target(pred_scaled)[0])
        # Protect against non-physical negative predictions
        pred_val = max(0.5, pred_val)

        # Baseline vector for explanation
        baseline_vec = np.zeros(X_eval.shape[1])
        attributions = explain_prediction(
            model=model,
            feature_names=feature_names,
            sample_vector=X_eval[0],
            baseline_vector=baseline_vec,
            predicted_val=pred_val,
        )
    else:
        # Fallback to physics engine
        m_id = "physics_baseline"
        m_type = "Naval Architecture Hydrodynamic Baseline"
        pred_val = phys["total_fuel_tonnes"]
        rmse = 2.1
        attributions = [
            {"feature": "speed_knots", "value": req.speed_knots, "attribution": round(pred_val * 0.55, 2), "abs_impact": round(pred_val * 0.55, 2)},
            {"feature": "distance_nm", "value": req.distance_nm, "attribution": round(pred_val * 0.25, 2), "abs_impact": round(pred_val * 0.25, 2)},
            {"feature": "cargo_load_ratio", "value": req.cargo_load_ratio, "attribution": round(pred_val * 0.12, 2), "abs_impact": round(pred_val * 0.12, 2)},
            {"feature": "wave_height_m", "value": req.wave_height_m, "attribution": round(pred_val * 0.08, 2), "abs_impact": round(pred_val * 0.08, 2)},
        ]

    ci = predict_with_confidence_interval(pred_val, model_rmse=rmse, confidence_level=req.confidence_level)
    co2e_wtw = pred_val * fuel["emission_factor_wtw"]
    fuel_cost = pred_val * fuel["cost_per_tonne_usd"]

    return PredictionResponse(
        model_id=m_id,
        model_type=m_type,
        predicted_fuel_tonnes=ci["predicted_value"],
        ci_lower=ci["ci_lower"],
        ci_upper=ci["ci_upper"],
        ci_level=ci["ci_level"],
        standard_error=ci["standard_error"],
        predicted_co2e_wtw_tonnes=round(co2e_wtw, 3),
        estimated_fuel_cost_usd=round(fuel_cost, 2),
        physics_baseline_comparison=phys,
        feature_attributions=[FeatureAttribution(**a) for a in attributions[:8]],
    )


@router.get("/compare")
def compare_models() -> Dict[str, Any]:
    """Compare all registered models across RMSE, MAE, R2, MAPE, and training duration."""
    models = ModelRegistry.list_models()
    if not models:
        # Train default models for benchmark comparison
        return {
            "comparison_table": [],
            "message": "No trained models found. Trigger a training run to generate comparison.",
        }

    table = []
    for m in models:
        metrics = m.get("metrics", {})
        table.append({
            "model_id": m["model_id"],
            "model_type": m["model_type"],
            "is_active": m.get("is_active", False),
            "rmse": metrics.get("rmse", 0.0),
            "mae": metrics.get("mae", 0.0),
            "r2": metrics.get("r2", 0.0),
            "mape_pct": metrics.get("mape_pct", 0.0),
            "training_time_sec": metrics.get("training_time_sec", 0.0),
        })

    return {"comparison_table": table}
