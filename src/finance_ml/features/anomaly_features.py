"""Strictly causal transaction-level anomaly features for Isolation Forest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder

from finance_ml.schema import CANONICAL_CATEGORIES, VN_TZ, normalize_category

NUMERIC_ANOMALY_COLS: tuple[str, ...] = (
    "log_amount",
    "user_amount_ratio",
    "user_amount_zscore",
    "user_cat_amount_ratio",
    "tx_freq_24h",
    "tx_freq_7d",
    "hour_of_day",
    "is_weekend",
)


@dataclass
class AnomalyFeatureFitState:
    global_median_amount: float
    global_log_mean: float
    global_log_std: float
    cat_medians: dict[str, float]
    encoder: OneHotEncoder
    min_prior_tx: int = 5
    feature_names: tuple[str, ...] = ()


def fit_anomaly_feature_state(
    train_expense_df: pd.DataFrame,
    min_prior_tx: int = 5,
) -> AnomalyFeatureFitState:
    if train_expense_df.empty:
        raise ValueError("Cannot fit AnomalyFeatureFitState on empty train_expense_df")

    amounts = train_expense_df["amount_vnd"].astype(float).to_numpy()
    logs = np.log1p(np.maximum(amounts, 0.0))
    cats = train_expense_df["category"].map(normalize_category)

    global_med = float(np.median(amounts))
    global_lmean = float(np.mean(logs))
    global_lstd = max(float(np.std(logs, ddof=0)), 0.1)

    cat_medians: dict[str, float] = {}
    tmp = pd.DataFrame({"cat": cats, "amt": amounts})
    for cat, grp in tmp.groupby("cat"):
        cat_medians[str(cat)] = float(np.median(grp["amt"].to_numpy()))

    enc = OneHotEncoder(
        categories=[list(CANONICAL_CATEGORIES)],
        handle_unknown="ignore",
        sparse_output=False,
    )
    enc.fit(cats.to_frame(name="category"))
    cat_feature_names = [f"cat_{c}" for c in CANONICAL_CATEGORIES]

    return AnomalyFeatureFitState(
        global_median_amount=global_med,
        global_log_mean=global_lmean,
        global_log_std=global_lstd,
        cat_medians=cat_medians,
        encoder=enc,
        min_prior_tx=min_prior_tx,
        feature_names=(*NUMERIC_ANOMALY_COLS, *cat_feature_names),
    )


def transform_anomaly_features(
    expense_df: pd.DataFrame,
    state: AnomalyFeatureFitState,
    history_expense_df: pd.DataFrame | None = None,
) -> tuple[np.ndarray, pd.DataFrame]:
    if expense_df.empty:
        empty_ctx = pd.DataFrame(columns=["transaction_id", "user_id", "timestamp", "amount_vnd", "category", *NUMERIC_ANOMALY_COLS])
        return np.zeros((0, len(state.feature_names)), dtype=float), empty_ctx

    target = expense_df.copy().reset_index(drop=True)
    target["_is_target"] = True
    target["_orig_pos"] = np.arange(len(target))

    if history_expense_df is not None and not history_expense_df.empty:
        hist = history_expense_df.copy().reset_index(drop=True)
        # Deduplicate any overlapping transaction_ids already in target
        hist = hist[~hist["transaction_id"].isin(set(target["transaction_id"]))].copy()
        hist["_is_target"] = False
        hist["_orig_pos"] = -1
        combined = pd.concat([hist, target], ignore_index=True)
    else:
        combined = target

    combined["_ts"] = pd.to_datetime(combined["timestamp"], utc=True).dt.tz_convert(VN_TZ)
    combined["_cat"] = combined["category"].map(normalize_category)
    combined["_amt"] = combined["amount_vnd"].astype(float)
    combined = combined.sort_values(["user_id", "_ts", "_is_target", "_orig_pos"], kind="mergesort").reset_index(drop=True)

    ctx_rows: list[dict[str, object]] = []
    delta_24h = timedelta(hours=24)
    delta_7d = timedelta(days=7)

    for user_id, grp in combined.groupby("user_id", sort=False):
        ts_list = [t.to_pydatetime() for t in grp["_ts"]]
        amt_arr = grp["_amt"].to_numpy(dtype=float)
        log_arr = np.log1p(np.maximum(amt_arr, 0.0))
        cat_list = grp["_cat"].tolist()
        is_target_list = grp["_is_target"].tolist()
        orig_pos_list = grp["_orig_pos"].tolist()
        tx_id_list = grp["transaction_id"].tolist()

        # Pointer for strictly causal prior transactions (ts < current_ts)
        strict_end = 0
        left_24h = 0
        left_7d = 0

        for i in range(len(grp)):
            cur_ts = ts_list[i]
            while strict_end < i and ts_list[strict_end] < cur_ts:
                strict_end += 1
            while left_24h < strict_end and ts_list[left_24h] < cur_ts - delta_24h:
                left_24h += 1
            while left_7d < strict_end and ts_list[left_7d] < cur_ts - delta_7d:
                left_7d += 1

            if not is_target_list[i]:
                continue

            amt = amt_arr[i]
            log_amt = float(log_arr[i])
            cat = cat_list[i]

            if strict_end >= state.min_prior_tx:
                prior_amts = amt_arr[:strict_end]
                prior_logs = log_arr[:strict_end]
                ref_med = float(np.median(prior_amts))
                ref_lmean = float(np.mean(prior_logs))
                ref_lstd = max(float(np.std(prior_logs, ddof=0)), 0.1)
            else:
                ref_med = state.global_median_amount
                ref_lmean = state.global_log_mean
                ref_lstd = state.global_log_std

            prior_cat_amts = [amt_arr[j] for j in range(strict_end) if cat_list[j] == cat]
            if len(prior_cat_amts) >= 3:
                cat_ref = float(np.median(prior_cat_amts))
            else:
                cat_ref = state.cat_medians.get(cat, ref_med)

            u_ratio = float(amt / (ref_med + 1.0))
            u_zscore = float((log_amt - ref_lmean) / ref_lstd)
            c_ratio = float(amt / (cat_ref + 1.0))
            f24 = float(strict_end - left_24h)
            f7d = float(strict_end - left_7d)

            ctx_rows.append(
                {
                    "_orig_pos": orig_pos_list[i],
                    "transaction_id": tx_id_list[i],
                    "user_id": user_id,
                    "timestamp": pd.Timestamp(cur_ts),
                    "amount_vnd": amt,
                    "category": cat,
                    "log_amount": log_amt,
                    "user_amount_ratio": u_ratio,
                    "user_amount_zscore": u_zscore,
                    "user_cat_amount_ratio": c_ratio,
                    "tx_freq_24h": f24,
                    "tx_freq_7d": f7d,
                    "hour_of_day": float(cur_ts.hour),
                    "is_weekend": 1.0 if cur_ts.weekday() >= 5 else 0.0,
                }
            )

    ctx_df = pd.DataFrame(ctx_rows).sort_values("_orig_pos", kind="mergesort").drop(columns=["_orig_pos"]).reset_index(drop=True)
    num_mat = ctx_df[list(NUMERIC_ANOMALY_COLS)].to_numpy(dtype=float)
    cat_mat = state.encoder.transform(ctx_df[["category"]])
    X = np.hstack([num_mat, cat_mat])
    return X, ctx_df
