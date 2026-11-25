"""Canonical schemas and category normalization for Personal Finance ML."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

VN_TZ = timezone(timedelta(hours=7))

CANONICAL_CATEGORIES: tuple[str, ...] = (
    "food",
    "transport",
    "housing",
    "utilities",
    "shopping",
    "entertainment",
    "health",
    "education",
    "salary",
    "bonus",
    "transfer",
    "other",
)

EXPENSE_CATEGORIES: tuple[str, ...] = (
    "food",
    "transport",
    "housing",
    "utilities",
    "shopping",
    "entertainment",
    "health",
    "education",
    "other",
)

ESSENTIAL_CATEGORIES: frozenset[str] = frozenset(
    {"food", "transport", "housing", "utilities", "health", "education"}
)

_CATEGORY_ALIASES: dict[str, str] = {
    # Food
    "food": "food",
    "food & dining": "food",
    "food & drink": "food",
    "dining out": "food",
    "groceries": "food",
    "grocery": "food",
    "restaurant": "food",
    "ăn uống": "food",
    "thực phẩm": "food",
    # Transport
    "transport": "transport",
    "transportation": "transport",
    "travel": "transport",
    "commute": "transport",
    "fuel": "transport",
    "di chuyển": "transport",
    "xăng xe": "transport",
    # Housing
    "housing": "housing",
    "rent": "housing",
    "household": "housing",
    "nhà ở": "housing",
    "thuê nhà": "housing",
    # Utilities
    "utilities": "utilities",
    "bills": "utilities",
    "electricity": "utilities",
    "internet": "utilities",
    "water": "utilities",
    "hóa đơn": "utilities",
    "điện nước": "utilities",
    # Shopping
    "shopping": "shopping",
    "apparel": "shopping",
    "beauty": "shopping",
    "personal care": "shopping",
    "mua sắm": "shopping",
    # Entertainment
    "entertainment": "entertainment",
    "culture": "entertainment",
    "leisure": "entertainment",
    "subscriptions": "entertainment",
    "festival": "entertainment",
    "giải trí": "entertainment",
    # Health
    "health": "health",
    "healthcare": "health",
    "medical": "health",
    "y tế": "health",
    "sức khỏe": "health",
    # Education
    "education": "education",
    "tuition": "education",
    "books": "education",
    "giáo dục": "education",
    "học tập": "education",
    # Income
    "salary": "salary",
    "paycheck": "salary",
    "lương": "salary",
    "bonus": "bonus",
    "allowance": "bonus",
    "interest": "bonus",
    "thưởng": "bonus",
    # Transfers
    "transfer": "transfer",
    "transfer-out": "transfer",
    "internal transfer": "transfer",
    "savings": "transfer",
    "investment": "transfer",
    "chuyển khoản nội bộ": "transfer",
    # Other
    "other": "other",
    "misc": "other",
    "gift": "other",
    "khác": "other",
}


def normalize_category(raw: Any) -> str:
    if raw is None:
        return "other"
    if isinstance(raw, float) and math.isnan(raw):
        return "other"
    cleaned = str(raw).strip().lower()
    if not cleaned:
        return "other"
    if cleaned in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[cleaned]
    for key, target in _CATEGORY_ALIASES.items():
        if key in cleaned and len(key) >= 4:
            return target
    return "other"


def ensure_vn_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=VN_TZ)
    return dt.astimezone(VN_TZ)


class TransactionRecord(BaseModel):
    transaction_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    timestamp: datetime
    type: Literal["income", "expense"]
    amount_vnd: float = Field(gt=0.0)
    category: str = "other"
    is_internal_transfer: bool = False
    note: str | None = None

    @field_validator("timestamp")
    @classmethod
    def _norm_ts(cls, v: datetime) -> datetime:
        return ensure_vn_datetime(v)

    @field_validator("category", mode="before")
    @classmethod
    def _norm_cat(cls, v: Any) -> str:
        return normalize_category(v)

    @model_validator(mode="after")
    def _sync_transfer_flag(self) -> TransactionRecord:
        if self.category == "transfer":
            self.is_internal_transfer = True
        return self


class ProfileWindow(BaseModel):
    user_id: str = Field(min_length=1)
    tracking_start_date: date
    tracking_end_date: date

    @model_validator(mode="after")
    def _check_dates(self) -> ProfileWindow:
        if self.tracking_end_date < self.tracking_start_date:
            raise ValueError("tracking_end_date must be >= tracking_start_date")
        return self


class ForecastResult(BaseModel):
    status: Literal["ok", "insufficient_data", "fallback_baseline"]
    user_id: str
    as_of_date: date
    horizon_days: int = 7
    forecast_start_date: date
    forecast_end_date: date
    predicted_total_vnd: float | None = None
    unit: Literal["VND"] = "VND"
    model_name: str
    model_version: str
    days_available: int = Field(ge=0)
    min_days_required: int = 28
    limitations_note: str


class AnomalyItem(BaseModel):
    transaction_id: str
    timestamp: datetime
    amount_vnd: float = Field(gt=0.0)
    category: str
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    reasons: list[str] = Field(default_factory=list)


class AnomalyBatchResult(BaseModel):
    status: Literal["ok", "model_unavailable"] = "ok"
    user_id: str
    model_version: str
    threshold: float | None = None
    total_evaluated: int = Field(ge=0)
    flagged_count: int = Field(ge=0)
    disclaimer: str = (
        "Điểm bất thường chỉ dùng để tham khảo xem xét, không phải xác suất gian lận "
        "và hệ thống không tự xóa hoặc chặn giao dịch."
    )
    items: list[AnomalyItem] = Field(default_factory=list)


class FeedbackRecord(BaseModel):
    transaction_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    is_confirmed_anomaly: bool
    model_version: str = Field(min_length=1)
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _norm_created(cls, v: datetime) -> datetime:
        return ensure_vn_datetime(v)


class DataManifest(BaseModel):
    dataset_name: str
    source_type: Literal["synthetic", "real_public"]
    source_url_or_generator: str
    usage_terms: str
    generated_or_fetched_at: str
    version: str
    seed: int | None = None
    currency_unit: Literal["VND"] = "VND"
    currency_conversion_note: str | None = None
    profile_count: int = Field(ge=1)
    min_date: date
    max_date: date
    total_transactions: int = Field(ge=0)
    missing_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    cleaning_summary: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
