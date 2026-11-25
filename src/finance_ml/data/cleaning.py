"""Transaction cleaning, schema validation, and deduplication."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any
import pandas as pd
from pydantic import BaseModel, Field

from finance_ml.schema import VN_TZ, ensure_vn_datetime, normalize_category

CANONICAL_TX_COLUMNS: tuple[str, ...] = (
    "transaction_id",
    "user_id",
    "timestamp",
    "type",
    "amount_vnd",
    "category",
    "is_internal_transfer",
    "note",
)


class CleaningReport(BaseModel):
    input_rows: int = 0
    valid_rows: int = 0
    dropped_invalid_rows: int = 0
    deduplicated_rows: int = 0
    internal_transfer_rows: int = 0
    error_breakdown: dict[str, int] = Field(default_factory=dict)


def _parse_vn_timestamp(val: Any) -> datetime | None:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    if isinstance(val, pd.Timestamp):
        if pd.isna(val):
            return None
        dt = val.to_pydatetime()
        return ensure_vn_datetime(dt)
    if isinstance(val, datetime):
        return ensure_vn_datetime(val)
    text = str(val).strip()
    if not text:
        return None
    try:
        ts = pd.Timestamp(text)
        if pd.isna(ts):
            return None
        return ensure_vn_datetime(ts.to_pydatetime())
    except Exception:
        return None


def _parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return False
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val).strip().lower() in {"true", "1", "yes", "y"}


def clean_transactions(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    input_rows = int(len(raw_df))
    errors: dict[str, int] = {}

    def bump(reason: str) -> None:
        errors[reason] = errors.get(reason, 0) + 1

    if input_rows == 0:
        empty = pd.DataFrame(columns=list(CANONICAL_TX_COLUMNS))
        return empty, CleaningReport(input_rows=0)

    required = {"transaction_id", "user_id", "timestamp", "type", "amount_vnd"}
    missing_cols = required - set(raw_df.columns)
    if missing_cols:
        raise ValueError(f"Missing required transaction columns: {sorted(missing_cols)}")

    valid_records: list[dict[str, Any]] = []
    for row in raw_df.to_dict(orient="records"):
        tx_id_raw = row.get("transaction_id")
        user_id_raw = row.get("user_id")
        if tx_id_raw is None or (isinstance(tx_id_raw, float) and math.isnan(tx_id_raw)) or not str(tx_id_raw).strip():
            bump("missing_transaction_id")
            continue
        if user_id_raw is None or (isinstance(user_id_raw, float) and math.isnan(user_id_raw)) or not str(user_id_raw).strip():
            bump("missing_user_id")
            continue

        ts = _parse_vn_timestamp(row.get("timestamp"))
        if ts is None:
            bump("invalid_timestamp")
            continue

        tx_type = str(row.get("type", "")).strip().lower()
        if tx_type not in {"income", "expense"}:
            bump("invalid_type")
            continue

        try:
            amount = float(row.get("amount_vnd"))
        except (TypeError, ValueError):
            bump("invalid_amount")
            continue
        if not math.isfinite(amount) or amount <= 0.0:
            bump("non_positive_amount")
            continue

        cat = normalize_category(row.get("category"))
        is_transfer = _parse_bool(row.get("is_internal_transfer", False)) or (cat == "transfer")
        note_raw = row.get("note")
        note = None if note_raw is None or (isinstance(note_raw, float) and math.isnan(note_raw)) else str(note_raw)

        valid_records.append(
            {
                "transaction_id": str(tx_id_raw).strip(),
                "user_id": str(user_id_raw).strip(),
                "timestamp": pd.Timestamp(ts),
                "type": tx_type,
                "amount_vnd": amount,
                "category": cat,
                "is_internal_transfer": bool(is_transfer),
                "note": note,
            }
        )

    dropped_invalid = input_rows - len(valid_records)
    if not valid_records:
        empty = pd.DataFrame(columns=list(CANONICAL_TX_COLUMNS))
        return empty, CleaningReport(
            input_rows=input_rows,
            valid_rows=0,
            dropped_invalid_rows=dropped_invalid,
            deduplicated_rows=0,
            internal_transfer_rows=0,
            error_breakdown=errors,
        )

    df = pd.DataFrame(valid_records, columns=list(CANONICAL_TX_COLUMNS))
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["transaction_id"], keep="first").copy()
    dedup_count = before_dedup - len(df)

    df = df.sort_values(["user_id", "timestamp", "transaction_id"], kind="mergesort").reset_index(drop=True)
    transfer_count = int(df["is_internal_transfer"].sum())

    report = CleaningReport(
        input_rows=input_rows,
        valid_rows=int(len(df)),
        dropped_invalid_rows=int(dropped_invalid),
        deduplicated_rows=int(dedup_count),
        internal_transfer_rows=transfer_count,
        error_breakdown=errors,
    )
    return df, report
