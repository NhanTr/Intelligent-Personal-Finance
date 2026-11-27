"""A reproducible F1–F5 flow on fixed, non-personal data and mock fixtures.

Forecast and anomaly results below are separate static fixtures, not computed ML.
"""
from pathlib import Path
import pandas as pd
from api_client import MockApiClient
from mock_ml_client import MockMLContractClient
from core import savings

ROOT = Path(__file__).resolve().parents[1]


def test_end_to_end_f1_to_f5_with_fixed_mock_data():
    client = MockApiClient()
    # Seven CSV transactions for U001, plus a separate account with the same ID.
    client.transactions = [{"transaction_id": "GD001", "user_id": "U002", "date": "2026-11-01", "type": "expense", "amount": 999, "category": "Ăn uống", "note": ""}]
    data = pd.read_csv(ROOT / "data" / "giao-dich-hop-le.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")

    # F1: import, idempotency, update, scoped filtering and delete.
    assert client.import_transactions("U001", data)["accepted"] == 7
    assert client.import_transactions("U001", data)["accepted"] == 0
    client.add_transaction("U001", {"transaction_id":"FLOW-001", "date":"2026-11-14", "type":"expense", "amount":100000, "category":"Ăn uống", "note":"Bữa trưa"})
    client.update_transaction("U001", "FLOW-001", {"amount":150000, "note":"Đã sửa"})
    selected = client.get_transactions("U001", {"from":"2026-11-14", "to":"2026-11-14", "category":"Ăn uống", "type":"expense"})
    assert len(selected) == 1 and selected[0]["amount"] == 150000
    assert client.get_transactions("U002")[0]["amount"] == 999

    # F2: independently calculated amounts; transfer is excluded.
    stats = client.get_stats("U001")
    assert (stats["income"], stats["expense"], stats["balance"]) == (8000000, 900000, 7100000)
    assert stats["categories"] == {"Ăn uống":450000, "Di chuyển":150000, "Mua sắm":300000}
    client.delete_transaction("U001", "FLOW-001")
    assert client.get_stats("U001")["expense"] == 750000

    # F3/F4: responses are independent contract fixtures, never predictions from the CSV.
    ml = MockMLContractClient()
    prediction = ml.forecast("U001")
    assert (prediction["predicted_total_vnd"], prediction["unit"], prediction["forecast_start_date"], prediction["forecast_end_date"]) == (845000, "VND", "2026-09-16", "2026-09-22")
    assert ml.forecast("U002")["status"] == "insufficient_data"
    batch = ml.anomaly_batch("U001")
    flagged = [item for item in batch["items"] if item["is_anomaly"]]
    assert len(flagged) == 1 and batch["flagged_count"] == 1
    feedback = ml.save_feedback("U001", flagged[0]["transaction_id"], True, batch)
    assert feedback["is_confirmed_anomaly"] is True and feedback["model_version"] == batch["model_version"]

    # F5: independent hand-checked scenario with no interest.
    result = savings(12000000, 2000000, 8000000, 4000000, 3000000)
    assert [x["months"] for x in result] == [10, 8, 7]
    assert [x["monthly"] for x in result] == [1000000, 1300000, 1600000]
