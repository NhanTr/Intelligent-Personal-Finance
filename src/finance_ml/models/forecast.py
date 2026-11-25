"""F3 7-day spending forecast models (Baseline, LinearRegression, RandomForestRegressor)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from finance_ml.config import PipelineConfig
from finance_ml.evaluation.metrics import compute_forecast_metrics
from finance_ml.features.forecast_features import FORECAST_FEATURE_COLUMNS


class Last7DaysBaseline(BaseEstimator, RegressorMixin):
    """Predicts next 7-day spending as exact sum of past 7 days spending (spend_last_7d)."""

    def fit(self, X: pd.DataFrame | np.ndarray, y: Any = None) -> Last7DaysBaseline:
        self.is_fitted_ = True
        return self

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            vals = X["spend_last_7d"].to_numpy(dtype=float)
        else:
            vals = np.asarray(X, dtype=float)[:, 0]
        return np.maximum(0.0, vals)


class NonNegativePipelineRegressor(BaseEstimator, RegressorMixin):
    """Wraps a scikit-learn Pipeline so predictions are clipped at >= 0 VND."""

    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline

    def fit(self, X: pd.DataFrame | np.ndarray, y: np.ndarray) -> NonNegativePipelineRegressor:
        self.pipeline.fit(X, y)
        self.is_fitted_ = True
        return self

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        raw = self.pipeline.predict(X)
        return np.maximum(0.0, np.asarray(raw, dtype=float))


def _augment_calendar_interactions(X: pd.DataFrame | np.ndarray) -> np.ndarray:
    arr = X[list(FORECAST_FEATURE_COLUMNS)].to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
    idx_s28 = FORECAST_FEATURE_COLUMNS.index("spend_last_28d")
    idx_start = FORECAST_FEATURE_COLUMNS.index("spans_month_start")
    idx_end = FORECAST_FEATURE_COLUMNS.index("spans_month_end")
    inter_start = (arr[:, idx_s28] * arr[:, idx_start]).reshape(-1, 1)
    inter_end = (arr[:, idx_s28] * arr[:, idx_end]).reshape(-1, 1)
    return np.hstack([arr, inter_start, inter_end])


@dataclass
class ForecastSelectionOutput:
    selected_name: str
    selected_estimator: Any
    all_models: dict[str, Any]
    val_comparison: dict[str, dict[str, Any]]
    best_rf_params: dict[str, Any]
    fallback_used: bool


def build_linear_regression_model() -> NonNegativePipelineRegressor:
    pipe = Pipeline(
        [
            ("interactions", FunctionTransformer(_augment_calendar_interactions, validate=False)),
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearRegression()),
        ]
    )
    return NonNegativePipelineRegressor(pipe)


def build_rf_model(params: dict[str, Any], seed: int) -> NonNegativePipelineRegressor:
    pipe = Pipeline(
        [
            ("interactions", FunctionTransformer(_augment_calendar_interactions, validate=False)),
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=params["n_estimators"],
                    max_depth=params["max_depth"],
                    min_samples_leaf=params["min_samples_leaf"],
                    random_state=seed,
                    n_jobs=1,
                ),
            ),
        ]
    )
    return NonNegativePipelineRegressor(pipe)


def train_and_select_forecast_models(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    config: PipelineConfig,
) -> ForecastSelectionOutput:
    if train_df.empty or val_df.empty:
        raise ValueError("train_df and val_df must both be non-empty for forecast model training")

    feat_cols = list(FORECAST_FEATURE_COLUMNS)
    X_train = train_df[feat_cols]
    y_train = train_df["target_next_7d_vnd"].to_numpy(dtype=float)
    X_val = val_df[feat_cols]
    y_val = val_df["target_next_7d_vnd"].to_numpy(dtype=float)
    val_users = val_df["user_id"]

    # 1. Baseline
    baseline = Last7DaysBaseline().fit(X_train, y_train)
    b_pred = baseline.predict(X_val)
    b_metrics = compute_forecast_metrics(
        y_val,
        b_pred,
        val_users,
        baseline_mae=None,
        target_improvement_pct=config.forecast.target_improvement_pct,
    )
    b_mae = float(b_metrics["mae_vnd"])

    # 2. Linear Regression
    lr = build_linear_regression_model().fit(X_train, y_train)
    lr_pred = lr.predict(X_val)
    lr_metrics = compute_forecast_metrics(
        y_val,
        lr_pred,
        val_users,
        baseline_mae=b_mae,
        target_improvement_pct=config.forecast.target_improvement_pct,
    )

    # 3. RandomForestRegressor tuned strictly on validation
    grid = config.forecast.rf_grid
    best_rf: NonNegativePipelineRegressor | None = None
    best_rf_mae = float("inf")
    best_rf_params: dict[str, Any] = {}
    best_rf_metrics: dict[str, Any] = {}

    for n_est, m_depth, min_leaf in product(grid.n_estimators, grid.max_depth, grid.min_samples_leaf):
        cand_params = {"n_estimators": n_est, "max_depth": m_depth, "min_samples_leaf": min_leaf}
        cand_rf = build_rf_model(cand_params, seed=config.seed).fit(X_train, y_train)
        cand_pred = cand_rf.predict(X_val)
        cand_metrics = compute_forecast_metrics(
            y_val,
            cand_pred,
            val_users,
            baseline_mae=b_mae,
            target_improvement_pct=config.forecast.target_improvement_pct,
        )
        if float(cand_metrics["mae_vnd"]) < best_rf_mae:
            best_rf_mae = float(cand_metrics["mae_vnd"])
            best_rf = cand_rf
            best_rf_params = cand_params
            best_rf_metrics = cand_metrics

    assert best_rf is not None

    all_models: dict[str, Any] = {
        "baseline_last_7d": baseline,
        "linear_regression": lr,
        "random_forest": best_rf,
    }
    val_comparison = {
        "baseline_last_7d": b_metrics,
        "linear_regression": lr_metrics,
        "random_forest": best_rf_metrics,
    }

    ml_candidates = [
        ("linear_regression", float(lr_metrics["mae_vnd"])),
        ("random_forest", float(best_rf_metrics["mae_vnd"])),
    ]
    best_ml_name, best_ml_mae = min(ml_candidates, key=lambda item: item[1])

    if best_ml_mae < b_mae:
        selected_name = best_ml_name
        fallback_used = False
    else:
        selected_name = "baseline_last_7d"
        fallback_used = True

    return ForecastSelectionOutput(
        selected_name=selected_name,
        selected_estimator=all_models[selected_name],
        all_models=all_models,
        val_comparison=val_comparison,
        best_rf_params=best_rf_params,
        fallback_used=fallback_used,
    )
