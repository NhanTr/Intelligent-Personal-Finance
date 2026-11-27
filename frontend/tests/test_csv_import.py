import pandas as pd
import pytest

from api_client import ApiError, MockApiClient


def row(transaction_id="IMPORTED-001", **changes):
    data = {"transaction_id": transaction_id, "date": "2026-11-22", "type": "expense", "amount": "150000", "category": "Ăn uống"}
    data.update(changes)
    return data


def test_import_binds_session_and_updates_statistics():
    client = MockApiClient()
    before = client.get_stats("U001")["expense"]
    result = client.import_transactions("U001", pd.DataFrame([row(user_id="U002")]))
    assert result["accepted"] == 1 and not result["errors"] and result["warnings"]
    item = next(x for x in client.get_transactions("U001") if x["transaction_id"] == "IMPORTED-001")
    assert item["user_id"] == "U001" and item["amount"] == 150000 and item["note"] == ""
    assert client.get_stats("U001")["expense"] == before + 150000
    assert not any(x["transaction_id"] == "IMPORTED-001" for x in client.get_transactions("U002"))


def test_invalid_row_is_atomic_and_reports_line():
    client = MockApiClient()
    before = len(client.get_transactions("U001"))
    result = client.import_transactions("U001", pd.DataFrame([row(), row("BAD", amount="150.000")]))
    assert result["accepted"] == 0 and result["errors"][0]["line"] == 3
    assert len(client.get_transactions("U001")) == before


def test_duplicate_inside_file_and_reimport_are_rejected():
    client = MockApiClient()
    duplicate = client.import_transactions("U001", pd.DataFrame([row("  DUP "), row("DUP")]))
    assert duplicate["accepted"] == 0 and {e["line"] for e in duplicate["errors"]} == {2, 3}
    df = pd.DataFrame([row()])
    assert client.import_transactions("U001", df)["accepted"] == 1
    again = client.import_transactions("U001", df)
    assert again["accepted"] == 0 and "trùng" in again["errors"][0]["message"]
    assert client.import_transactions("U002", df)["accepted"] == 1


def test_empty_missing_columns_transfer_and_connection_failure():
    client = MockApiClient()
    assert client.import_transactions("U001", pd.DataFrame())["errors"]
    assert client.import_transactions("U001", pd.DataFrame([{"transaction_id": "X"}]))["errors"]
    before = client.get_stats("U001")
    assert client.import_transactions("U001", pd.DataFrame([row(type="transfer")]))["accepted"] == 1
    after = client.get_stats("U001")
    assert (before["income"], before["expense"]) == (after["income"], after["expense"])
    client.simulate_error = True
    with pytest.raises(ApiError):
        client.import_transactions("U001", pd.DataFrame([row("other")]))
