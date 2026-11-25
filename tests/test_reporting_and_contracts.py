import json
from pathlib import Path
import pandas as pd
from finance_ml.schema import ForecastResult, AnomalyBatchResult
from finance_ml.reporting.review_export import export_manual_review_sample


def test_manual_review_export_has_top30_and_random30_with_reviewer_columns(tmp_path: Path):
    df = pd.DataFrame([
        {
            "transaction_id": f"tx_{i}",
            "user_id": "user_001",
            "timestamp": f"2026-08-{(i % 28) + 1:02d}T12:00:00+07:00",
            "amount_vnd": float((i + 1) * 10000),
            "category": "shopping",
            "anomaly_score": float(i) / 100.0,
            "is_anomaly": i >= 85,
            "reasons": ["Cao bất thường"] if i >= 85 else [],
        }
        for i in range(100)
    ])
    out_csv = export_manual_review_sample(df, tmp_path / "review.csv", top_k=30, random_k=30, seed=42)
    saved = pd.read_csv(out_csv)
    assert len(saved) == 60
    assert {"sample_group", "khoa_label", "duy_label", "reviewer_notes"}.issubset(saved.columns)
    assert (saved["sample_group"] == "top_alert").sum() == 30
    assert (saved["sample_group"] == "random_sample").sum() == 30


def test_contract_sample_jsons_validate_against_pydantic_schemas():
    ok = json.loads(Path("contracts/samples/forecast_response_ok.json").read_text(encoding="utf-8"))
    insuf = json.loads(Path("contracts/samples/forecast_response_insufficient.json").read_text(encoding="utf-8"))
    anom = json.loads(Path("contracts/samples/anomaly_response.json").read_text(encoding="utf-8"))
    ForecastResult.model_validate(ok)
    ForecastResult.model_validate(insuf)
    AnomalyBatchResult.model_validate(anom)
