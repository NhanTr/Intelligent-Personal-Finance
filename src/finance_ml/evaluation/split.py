"""Chronological split cutoffs and boundary-purged origin assignment."""

from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
from pydantic import BaseModel

from finance_ml.schema import VN_TZ


class TimeSplitCutoffs(BaseModel):
    train_start: date
    train_end: date
    val_start: date
    val_end: date
    test_start: date
    test_end: date


def compute_time_cutoffs(
    daily_df: pd.DataFrame,
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
) -> TimeSplitCutoffs:
    unique_dates = sorted(pd.Series(daily_df["date"]).unique())
    n = len(unique_dates)
    if n < 30:
        raise ValueError(f"Need at least 30 unique dates for chronological split, got {n}")

    r_train, r_val, _ = ratios
    train_end_idx = max(0, int(round(n * r_train)) - 1)
    val_end_idx = max(train_end_idx + 1, int(round(n * (r_train + r_val))) - 1)
    val_end_idx = min(val_end_idx, n - 2)

    return TimeSplitCutoffs(
        train_start=unique_dates[0],
        train_end=unique_dates[train_end_idx],
        val_start=unique_dates[train_end_idx + 1],
        val_end=unique_dates[val_end_idx],
        test_start=unique_dates[val_end_idx + 1],
        test_end=unique_dates[-1],
    )


def assign_forecast_origins(
    origins_df: pd.DataFrame,
    cutoffs: TimeSplitCutoffs,
    horizon_days: int = 7,
    min_step_days: int = 7,
) -> pd.DataFrame:
    if origins_df.empty:
        out = origins_df.copy()
        out["split"] = pd.Series(dtype="object")
        return out

    horizon = timedelta(days=horizon_days)
    df = origins_df.sort_values(["user_id", "origin_date"], kind="mergesort").copy()

    splits: list[str | None] = []
    for origin_d in df["origin_date"]:
        label_end = origin_d + horizon
        if cutoffs.train_start <= origin_d and label_end <= cutoffs.train_end:
            splits.append("train")
        elif cutoffs.val_start <= origin_d and label_end <= cutoffs.val_end:
            splits.append("validation")
        elif cutoffs.test_start <= origin_d and label_end <= cutoffs.test_end:
            splits.append("test")
        else:
            # Boundary-crossing label window is strictly purged
            splits.append(None)

    df["split"] = splits
    df = df[df["split"].notna()].copy()

    # Enforce >= min_step_days spacing per (user_id, split)
    keep_mask: list[bool] = []
    for _, grp in df.groupby(["user_id", "split"], sort=False):
        last_kept: date | None = None
        for d in grp["origin_date"]:
            if last_kept is None or (d - last_kept).days >= min_step_days:
                keep_mask.append(True)
                last_kept = d
            else:
                keep_mask.append(False)

    return df[keep_mask].reset_index(drop=True)


def assign_transaction_splits(tx_df: pd.DataFrame, cutoffs: TimeSplitCutoffs) -> pd.DataFrame:
    if tx_df.empty:
        out = tx_df.copy()
        out["split"] = pd.Series(dtype="object")
        return out

    out = tx_df.copy()
    tx_dates = pd.to_datetime(out["timestamp"], utc=True).dt.tz_convert(VN_TZ).dt.date
    splits: list[str | None] = []
    for d in tx_dates:
        if cutoffs.train_start <= d <= cutoffs.train_end:
            splits.append("train")
        elif cutoffs.val_start <= d <= cutoffs.val_end:
            splits.append("validation")
        elif cutoffs.test_start <= d <= cutoffs.test_end:
            splits.append("test")
        else:
            splits.append(None)
    out["split"] = splits
    return out[out["split"].notna()].reset_index(drop=True)
