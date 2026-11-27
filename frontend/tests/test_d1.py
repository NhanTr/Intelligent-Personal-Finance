import pandas as pd
from core import validate, savings, money
from api_client import MockApiClient

def sample():
    return pd.DataFrame([dict(transaction_id="NEW", date="2026-11-01", type="expense", amount=100, category="Ăn uống")])

def test_optional_note_and_user_scope():
    df = sample(); df["user_id"] = "U002"
    normalized, errors, warnings = validate(df, "U001")
    assert not errors and warnings and normalized.loc[0, "user_id"] == "U001" and normalized.loc[0, "note"] == ""

def test_duplicate_and_bad_amount():
    df = pd.concat([sample(), sample()], ignore_index=True); df.loc[0, "amount"] = -1
    _, errors, _ = validate(df, "U001")
    assert len(errors) == 2 and "trùng" in errors[1]["message"]

def test_transfer_and_scope():
    client = MockApiClient()
    assert all(x["user_id"] == "U001" for x in client.get_transactions("U001"))
    before = client.get_stats("U001")
    client.add_transaction("U001", dict(transaction_id="t", date="2026-11-01", type="transfer", amount=999, category="Chuyển nội bộ", note=""))
    after = client.get_stats("U001")
    assert (before["income"], before["expense"]) == (after["income"], after["expense"])

def test_legacy_ml_fixtures_do_not_block_transactions(monkeypatch):
    import pytest
    from api_client import ApiError

    def broken_legacy(*_args):
        raise ApiError('legacy fixture unavailable')

    monkeypatch.setattr(MockApiClient, '_legacy_fixture', broken_legacy)
    client = MockApiClient()
    assert client.get_transactions('U001')
    with pytest.raises(ApiError):
        client.forecast('U001')

def test_savings():
    assert [x["months"] for x in savings(12000000,2000000,8000000,4000000,3000000)] == [10,8,7]
    assert savings(12000000,2000000,8000000,4000000,2000000)[0]["months"] == 5
    assert savings(1,1,0,0,0)[0]["months"] == 0
    assert savings(1,0,0,0,0)[0]["months"] is None
    assert money(8000000) == "8.000.000 VND"

def test_ui_smoke():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file("../wireframe_d1.py", default_timeout=20).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception


def test_all_pages():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file("../wireframe_d1.py", default_timeout=20).run()
    app.button[0].click().run()
    assert app.sidebar.radio[0].options == ["Dashboard", "Thu chi", "Dự báo", "Cảnh báo", "Tiết kiệm"]
    for name in ["Dashboard", "Dự báo", "Cảnh báo", "Tiết kiệm", "Thu chi"]:
        app.sidebar.radio[0].set_value(name).run()
        assert not app.exception, name
    app.sidebar.checkbox[0].check().run()
    assert app.error and not app.exception


def test_amount_text_must_be_plain_digits():
    for value in ["1.000", "150.000", "1,000", "1.5", "1e3", "+100", "0", "-1"]:
        df = sample(); df["amount"] = value
        _, errors, _ = validate(df, "U001")
        assert errors, value
    for value in ["150000", " 100 "]:
        df = sample(); df["amount"] = value
        _, errors, _ = validate(df, "U001")
        assert not errors, value


def test_mock_edit_delete_user_scope():
    import pytest
    from api_client import ApiError
    client = MockApiClient()
    txn = client.get_transactions("U001")[0]
    ident = txn["transaction_id"]
    with pytest.raises(ApiError):
        client.update_transaction("U002", ident, {"amount": 1})
    with pytest.raises(ApiError):
        client.delete_transaction("U002", ident)
    client.update_transaction("U001", ident, {"amount": 10, "user_id": "U002"})
    assert client.get_transactions("U001")[0]["amount"] == 10
    client.delete_transaction("U001", ident)
    assert all(row["transaction_id"] != ident for row in client.get_transactions("U001"))

def test_weeks_are_chronological_after_backdated_and_future_transactions():
    client = MockApiClient()
    for tid, when in [("newer", "2026-12-01"), ("older", "2026-01-01")]:
        client.add_transaction("U001", {"transaction_id":tid, "date":when, "type":"expense", "amount":1000, "category":"Ăn uống", "note":""})
    weeks = list(client.get_stats("U001")["weeks"])
    assert weeks == sorted(weeks)
    assert weeks[0].startswith("2025-12-29")
    assert weeks[-1].startswith("2026-11-30")


def test_savings_whole_month_boundary():
    # The 10% scenario saves exactly 0.1 VND a month; float math gave 11.
    assert savings(1, 0, 1, 0, 1)[1]["months"] == 10
    assert savings(10000000, 0, 10000000, 0, 10000000)[1]["months"] == 10
