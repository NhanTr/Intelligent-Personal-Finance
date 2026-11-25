"""Adapter for Kaggle 'Daily Household Transactions' public dataset."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from finance_ml.data.cleaning import clean_transactions
from finance_ml.schema import DataManifest, ProfileWindow, VN_TZ


def _parse_kaggle_date(val: object) -> pd.Timestamp | None:
    if val is None or pd.isna(val):
        return None
    text = str(val).strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=VN_TZ)
            return pd.Timestamp(dt)
        except ValueError:
            continue
    ts = pd.to_datetime(text, dayfirst=True, errors="coerce")
    if pd.isna(ts):
        return None
    dt = ts.to_pydatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=VN_TZ)
    else:
        dt = dt.astimezone(VN_TZ)
    return pd.Timestamp(dt)


def adapt_kaggle_daily_transactions(
    csv_path: Path,
    inr_to_vnd_rate: float = 300.0,
) -> tuple[pd.DataFrame, dict[str, ProfileWindow], DataManifest]:
    raw = pd.read_csv(csv_path)
    mapped_rows: list[dict[str, object]] = []

    for idx, row in raw.iterrows():
        ie_raw = str(row.get("Income/Expense", row.get("Type", ""))).strip().lower()
        is_transfer = False
        if ie_raw in {"transfer-out", "transfer", "transfer out"}:
            tx_type = "expense"
            is_transfer = True
            cat = "transfer"
        elif ie_raw in {"income", "credit"}:
            tx_type = "income"
            cat = str(row.get("Category", "other"))
        elif ie_raw in {"expense", "debit"}:
            tx_type = "expense"
            cat = str(row.get("Category", "other"))
        else:
            tx_type = ie_raw
            cat = str(row.get("Category", "other"))

        try:
            amt_vnd = float(row.get("Amount", 0.0)) * float(inr_to_vnd_rate)
        except (TypeError, ValueError):
            amt_vnd = -1.0

        sub = str(row.get("Subcategory", "") or "").strip()
        note = str(row.get("Note", "") or "").strip()
        full_note = " - ".join(p for p in (sub, note) if p) or None

        mapped_rows.append(
            {
                "transaction_id": f"pub_{idx + 1:06d}",
                "user_id": "public_hh_001",
                "timestamp": _parse_kaggle_date(row.get("Date")),
                "type": tx_type,
                "amount_vnd": amt_vnd,
                "category": cat,
                "is_internal_transfer": is_transfer,
                "note": full_note,
            }
        )

    mapped_df = pd.DataFrame(mapped_rows)
    clean_df, report = clean_transactions(mapped_df)
    if clean_df.empty:
        raise ValueError(f"No valid transactions extracted from {csv_path}")

    dates = pd.to_datetime(clean_df["timestamp"], utc=True).dt.tz_convert(VN_TZ).dt.date
    min_d = dates.min()
    max_d = dates.max()
    windows = {
        "public_hh_001": ProfileWindow(
            user_id="public_hh_001",
            tracking_start_date=min_d,
            tracking_end_date=max_d,
        )
    }

    missing_rate = float(report.dropped_invalid_rows / max(1, report.input_rows))
    manifest = DataManifest(
        dataset_name="kaggle_daily_household_transactions",
        source_type="real_public",
        source_url_or_generator="https://www.kaggle.com/datasets/prasad22/dai-ly-transactions-dataset",
        usage_terms="Public Kaggle dataset for academic/research evaluation; single anonymized household profile.",
        generated_or_fetched_at=datetime.now(timezone.utc).astimezone(VN_TZ).isoformat(),
        version="1.0.0",
        seed=None,
        currency_unit="VND",
        currency_conversion_note=f"Converted from INR to VND using fixed factor {inr_to_vnd_rate:.1f} VND/INR.",
        profile_count=1,
        min_date=min_d,
        max_date=max_d,
        total_transactions=int(len(clean_df)),
        missing_rate=missing_rate,
        cleaning_summary=report.model_dump(),
        notes=[
            "Single-household real-world transaction benchmark.",
            "Transfer-Out rows mapped to is_internal_transfer=True so they are excluded from spending totals.",
            "Reported strictly separately from synthetic multi-user results.",
        ],
    )
    return clean_df, windows, manifest
