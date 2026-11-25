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


def test_eda_report_preserves_existing_stream_section_without_dotfile_cache(tmp_path: Path):
    from datetime import date
    from finance_ml.data.cleaning import clean_transactions
    from finance_ml.data.daily import aggregate_daily_spending
    from finance_ml.reporting.eda import generate_eda_artifacts
    from finance_ml.schema import DataManifest, ProfileWindow

    raw = pd.DataFrame([
        {"transaction_id": "t1", "user_id": "u1", "timestamp": "2026-01-01T10:00:00+07:00", "type": "expense", "amount_vnd": 123456.0, "category": "food", "is_internal_transfer": False}
    ])
    clean_df, _ = clean_transactions(raw)
    daily_df = aggregate_daily_spending(clean_df, {"u1": ProfileWindow(user_id="u1", tracking_start_date=date(2026, 1, 1), tracking_end_date=date(2026, 1, 2))})
    report_md = tmp_path / "docs" / "eda_report.md"

    m_syn = DataManifest(
        dataset_name="syn", source_type="synthetic", source_url_or_generator="gen", usage_terms="demo",
        generated_or_fetched_at="2026-11-25", version="1.0", seed=42, profile_count=1,
        min_date=date(2026, 1, 1), max_date=date(2026, 1, 2), total_transactions=1,
    )
    generate_eda_artifacts("synthetic", clean_df, daily_df, m_syn, tmp_path / "figs_syn", report_md)
    dotfile = report_md.parent / ".eda_sections.json"
    if dotfile.exists():
        dotfile.unlink()

    m_pub = DataManifest(
        dataset_name="pub", source_type="real_public", source_url_or_generator="kaggle", usage_terms="open",
        generated_or_fetched_at="2026-11-25", version="1.0", seed=None, profile_count=1,
        min_date=date(2026, 1, 1), max_date=date(2026, 1, 2), total_transactions=1,
    )
    generate_eda_artifacts("real_public", clean_df, daily_df, m_pub, tmp_path / "figs_pub", report_md)
    text = report_md.read_text(encoding="utf-8")
    assert "Chưa chạy EDA cho luồng này" not in text
    assert "gen" in text and "kaggle" in text
