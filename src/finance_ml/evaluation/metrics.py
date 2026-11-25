"""Evaluation metrics for F3 regression (VND MAE/RMSE) and F4 synthetic injection benchmark."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score


def compute_forecast_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    user_ids: pd.Series,
    baseline_mae: float | None = None,
    target_improvement_pct: float = 10.0,
) -> dict[str, Any]:
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if len(yt) == 0:
        raise ValueError("Cannot compute forecast metrics on empty arrays")

    abs_err = np.abs(yt - yp)
    sq_err = (yt - yp) ** 2
    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(sq_err)))

    u_series = pd.Series(user_ids).reset_index(drop=True)
    per_user: dict[str, dict[str, Any]] = {}
    for uid in sorted(u_series.unique()):
        mask = (u_series == uid).to_numpy()
        per_user[str(uid)] = {
            "mae_vnd": float(np.mean(abs_err[mask])),
            "rmse_vnd": float(np.sqrt(np.mean(sq_err[mask]))),
            "n_samples": int(mask.sum()),
        }

    result: dict[str, Any] = {
        "unit": "VND",
        "mae_vnd": mae,
        "rmse_vnd": rmse,
        "n_samples": int(len(yt)),
        "per_user": per_user,
    }
    if baseline_mae is not None and baseline_mae > 0.0:
        imp = float((baseline_mae - mae) / baseline_mae * 100.0)
        result["baseline_mae_vnd"] = float(baseline_mae)
        result["improvement_vs_baseline_pct"] = imp
        result["meets_10pct_target"] = bool(imp >= target_improvement_pct)
    else:
        result["improvement_vs_baseline_pct"] = None
        result["meets_10pct_target"] = None
    return result


def compute_anomaly_injection_metrics(
    y_true: np.ndarray,
    is_flagged: np.ndarray,
) -> dict[str, Any]:
    yt = np.asarray(y_true, dtype=bool)
    yp = np.asarray(is_flagged, dtype=bool)
    return {
        "evaluation_scope": "synthetic_injection_benchmark_only",
        "total_evaluated": int(len(yt)),
        "true_anomaly_count": int(yt.sum()),
        "alert_count": int(yp.sum()),
        "alert_rate": float(yp.mean()) if len(yp) > 0 else 0.0,
        "precision": float(precision_score(yt, yp, zero_division=0.0)),
        "recall": float(recall_score(yt, yp, zero_division=0.0)),
        "f1": float(f1_score(yt, yp, zero_division=0.0)),
    }
