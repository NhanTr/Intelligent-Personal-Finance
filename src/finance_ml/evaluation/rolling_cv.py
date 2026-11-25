"""Expanding-window time-series cross-validation confined strictly to train+validation."""

from __future__ import annotations

import pandas as pd

from finance_ml.evaluation.split import TimeSplitCutoffs


def generate_expanding_cv_splits(
    daily_df: pd.DataFrame,
    cutoffs: TimeSplitCutoffs,
    n_splits: int = 3,
) -> list[TimeSplitCutoffs]:
    if n_splits < 1:
        raise ValueError("n_splits must be >= 1")

    dev_dates = sorted(d for d in pd.Series(daily_df["date"]).unique() if d <= cutoffs.val_end)
    total = len(dev_dates)
    if total < 60:
        raise ValueError(f"Need at least 60 development dates for expanding CV, got {total}")

    # Reserve first 50% as initial training base, partition remaining 50% into n_splits validation windows
    base_len = max(35, total // 2)
    rem = total - base_len
    fold_width = max(14, rem // n_splits)

    folds: list[TimeSplitCutoffs] = []
    for k in range(n_splits):
        train_end_idx = base_len + k * fold_width - 1
        val_end_idx = total - 1 if k == n_splits - 1 else min(total - 1, train_end_idx + fold_width)
        folds.append(
            TimeSplitCutoffs(
                train_start=dev_dates[0],
                train_end=dev_dates[train_end_idx],
                val_start=dev_dates[train_end_idx + 1],
                val_end=dev_dates[val_end_idx],
                # Dummy post-val placeholders never consumed in CV
                test_start=dev_dates[val_end_idx],
                test_end=dev_dates[val_end_idx],
            )
        )
    return folds
