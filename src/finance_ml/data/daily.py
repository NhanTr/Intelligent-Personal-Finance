"""Strict windowed daily spending aggregation."""

from __future__ import annotations

from datetime import timedelta
import numpy as np
import pandas as pd

from finance_ml.schema import ESSENTIAL_CATEGORIES, EXPENSE_CATEGORIES, ProfileWindow, VN_TZ


def aggregate_daily_spending(
    clean_df: pd.DataFrame,
    profile_windows: dict[str, ProfileWindow],
) -> pd.DataFrame:
    share_cols = [f"cat_share_{cat}" for cat in EXPENSE_CATEGORIES]
    base_cols = ["user_id", "date", "total_expense_vnd", "tx_count", "essential_expense_vnd", *share_cols]

    if not profile_windows:
        return pd.DataFrame(columns=base_cols)

    grid_rows: list[dict[str, object]] = []
    for user_id in sorted(profile_windows.keys()):
        win = profile_windows[user_id]
        n_days = (win.tracking_end_date - win.tracking_start_date).days + 1
        for offset in range(n_days):
            grid_rows.append({"user_id": user_id, "date": win.tracking_start_date + timedelta(days=offset)})
    grid_df = pd.DataFrame(grid_rows)

    if clean_df.empty:
        grid_df["total_expense_vnd"] = 0.0
        grid_df["tx_count"] = 0
        grid_df["essential_expense_vnd"] = 0.0
        for col in share_cols:
            grid_df[col] = 0.0
        return grid_df[base_cols]

    exp = clean_df[
        (clean_df["type"] == "expense")
        & (~clean_df["is_internal_transfer"].astype(bool))
        & (clean_df["user_id"].isin(profile_windows.keys()))
    ].copy()

    if exp.empty:
        grid_df["total_expense_vnd"] = 0.0
        grid_df["tx_count"] = 0
        grid_df["essential_expense_vnd"] = 0.0
        for col in share_cols:
            grid_df[col] = 0.0
        return grid_df[base_cols]

    ts_vn = pd.to_datetime(exp["timestamp"], utc=True).dt.tz_convert(VN_TZ)
    exp["date"] = ts_vn.dt.date

    # Keep only dates strictly inside each user's confirmed tracking window
    start_map = {u: w.tracking_start_date for u, w in profile_windows.items()}
    end_map = {u: w.tracking_end_date for u, w in profile_windows.items()}
    in_window = (exp["date"] >= exp["user_id"].map(start_map)) & (exp["date"] <= exp["user_id"].map(end_map))
    exp = exp[in_window].copy()

    if exp.empty:
        grid_df["total_expense_vnd"] = 0.0
        grid_df["tx_count"] = 0
        grid_df["essential_expense_vnd"] = 0.0
        for col in share_cols:
            grid_df[col] = 0.0
        return grid_df[base_cols]

    exp["is_essential"] = exp["category"].isin(ESSENTIAL_CATEGORIES)
    exp["essential_amount"] = np.where(exp["is_essential"], exp["amount_vnd"], 0.0)

    daily_totals = (
        exp.groupby(["user_id", "date"], as_index=False)
        .agg(
            total_expense_vnd=("amount_vnd", "sum"),
            tx_count=("transaction_id", "count"),
            essential_expense_vnd=("essential_amount", "sum"),
        )
    )

    cat_pivot = (
        exp.pivot_table(
            index=["user_id", "date"],
            columns="category",
            values="amount_vnd",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    merged = grid_df.merge(daily_totals, on=["user_id", "date"], how="left")
    merged["total_expense_vnd"] = merged["total_expense_vnd"].fillna(0.0).astype(float)
    merged["tx_count"] = merged["tx_count"].fillna(0).astype(int)
    merged["essential_expense_vnd"] = merged["essential_expense_vnd"].fillna(0.0).astype(float)

    merged = merged.merge(cat_pivot, on=["user_id", "date"], how="left")
    denom = merged["total_expense_vnd"].to_numpy(dtype=float)
    for cat in EXPENSE_CATEGORIES:
        raw_cat = merged[cat].fillna(0.0).to_numpy(dtype=float) if cat in merged.columns else np.zeros(len(merged))
        merged[f"cat_share_{cat}"] = np.where(denom > 0.0, raw_cat / np.where(denom > 0.0, denom, 1.0), 0.0)

    merged = merged.sort_values(["user_id", "date"], kind="mergesort").reset_index(drop=True)
    return merged[base_cols]
