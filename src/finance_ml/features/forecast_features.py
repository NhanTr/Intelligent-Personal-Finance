"""Causal 7-day spending forecast feature builder (shared by training and inference)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
import pandas as pd

from finance_ml.schema import ProfileWindow

FORECAST_FEATURE_COLUMNS: tuple[str, ...] = (
    "spend_last_7d",
    "spend_last_14d",
    "spend_last_28d",
    "daily_mean_7d",
    "daily_std_7d",
    "daily_mean_28d",
    "daily_std_28d",
    "tx_count_7d",
    "tx_count_28d",
    "zero_spend_days_28d",
    "essential_share_28d",
    "origin_day_of_week",
    "origin_day_of_month",
    "days_to_month_end",
    "spans_month_start",
    "spans_month_end",
)


def _compute_causal_row(
    history_df: pd.DataFrame,
    origin_date: date,
    horizon_days: int = 7,
) -> dict[str, float]:
    last_7 = history_df.tail(7)
    last_14 = history_df.tail(14)
    last_28 = history_df.tail(28)

    s7 = float(last_7["total_expense_vnd"].sum())
    s14 = float(last_14["total_expense_vnd"].sum())
    s28 = float(last_28["total_expense_vnd"].sum())

    m7 = float(last_7["total_expense_vnd"].mean())
    std7 = float(last_7["total_expense_vnd"].std(ddof=0))
    m28 = float(last_28["total_expense_vnd"].mean())
    std28 = float(last_28["total_expense_vnd"].std(ddof=0))

    tx7 = float(last_7["tx_count"].sum())
    tx28 = float(last_28["tx_count"].sum())
    zero28 = float((last_28["total_expense_vnd"] == 0.0).sum())

    ess28 = float(last_28["essential_expense_vnd"].sum()) if "essential_expense_vnd" in last_28.columns else 0.0
    ess_share = ess28 / s28 if s28 > 0.0 else 0.0

    last_dom = calendar.monthrange(origin_date.year, origin_date.month)[1]
    days_to_end = float(last_dom - origin_date.day)

    future_days = [origin_date + timedelta(days=k) for k in range(1, horizon_days + 1)]
    spans_start = 1.0 if any(1 <= d.day <= 5 for d in future_days) else 0.0
    spans_end = 1.0 if any(d.day >= 25 for d in future_days) else 0.0

    return {
        "spend_last_7d": s7,
        "spend_last_14d": s14,
        "spend_last_28d": s28,
        "daily_mean_7d": m7,
        "daily_std_7d": std7,
        "daily_mean_28d": m28,
        "daily_std_28d": std28,
        "tx_count_7d": tx7,
        "tx_count_28d": tx28,
        "zero_spend_days_28d": zero28,
        "essential_share_28d": ess_share,
        "origin_day_of_week": float(origin_date.weekday()),
        "origin_day_of_month": float(origin_date.day),
        "days_to_month_end": days_to_end,
        "spans_month_start": spans_start,
        "spans_month_end": spans_end,
    }


def build_forecast_dataset(
    daily_df: pd.DataFrame,
    profile_windows: dict[str, ProfileWindow],
    horizon_days: int = 7,
    min_history_days: int = 28,
) -> pd.DataFrame:
    cols = ["user_id", "origin_date", *FORECAST_FEATURE_COLUMNS, "target_next_7d_vnd"]
    if daily_df.empty:
        return pd.DataFrame(columns=cols)

    records: list[dict[str, object]] = []
    sorted_daily = daily_df.sort_values(["user_id", "date"], kind="mergesort").reset_index(drop=True)

    for user_id, u_df in sorted_daily.groupby("user_id", sort=False):
        if user_id not in profile_windows:
            continue
        win = profile_windows[user_id]
        u_df = u_df.reset_index(drop=True)
        n = len(u_df)
        if n < min_history_days + horizon_days:
            continue

        for idx in range(min_history_days - 1, n - horizon_days):
            origin_d: date = u_df.loc[idx, "date"]
            if origin_d + timedelta(days=horizon_days) > win.tracking_end_date:
                continue
            hist_slice = u_df.iloc[: idx + 1]
            future_slice = u_df.iloc[idx + 1 : idx + 1 + horizon_days]
            if len(future_slice) < horizon_days:
                continue

            feats = _compute_causal_row(hist_slice, origin_d, horizon_days=horizon_days)
            target = float(future_slice["total_expense_vnd"].sum())
            records.append(
                {
                    "user_id": user_id,
                    "origin_date": origin_d,
                    **feats,
                    "target_next_7d_vnd": target,
                }
            )

    if not records:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(records, columns=cols)


def build_single_forecast_features(
    daily_df: pd.DataFrame,
    user_id: str,
    as_of_date: date,
    min_history_days: int = 28,
    horizon_days: int = 7,
) -> pd.DataFrame:
    u_df = daily_df[(daily_df["user_id"] == user_id) & (daily_df["date"] <= as_of_date)].sort_values(
        "date", kind="mergesort"
    )
    if len(u_df) < min_history_days:
        raise ValueError(
            f"User {user_id} has {len(u_df)} days <= {as_of_date}, requires >= {min_history_days} days"
        )
    feats = _compute_causal_row(u_df, as_of_date, horizon_days=horizon_days)
    return pd.DataFrame([{"user_id": user_id, "origin_date": as_of_date, **feats}])
