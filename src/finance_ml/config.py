"""Pipeline configuration loader and validator."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator


class CurrencyConfig(BaseModel):
    inr_to_vnd_rate: float = Field(default=300.0, gt=0.0)


class SyntheticConfig(BaseModel):
    n_core_users: int = Field(default=8, ge=1)
    core_days: int = Field(default=300, ge=180)
    start_date: date = Field(default=date(2026, 1, 1))
    short_user_id: str = "user_short_001"
    short_user_days: int = Field(default=14, ge=1, lt=28)
    internal_transfer_prob: float = Field(default=0.05, ge=0.0, lt=0.5)
    anomaly_eval_users: int = Field(default=4, ge=1)
    anomaly_injection_rate: float = Field(default=0.035, gt=0.0, lt=0.5)


class RFGridConfig(BaseModel):
    n_estimators: list[int] = Field(default_factory=lambda: [100, 200])
    max_depth: list[int | None] = Field(default_factory=lambda: [4, 6, 10, None])
    min_samples_leaf: list[int] = Field(default_factory=lambda: [2, 5, 10])


class ForecastConfig(BaseModel):
    horizon_days: int = Field(default=7, ge=1)
    min_history_days: int = Field(default=28, ge=7)
    origin_step_days: int = Field(default=7, ge=7)
    target_improvement_pct: float = Field(default=10.0, ge=0.0)
    rf_grid: RFGridConfig = Field(default_factory=RFGridConfig)


class AnomalyConfig(BaseModel):
    n_estimators: int = Field(default=200, ge=10)
    validation_quantile: float = Field(default=0.95, gt=0.5, lt=1.0)
    min_prior_tx_for_user_stats: int = Field(default=5, ge=1)
    alert_rate_bounds: tuple[float, float] = (0.01, 0.10)


class RetrainConfig(BaseModel):
    max_mae_regression_ratio: float = Field(default=1.02, ge=1.0)
    min_val_feedback_rows: int = Field(default=10, ge=1)


class PipelineConfig(BaseModel):
    seed: int = 42
    timezone: str = "Asia/Ho_Chi_Minh"
    split_ratios: tuple[float, float, float] = (0.6, 0.2, 0.2)
    currency: CurrencyConfig = Field(default_factory=CurrencyConfig)
    synthetic: SyntheticConfig = Field(default_factory=SyntheticConfig)
    forecast: ForecastConfig = Field(default_factory=ForecastConfig)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)
    retrain: RetrainConfig = Field(default_factory=RetrainConfig)

    @field_validator("split_ratios")
    @classmethod
    def _validate_ratios(cls, v: tuple[float, float, float]) -> tuple[float, float, float]:
        if any(r <= 0 for r in v) or abs(sum(v) - 1.0) > 1e-6:
            raise ValueError("split_ratios must be positive and sum to 1.0")
        return v

    def config_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_config(path: Path = Path("configs/default.yaml")) -> PipelineConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return PipelineConfig.model_validate(raw)
