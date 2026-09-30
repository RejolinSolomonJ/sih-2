"""
Model Registry: versioned storage, serialization, metadata tracking,
and active model loading for GreenFleet Q prediction services.
"""

from typing import Dict, Any, List, Optional
import os
import json
import joblib
from pathlib import Path

REGISTRY_DIR = Path("backend/artifacts/models")
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
METADATA_FILE = REGISTRY_DIR / "metadata.json"


class ModelRegistry:
    """Manages trained fuel prediction models, versions, and metadata."""

    @classmethod
    def _load_meta_dict(cls) -> Dict[str, Any]:
        if METADATA_FILE.exists():
            try:
                with open(METADATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_meta_dict(cls, data: Dict[str, Any]):
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def save_model(
        cls,
        model_id: str,
        model_obj: Any,
        pipeline: Any,
        metrics: Dict[str, Any],
        model_type: str,
        feature_names: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Save trained model artifacts and write to registry metadata."""
        model_path = REGISTRY_DIR / f"{model_id}.joblib"
        pipeline_path = REGISTRY_DIR / f"{model_id}_pipeline.joblib"

        joblib.dump(model_obj, model_path)
        joblib.dump(pipeline, pipeline_path)

        meta = cls._load_meta_dict()
        record = {
            "model_id": model_id,
            "model_type": model_type,
            "created_at": time_now_iso(),
            "metrics": metrics,
            "feature_names": feature_names,
            "parameters": parameters or {},
            "notes": notes,
            "model_path": str(model_path),
            "pipeline_path": str(pipeline_path),
            "is_active": len(meta) == 0, # First model active by default
        }
        meta[model_id] = record
        cls._save_meta_dict(meta)
        return record

    @classmethod
    def get_model(cls, model_id: str) -> Optional[Dict[str, Any]]:
        """Load model object and pipeline from registry."""
        meta = cls._load_meta_dict()
        if model_id not in meta:
            return None
        info = meta[model_id]
        model_path = Path(info["model_path"])
        pipeline_path = Path(info["pipeline_path"])
        if not model_path.exists() or not pipeline_path.exists():
            return None
        model_obj = joblib.load(model_path)
        pipeline = joblib.load(pipeline_path)
        return {
            "info": info,
            "model": model_obj,
            "pipeline": pipeline,
        }

    @classmethod
    def get_active_model(cls) -> Optional[Dict[str, Any]]:
        """Retrieve current active production model."""
        meta = cls._load_meta_dict()
        for m_id, m_data in meta.items():
            if m_data.get("is_active"):
                return cls.get_model(m_id)
        if meta:
            # Fallback to first available
            first_id = list(meta.keys())[0]
            return cls.get_model(first_id)
        return None

    @classmethod
    def set_active_model(cls, model_id: str) -> bool:
        """Mark a model as the active surrogate evaluator."""
        meta = cls._load_meta_dict()
        if model_id not in meta:
            return False
        for k in meta:
            meta[k]["is_active"] = (k == model_id)
        cls._save_meta_dict(meta)
        return True

    @classmethod
    def list_models(cls) -> List[Dict[str, Any]]:
        """List summary of all registered models."""
        meta = cls._load_meta_dict()
        return list(meta.values())


def time_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
