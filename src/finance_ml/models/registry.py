"""Versioned model bundle serialization and active pointer management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import joblib
import sklearn

from finance_ml.models.anomaly import TrainedAnomalyDetector
from finance_ml.models.forecast import ForecastSelectionOutput
from finance_ml.schema import VN_TZ


@dataclass
class ModelBundle:
    version: str
    dataset_name: str
    selected_forecast_name: str
    forecast_estimator: Any
    all_forecast_models: dict[str, Any]
    anomaly_detector: TrainedAnomalyDetector
    metadata: dict[str, Any]


def save_model_bundle(
    dataset_dir: Path,
    version: str,
    forecast_out: ForecastSelectionOutput,
    anomaly_det: TrainedAnomalyDetector,
    metadata: dict[str, Any],
) -> Path:
    dataset_dir = Path(dataset_dir)
    dataset_name = dataset_dir.name
    bundle_dir = dataset_dir / "models" / version
    bundle_dir.mkdir(parents=True, exist_ok=True)

    full_meta = {
        "version": version,
        "dataset_name": dataset_name,
        "trained_at": datetime.now(timezone.utc).astimezone(VN_TZ).isoformat(),
        "sklearn_version": sklearn.__version__,
        "selected_forecast_name": forecast_out.selected_name,
        "forecast_fallback_used": forecast_out.fallback_used,
        "best_rf_params": forecast_out.best_rf_params,
        "anomaly_threshold": anomaly_det.threshold,
        "anomaly_validation_alert_rate": anomaly_det.validation_alert_rate,
        **metadata,
    }

    bundle = ModelBundle(
        version=version,
        dataset_name=dataset_name,
        selected_forecast_name=forecast_out.selected_name,
        forecast_estimator=forecast_out.selected_estimator,
        all_forecast_models=forecast_out.all_models,
        anomaly_detector=anomaly_det,
        metadata=full_meta,
    )

    joblib.dump(bundle, bundle_dir / "bundle.joblib")
    (bundle_dir / "metadata.json").write_text(
        json.dumps(full_meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return bundle_dir


def set_active_pointer(
    pointer_path: Path,
    bundle_dir: Path,
    version: str,
    dataset_name: str,
) -> None:
    pointer_path = Path(pointer_path)
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "dataset_name": dataset_name,
        "bundle_dir": str(Path(bundle_dir).resolve()),
        "updated_at": datetime.now(timezone.utc).astimezone(VN_TZ).isoformat(),
    }
    pointer_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
