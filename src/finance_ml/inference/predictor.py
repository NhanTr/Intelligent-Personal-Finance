"""Public Python inference functions for F3 7-day forecast and F4 anomaly detection."""

from __future__ import annotations

from datetime import date, timedelta
import pandas as pd

from finance_ml.data.cleaning import clean_transactions
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.features.forecast_features import FORECAST_FEATURE_COLUMNS, build_single_forecast_features
from finance_ml.inference.loader import LoadedBundle
from finance_ml.models.anomaly import score_expense_anomalies
from finance_ml.models.forecast import Last7DaysBaseline
from finance_ml.schema import AnomalyBatchResult, AnomalyItem, ForecastResult, ProfileWindow, VN_TZ


def predict_next_7d(
    transactions_df: pd.DataFrame,
    user_id: str,
    as_of_date: date,
    bundle: LoadedBundle,
    tracking_start_date: date | None = None,
    min_days_required: int = 28,
    horizon_days: int = 7,
) -> ForecastResult:
    f_start = as_of_date + timedelta(days=1)
    f_end = as_of_date + timedelta(days=horizon_days)

    if transactions_df.empty or "user_id" not in transactions_df.columns:
        user_clean = pd.DataFrame()
    else:
        user_raw = transactions_df[transactions_df["user_id"].astype(str) == str(user_id)]
        user_clean, _ = clean_transactions(user_raw)

    effective_start: date | None = None
    if tracking_start_date is not None:
        if tracking_start_date <= as_of_date:
            effective_start = tracking_start_date
            days_available = (as_of_date - effective_start).days + 1
        else:
            days_available = 0
    else:
        if user_clean.empty:
            days_available = 0
        else:
            tx_dates = pd.to_datetime(user_clean["timestamp"], utc=True).dt.tz_convert(VN_TZ).dt.date
            le_dates = tx_dates[tx_dates <= as_of_date]
            if le_dates.empty:
                days_available = 0
            else:
                effective_start = le_dates.min()
                days_available = (as_of_date - effective_start).days + 1

    if effective_start is None or days_available < min_days_required:
        return ForecastResult(
            status="insufficient_data",
            user_id=str(user_id),
            as_of_date=as_of_date,
            horizon_days=horizon_days,
            forecast_start_date=f_start,
            forecast_end_date=f_end,
            predicted_total_vnd=None,
            unit="VND",
            model_name="none",
            model_version=bundle.version,
            days_available=days_available,
            min_days_required=min_days_required,
            limitations_note=(
                f"Chưa đủ lịch sử giao dịch để dự báo: hiện có {days_available} ngày, "
                f"cần tối thiểu {min_days_required} ngày."
            ),
        )

    window = {
        str(user_id): ProfileWindow(
            user_id=str(user_id),
            tracking_start_date=effective_start,
            tracking_end_date=as_of_date,
        )
    }
    daily = aggregate_daily_spending(user_clean, window)
    feat_df = build_single_forecast_features(
        daily,
        str(user_id),
        as_of_date,
        min_history_days=min_days_required,
        horizon_days=horizon_days,
    )[list(FORECAST_FEATURE_COLUMNS)]

    if bundle.fallback_only or bundle.bundle is None:
        pred_val = float(Last7DaysBaseline().fit(feat_df).predict(feat_df)[0])
        return ForecastResult(
            status="fallback_baseline",
            user_id=str(user_id),
            as_of_date=as_of_date,
            horizon_days=horizon_days,
            forecast_start_date=f_start,
            forecast_end_date=f_end,
            predicted_total_vnd=round(pred_val, 2),
            unit="VND",
            model_name="baseline_last_7d",
            model_version=bundle.version,
            days_available=days_available,
            min_days_required=min_days_required,
            limitations_note="Đang dùng mô hình cơ sở (tổng chi 7 ngày gần nhất) do chưa nạp được mô hình huấn luyện.",
        )

    mb = bundle.bundle
    pred_val = float(mb.forecast_estimator.predict(feat_df)[0])
    is_fallback = bool(mb.metadata.get("forecast_fallback_used", False))
    status = "fallback_baseline" if is_fallback else "ok"
    return ForecastResult(
        status=status,
        user_id=str(user_id),
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        forecast_start_date=f_start,
        forecast_end_date=f_end,
        predicted_total_vnd=round(pred_val, 2),
        unit="VND",
        model_name=mb.selected_forecast_name,
        model_version=mb.version,
        days_available=days_available,
        min_days_required=min_days_required,
        limitations_note=(
            "Dự báo 7 ngày tới dựa trên hành vi lịch sử (đơn vị VND); không tự quy đổi thành dự báo tháng."
        ),
    )


def detect_anomalies(
    transactions_df: pd.DataFrame,
    user_id: str,
    bundle: LoadedBundle,
    target_transaction_ids: list[str] | None = None,
) -> AnomalyBatchResult:
    if bundle.fallback_only or bundle.bundle is None:
        return AnomalyBatchResult(
            status="model_unavailable",
            user_id=str(user_id),
            model_version=bundle.version,
            threshold=None,
            total_evaluated=0,
            flagged_count=0,
            items=[],
        )

    if transactions_df.empty or "user_id" not in transactions_df.columns:
        return AnomalyBatchResult(
            status="ok",
            user_id=str(user_id),
            model_version=bundle.bundle.version,
            threshold=bundle.bundle.anomaly_detector.threshold,
            total_evaluated=0,
            flagged_count=0,
            items=[],
        )

    user_raw = transactions_df[transactions_df["user_id"].astype(str) == str(user_id)]
    user_clean, _ = clean_transactions(user_raw)
    exp_df = user_clean[(user_clean["type"] == "expense") & (~user_clean["is_internal_transfer"])].copy()

    if exp_df.empty:
        return AnomalyBatchResult(
            status="ok",
            user_id=str(user_id),
            model_version=bundle.bundle.version,
            threshold=bundle.bundle.anomaly_detector.threshold,
            total_evaluated=0,
            flagged_count=0,
            items=[],
        )

    scored = score_expense_anomalies(exp_df, bundle.bundle.anomaly_detector)
    if target_transaction_ids is not None:
        wanted = {str(tid) for tid in target_transaction_ids}
        scored = scored[scored["transaction_id"].astype(str).isin(wanted)].reset_index(drop=True)

    items = [
        AnomalyItem(
            transaction_id=str(row["transaction_id"]),
            timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
            amount_vnd=float(row["amount_vnd"]),
            category=str(row["category"]),
            anomaly_score=round(float(row["anomaly_score"]), 6),
            threshold=round(float(row["threshold"]), 6),
            is_anomaly=bool(row["is_anomaly"]),
            reasons=list(row["reasons"]),
        )
        for _, row in scored.iterrows()
    ]
    flagged_cnt = sum(1 for it in items if it.is_anomaly)
    return AnomalyBatchResult(
        status="ok",
        user_id=str(user_id),
        model_version=bundle.bundle.version,
        threshold=round(float(bundle.bundle.anomaly_detector.threshold), 6),
        total_evaluated=len(items),
        flagged_count=flagged_cnt,
        items=items,
    )
