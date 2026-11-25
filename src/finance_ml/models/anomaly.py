"""F4 Isolation Forest anomaly detector with validation thresholding and Vietnamese reasons."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from finance_ml.config import PipelineConfig
from finance_ml.features.anomaly_features import (
    AnomalyFeatureFitState,
    fit_anomaly_feature_state,
    transform_anomaly_features,
)


@dataclass
class TrainedAnomalyDetector:
    feature_state: AnomalyFeatureFitState
    isolation_forest: IsolationForest
    threshold: float
    validation_alert_rate: float


def _build_reasons(row: pd.Series, score: float, threshold: float) -> list[str]:
    reasons: list[str] = []
    u_ratio = float(row["user_amount_ratio"])
    c_ratio = float(row["user_cat_amount_ratio"])
    f24 = float(row["tx_freq_24h"])
    cat = str(row["category"])
    amt = float(row["amount_vnd"])

    if u_ratio >= 2.5:
        reasons.append(f"Số tiền gấp {u_ratio:.1f} lần mức chi tiêu trung vị lịch sử của bạn")
    if c_ratio >= 2.5:
        reasons.append(f"Cao gấp {c_ratio:.1f} lần mức thường chi cho danh mục '{cat}'")
    if f24 >= 4.0:
        reasons.append(f"Tần suất giao dịch dày bất thường ({int(f24) + 1} giao dịch trong 24 giờ qua)")

    if not reasons:
        reasons.append(
            f"Tổ hợp mức chi ({amt:,.0f} VND), thời điểm và danh mục '{cat}' lệch khỏi nền lịch sử "
            f"(điểm {score:.3f} >= ngưỡng {threshold:.3f})"
        )
    return reasons[:3]


def train_anomaly_detector(
    train_expense_df: pd.DataFrame,
    val_expense_df: pd.DataFrame,
    config: PipelineConfig,
    confirmed_anomaly_ids: set[str] | None = None,
    val_feedback_df: pd.DataFrame | None = None,
) -> TrainedAnomalyDetector:
    if train_expense_df.empty or val_expense_df.empty:
        raise ValueError("train_expense_df and val_expense_df must both be non-empty")

    train_clean = train_expense_df.copy()
    if confirmed_anomaly_ids:
        filtered = train_clean[~train_clean["transaction_id"].isin(confirmed_anomaly_ids)].copy()
        if len(filtered) >= 10:
            train_clean = filtered

    state = fit_anomaly_feature_state(
        train_clean,
        min_prior_tx=config.anomaly.min_prior_tx_for_user_stats,
    )
    X_train, _ = transform_anomaly_features(train_clean, state)

    iforest = IsolationForest(
        n_estimators=config.anomaly.n_estimators,
        contamination="auto",
        random_state=config.seed,
        n_jobs=1,
    )
    iforest.fit(X_train)

    X_val, _ = transform_anomaly_features(val_expense_df, state, history_expense_df=train_clean)
    val_scores = -iforest.decision_function(X_val)

    q = config.anomaly.validation_quantile
    threshold = float(np.quantile(val_scores, q))

    # Optional validation feedback calibration: reduce false positives on confirmed normal rows
    if val_feedback_df is not None and not val_feedback_df.empty:
        fb_map = dict(
            zip(
                val_feedback_df["transaction_id"].astype(str),
                val_feedback_df["is_confirmed_anomaly"].astype(bool),
            )
        )
        matched_mask = val_expense_df["transaction_id"].astype(str).isin(fb_map.keys()).to_numpy()
        if int(matched_mask.sum()) >= config.retrain.min_val_feedback_rows:
            matched_ids = val_expense_df["transaction_id"].astype(str).to_numpy()[matched_mask]
            matched_scores = val_scores[matched_mask]
            normal_scores = np.array([s for tid, s in zip(matched_ids, matched_scores) if not fb_map[tid]])
            if len(normal_scores) >= 5 and float(np.mean(normal_scores >= threshold)) > 0.10:
                cand_thresh = float(np.quantile(normal_scores, 0.90))
                max_thresh = float(np.quantile(val_scores, 0.99))
                threshold = min(max(threshold, cand_thresh), max_thresh)

    alert_rate = float(np.mean(val_scores >= threshold))
    return TrainedAnomalyDetector(
        feature_state=state,
        isolation_forest=iforest,
        threshold=threshold,
        validation_alert_rate=alert_rate,
    )


def score_expense_anomalies(
    expense_df: pd.DataFrame,
    detector: TrainedAnomalyDetector,
    history_expense_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    X, ctx_df = transform_anomaly_features(
        expense_df,
        detector.feature_state,
        history_expense_df=history_expense_df,
    )
    out = ctx_df.copy()
    if len(out) == 0:
        out["anomaly_score"] = pd.Series(dtype=float)
        out["threshold"] = pd.Series(dtype=float)
        out["is_anomaly"] = pd.Series(dtype=bool)
        out["reasons"] = pd.Series(dtype=object)
        return out

    scores = -detector.isolation_forest.decision_function(X)
    flags = scores >= detector.threshold
    out["anomaly_score"] = scores.astype(float)
    out["threshold"] = float(detector.threshold)
    out["is_anomaly"] = flags.astype(bool)

    reasons_col: list[list[str]] = []
    for idx, row in out.iterrows():
        if bool(row["is_anomaly"]):
            reasons_col.append(_build_reasons(row, float(row["anomaly_score"]), float(detector.threshold)))
        else:
            reasons_col.append([])
    out["reasons"] = reasons_col
    return out
