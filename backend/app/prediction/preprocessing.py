"""
Data preprocessing, encoding, and scaling pipelines for marine fuel consumption prediction.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer


FEATURE_COLUMNS_NUMERIC = [
    "speed_knots",
    "speed_stw_knots",
    "draft_m",
    "cargo_load_ratio",
    "cargo_tonnes",
    "wave_height_m",
    "wind_speed_knots",
    "wind_direction_deg",
    "current_knots",
    "fouling_index",
    "distance_nm",
    "engine_load_fraction",
    "sfoc_g_per_kwh",
    "added_resistance_wind_kw",
    "added_resistance_wave_kw",
    "added_resistance_fouling_kw",
]

FEATURE_COLUMNS_CATEGORICAL = [
    "vessel_id",
    "fuel_id",
]

TARGET_COLUMN = "fuel_consumption_tonnes"


class MarineDataPipeline:
    """Handles feature extraction, scaling, one-hot encoding, and inverse transforms."""

    def __init__(self, selected_numeric_features: Optional[List[str]] = None):
        self.numeric_features = selected_numeric_features or FEATURE_COLUMNS_NUMERIC
        self.categorical_features = FEATURE_COLUMNS_CATEGORICAL
        self.preprocessor: Optional[ColumnTransformer] = None
        self.feature_names_out: List[str] = []
        self.target_scaler = StandardScaler()

    def fit_transform(
        self, df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        # Filter available features
        num_cols = [c for c in self.numeric_features if c in df.columns]
        cat_cols = [c for c in self.categorical_features if c in df.columns]

        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), num_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
            ]
        )

        X = self.preprocessor.fit_transform(df[num_cols + cat_cols])
        
        # Build feature names
        num_names = num_cols
        cat_encoder = self.preprocessor.named_transformers_["cat"]
        if hasattr(cat_encoder, "get_feature_names_out"):
            cat_names = list(cat_encoder.get_feature_names_out(cat_cols))
        else:
            cat_names = [f"cat_{i}" for i in range(X.shape[1] - len(num_cols))]
        self.feature_names_out = num_names + cat_names

        y = df[TARGET_COLUMN].to_numpy().reshape(-1, 1)
        y_scaled = self.target_scaler.fit_transform(y).ravel()
        return X, y_scaled

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if self.preprocessor is None:
            raise ValueError("Pipeline has not been fitted yet.")
        num_cols = [c for c in self.numeric_features if c in df.columns]
        cat_cols = [c for c in self.categorical_features if c in df.columns]
        return self.preprocessor.transform(df[num_cols + cat_cols])

    def inverse_transform_target(self, y_scaled: np.ndarray) -> np.ndarray:
        if y_scaled.ndim == 1:
            y_scaled = y_scaled.reshape(-1, 1)
        return self.target_scaler.inverse_transform(y_scaled).ravel()
