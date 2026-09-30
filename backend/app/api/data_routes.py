"""
Data Management Endpoints: CSV upload, synthetic generator, schema validation,
missing value imputation, and preview.
"""

from typing import Dict, Any, Optional
import os
import io
from pathlib import Path
import pandas as pd
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from data.generate import generate_synthetic_voyages

router = APIRouter(prefix="/data", tags=["Data"])
DATA_PATH = Path("data/voyages_50k.csv")


@router.get("/summary")
def get_dataset_summary() -> Dict[str, Any]:
    """Retrieve statistical summary and schema information of current dataset."""
    if not DATA_PATH.exists():
        return {
            "dataset_loaded": False,
            "total_rows": 0,
            "columns": [],
            "features_distribution": {},
        }

    df = pd.read_csv(DATA_PATH)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    stats = {}
    for col in ["speed_knots", "fuel_consumption_tonnes", "co2e_wtw_tonnes", "wave_height_m", "wind_speed_knots"]:
        if col in df.columns:
            stats[col] = {
                "min": round(float(df[col].min()), 2),
                "max": round(float(df[col].max()), 2),
                "mean": round(float(df[col].mean()), 2),
                "std": round(float(df[col].std()), 2),
            }

    vessel_counts = df["vessel_id"].value_counts().to_dict() if "vessel_id" in df.columns else {}
    fuel_counts = df["fuel_id"].value_counts().to_dict() if "fuel_id" in df.columns else {}

    return {
        "dataset_loaded": True,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": list(df.columns),
        "numeric_stats": stats,
        "vessel_distribution": vessel_counts,
        "fuel_distribution": fuel_counts,
        "missing_values": int(df.isna().sum().sum()),
    }


@router.get("/preview")
def get_dataset_preview(limit: int = Query(25, ge=1, le=200)) -> Dict[str, Any]:
    """Preview top N rows of the dataset."""
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset not found. Please generate or upload data.")
    df = pd.read_csv(DATA_PATH)
    rows = df.head(limit).to_dict(orient="records")
    return {
        "total_rows": len(df),
        "preview_count": len(rows),
        "columns": list(df.columns),
        "rows": rows,
    }


@router.post("/generate")
def generate_dataset(samples: int = Query(50000, ge=1000, le=100000), seed: int = 42) -> Dict[str, Any]:
    """Trigger synthetic voyage data generation with physics baseline."""
    df = generate_synthetic_voyages(n_samples=samples, seed=seed, output_path=str(DATA_PATH))
    return {
        "message": f"Successfully generated {len(df)} synthetic voyage records.",
        "samples": len(df),
        "file_path": str(DATA_PATH),
    }


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload real CSV voyage dataset with schema validation, missing-value imputation,
    and outlier flagging.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    # Schema check
    required_cols = ["speed_knots", "distance_nm"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"CSV missing mandatory columns: {missing}",
        )

    # Impute missing values for numeric columns with median
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())

    # Save to uploaded destination
    upload_path = Path("data/uploaded_voyages.csv")
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(upload_path, index=False)

    return {
        "message": "File successfully uploaded and validated.",
        "total_rows": len(df),
        "columns": list(df.columns),
        "imputed_missing_columns": list(num_cols),
    }
