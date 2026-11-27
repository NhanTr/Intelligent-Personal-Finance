from pathlib import Path
from datetime import date
import json
import pandas as pd
import pytest

from api_client import ApiError, MockApiClient
from core import savings, validate

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    return pd.read_csv(ROOT / 'data' / name, dtype=str, keep_default_na=False, encoding='utf-8-sig')


def test_example_csv_produces_hand_checked_dashboard_totals():
    data = read_csv('giao-dich-hop-le.csv')
    _, errors, _ = validate(data, 'U001')
    assert not errors
    client = MockApiClient()
    client.transactions = []
    for record in data.to_dict('records'):
        record['amount'] = int(record['amount'])
        client.add_transaction('U001', record)
    stats = client.get_stats('U001')
    assert (stats['income'], stats['expense'], stats['balance']) == (8_000_000, 750_000, 7_250_000)
    assert stats['categories'] == {'Ăn uống': 300_000, 'Di chuyển': 150_000, 'Mua sắm': 300_000}


def test_csv_error_lines_and_duplicate_fixture():
    _, errors, _ = validate(read_csv('giao-dich-co-loi.csv'), 'U001')
    assert {error['line'] for error in errors} == {2, 3, 4, 5, 6}
    _, errors, _ = validate(read_csv('giao-dich-trung-khoa.csv'), 'U001')
    assert {error['line'] for error in errors} == {2, 3}
    assert all('trùng' in e['message'] for e in errors)


def test_filters_are_inclusive_and_user_scoped():
    client = MockApiClient()
    client.transactions = [
        {'transaction_id': 'a', 'user_id': 'U001', 'date': '2026-11-01', 'type': 'expense', 'amount': 100, 'category': 'Ăn uống', 'note': ''},
        {'transaction_id': 'b', 'user_id': 'U001', 'date': '2026-11-02', 'type': 'expense', 'amount': 300, 'category': 'Ăn uống', 'note': ''},
        {'transaction_id': 'c', 'user_id': 'U001', 'date': '2026-11-02', 'type': 'income', 'amount': 500, 'category': 'Lương', 'note': ''},
        {'transaction_id': 'd', 'user_id': 'U002', 'date': '2026-11-02', 'type': 'expense', 'amount': 9999, 'category': 'Ăn uống', 'note': ''},
    ]
    filters = {'from': '2026-11-01', 'to': '2026-11-02', 'type': 'expense', 'category': 'Ăn uống'}
    assert [row['transaction_id'] for row in client.get_transactions('U001', filters)] == ['a', 'b']
    assert client.get_stats('U001', filters)['expense'] == 400
    assert client.get_stats('U002', filters)['expense'] == 9999


def test_forecast_and_feedback_mock_statuses_are_scoped():
    client = MockApiClient()
    assert client.forecast('U001')['status'] == 'ok'
    assert client.forecast('U002')['status'] == 'insufficient_history'
    alert = client.get_anomalies('U001')[0]
    assert client.save_feedback('U001', alert['transaction_id'], 'correct')['status'] == 'saved_in_mock_session'
    with pytest.raises(ApiError):
        client.save_feedback('U002', alert['transaction_id'], 'correct')


def test_savings_three_scenarios_and_nonpositive_income():
    rows = savings(12_000_000, 2_000_000, 8_000_000, 4_000_000, 3_000_000)
    assert [row['months'] for row in rows] == [10, 8, 7]
    assert [row['monthly'] for row in rows] == [1_000_000, 1_300_000, 1_600_000]
    assert all(row['months'] is None for row in savings(1_000_000, 0, 0, 100_000, 0))
    assert all(row['months'] == 0 for row in savings(0, 0, 0, 0, 0))
    assert len({row['months'] for row in savings(1_000_000, 0, 2_000_000, 1_000_000, 0)}) == 1


def test_ui_add_transaction_rejects_zero_then_updates_session():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('../wireframe_d1.py', default_timeout=10).run()
    app.button[0].click().run()
    app.sidebar.radio[0].set_value('Thu chi').run()
    client = app.session_state['client']
    before = len(client.get_transactions('U001'))
    next(button for button in app.button if button.label == 'Thêm giao dịch').click().run()
    assert len(client.get_transactions('U001')) == before
    assert any('lớn hơn 0' in error.value for error in app.error)
    next(field for field in app.number_input if field.label == 'Số tiền (VND)').set_value(125000)
    next(button for button in app.button if button.label == 'Thêm giao dịch').click().run()
    rows = client.get_transactions('U001')
    assert len(rows) == before + 1
    assert rows[-1]['amount'] == 125000 and rows[-1]['user_id'] == 'U001'
    assert any('Đã thêm giao dịch' in message.value for message in app.success)


def test_ui_edit_preserves_existing_category_not_in_demo_list():
    app = open_demo()
    client = app.session_state['client']
    client.add_transaction('U001', {
        'transaction_id': 'CATEGORY-SAFE-001', 'date': '2026-11-10',
        'type': 'expense', 'amount': 123000, 'category': 'education', 'note': ''
    })
    app.sidebar.radio[0].set_value('Thu chi').run()
    picker = next(x for x in app.selectbox if x.label == 'Chọn giao dịch')
    picker.set_value(next(x for x in picker.options if 'education' in x)).run()
    category = next(x for x in app.selectbox if x.label == 'Danh mục mới')
    assert category.value == 'education'
    next(x for x in app.text_input if x.label == 'Ghi chú mới').set_value('Đã cập nhật')
    next(x for x in app.button if x.label == 'Lưu thay đổi').click().run()
    record = next(x for x in client.get_transactions('U001') if x['transaction_id'] == 'CATEGORY-SAFE-001')
    assert record['category'] == 'education' and record['note'] == 'Đã cập nhật'
    assert not app.exception


def open_demo(user='U001'):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('../wireframe_d1.py', default_timeout=10).run()
    app.selectbox[0].set_value(user)
    app.button[0].click().run()
    return app


def test_ui_dashboard_reconciles_sample_dataset():
    app = open_demo()
    markup = '\n'.join(element.value for element in app.markdown)
    assert '16/10/2026' in markup and '15/11/2026' in markup
    assert '8.000.000 VND' in markup
    assert '3.580.000 VND' in markup
    assert '4.420.000 VND' in markup
    assert not app.exception


def test_dashboard_no_transactions_is_distinct_from_zero_balance():
    app = open_demo('U003')
    markup = '\n'.join(element.value for element in app.markdown)
    assert 'Chưa có giao dịch trong kỳ' in markup
    assert 'Tài khoản này chưa có giao dịch' in markup
    assert 'ledger-summary' not in markup.replace(app.markdown[0].value, '')
    assert any(button.label == 'Thêm giao dịch' for button in app.button)
    assert not app.exception


def test_account_switch_resets_navigation_and_transaction_filters():
    app = open_demo()
    app.sidebar.radio(key="nav").set_value("Thu chi").run()
    assert app.title[0].value == "Giao dịch của bạn"
    app.date_input(key="txend").set_value(date(2026, 10, 31)).run()
    app.selectbox(key="tx_type").set_value("Thu").run()
    app.sidebar.button[0].click().run()
    assert "U003 · tài khoản trống ban đầu" in app.selectbox[0].options
    assert all(key not in app.session_state for key in ("nav", "txend", "tx_type", "dashend"))
    app.selectbox[0].set_value("U002")
    app.button[0].click().run()
    assert app.sidebar.radio(key="nav").value == "Dashboard"
    assert app.title[0].value == "Tổng quan tài chính"
    app.sidebar.radio(key="nav").set_value("Thu chi").run()
    assert app.date_input(key="txend").value == date(2026, 11, 15)
    assert app.selectbox(key="tx_type").value == "Tất cả"
    assert not app.exception


def test_new_transaction_visible_after_save_even_outside_active_filters():
    app = open_demo()
    app.sidebar.radio(key="nav").set_value("Thu chi").run()
    app.selectbox(key="tx_type").set_value("Thu").run()
    next(field for field in app.date_input if field.label == "Ngày giao dịch").set_value(date(2026, 12, 7))
    next(field for field in app.number_input if field.label == "Số tiền (VND)").set_value(125000)
    next(field for field in app.text_input if field.label == "Ghi chú (không bắt buộc)").set_value("Mới <thêm>")
    next(button for button in app.button if button.label == "Thêm giao dịch").click().run()
    assert app.date_input(key="txend").value == date(2026, 12, 7)
    assert app.selectbox(key="tx_type").value == "Tất cả"
    table = next(element.value for element in app.markdown if '<table aria-label="Danh sách giao dịch">' in element.value)
    assert "Mới &lt;thêm&gt;" in table.split("<tr>")[2]
    assert not app.exception


def test_dashboard_chart_and_comparison_table_reconcile_for_both_granularities():
    from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df

    app = open_demo()
    client = app.session_state["client"]
    fixtures = [
        ("week-prior", "2026-11-05", "income", 700),
        ("week-current", "2026-11-08", "expense", 125),
        ("month-prior", "2026-10-31", "expense", 200),
        ("transfer", "2026-11-06", "transfer", 900),
        ("later", "2026-11-11", "expense", 800),
    ]
    client.transactions = [
        {"transaction_id": ident, "user_id": "U001", "date": day, "type": kind, "amount": amount, "category": "Mẫu"}
        for ident, day, kind, amount in fixtures
    ]
    client.transactions.append(dict(client.transactions[0], user_id="U002", amount=999))
    app.date_input(key="dashend").set_value(date(2026, 11, 9)).run()

    for grain, prior, current in (("Tuần", (700, 125), (0, 0)), ("Tháng", (0, 200), (700, 125))):
        app.radio(key="dash_granularity").set_value(grain).run()
        proto = app.get("vega_lite_chart")[0].proto
        spec = json.loads(proto.spec)
        assert spec["mark"]["type"] == "bar" and spec["encoding"]["xOffset"]["field"] == "Loại"
        chart_rows = convert_arrow_bytes_to_pandas_df(proto.datasets[0].data.data).to_dict("records")
        assert {(row["Kỳ"], row["Loại"]): row["Số tiền"] for row in chart_rows} == {
            ("Kỳ trước", "Thu"): prior[0], ("Kỳ trước", "Chi"): prior[1],
            ("Kỳ này", "Thu"): current[0], ("Kỳ này", "Chi"): current[1],
        }
        table = next(element.value for element in app.markdown if '<table aria-label="So sánh thu chi theo kỳ">' in element.value)
        for label, old, new in (
            ("Thu", prior[0], current[0]), ("Chi", prior[1], current[1]),
            ("Chênh lệch", prior[0] - prior[1], current[0] - current[1]),
        ):
            delta = f"{new - old:+d}" if new > old else str(new - old)
            assert (f'<th scope="row">{label}</th><td class="numeric">{old}</td>'
                    f'<td class="numeric">{new}</td><td class="numeric">{delta}</td>') in table
        assert not app.exception


def test_ui_dashboard_explains_largest_increase_without_threshold_claim():
    app = open_demo()
    app.date_input(key="dashstart").set_value(date(2026, 10, 17))
    app.date_input(key="dashend").set_value(date(2026, 11, 16)).run()
    assert any('Không có danh mục nào tăng' in item.value for item in app.caption)
    app.session_state['client'].add_transaction('U001', {
        'transaction_id': 'INCREASE-CHECK', 'date': '2026-11-10',
        'type': 'expense', 'amount': 2_000_000, 'category': 'Y tế', 'note': ''
    })
    app.run()
    assert any('Y tế' in item.value and '+2.000.000 VND' in item.value
               and 'chưa áp dụng ngưỡng' in item.value for item in app.caption)
    assert not app.exception


def test_ui_forecast_seven_days_and_insufficient_history():
    app = open_demo()
    app.sidebar.radio[0].set_value('Dự báo').run()
    assert app.metric[0].value == '845.000 VND'
    assert any('16/09 – 22/09/2026' in element.value for element in app.markdown)
    assert any('MẪU CONTRACT ML' in element.value for element in app.warning)
    assert not app.exception
    other = open_demo('U002')
    other.sidebar.radio[0].set_value('Dự báo').run()
    assert any('chưa đủ lịch sử' in element.value.lower() for element in other.info)
    assert not other.metric and not other.exception


def test_ui_alert_feedback_survives_page_navigation():
    app = open_demo()
    app.sidebar.radio[0].set_value('Cảnh báo').run()
    next(button for button in app.button if button.label == 'Đúng').click().run()
    assert any('Đã ghi trong phiên: Đúng' in message.value for message in app.success)
    app.sidebar.radio[0].set_value('Dashboard').run()
    app.sidebar.radio[0].set_value('Cảnh báo').run()
    assert any('Đã ghi trong phiên: Đúng' in message.value for message in app.success)
    assert not any(button.label in ['Đúng', 'Sai'] for button in app.button)
    assert not app.exception


def test_ui_contract_fallback_and_unavailable_states():
    app = open_demo()
    app.sidebar.radio[0].set_value('Dự báo').run()
    next(x for x in app.sidebar.selectbox if x.label == 'Kịch bản dự báo mẫu').set_value('Dự báo cơ sở').run()
    assert any('Dự báo cơ sở' in item.value for item in app.info)
    assert app.metric[0].value == '900.000 VND'
    app.sidebar.radio[0].set_value('Cảnh báo').run()
    next(x for x in app.sidebar.selectbox if x.label == 'Kịch bản cảnh báo mẫu').set_value('Mô hình chưa sẵn sàng').run()
    assert any('chưa sẵn sàng' in item.value for item in app.info)
    assert not any(button.label in ['Đúng', 'Sai'] for button in app.button)
    assert not app.exception


def test_ui_contract_displays_only_flagged_items():
    app = open_demo()
    app.sidebar.radio[0].set_value('Cảnh báo').run()
    markup = '\n'.join(item.value for item in app.markdown)
    assert 'syn_user_001_00413' not in markup
    assert len([button for button in app.button if button.label in ['Đúng', 'Sai']]) == 2
    assert not app.exception


def test_ui_paginates_large_flagged_batch():
    from copy import deepcopy
    app = open_demo()
    app.sidebar.radio[0].set_value('Cảnh báo').run()
    ml = app.session_state['ml_client']
    item = ml._anomaly_ok['items'][0]
    ml._anomaly_ok['items'] = [dict(deepcopy(item), transaction_id=f'alert-{i:02}') for i in range(11)]
    ml._anomaly_ok['total_evaluated'] = 11
    ml._anomaly_ok['flagged_count'] = 11
    app.run()
    assert len([b for b in app.button if b.label == 'Đúng']) == 10
    next(x for x in app.number_input if x.label == 'Trang cảnh báo').set_value(2).run()
    assert len([b for b in app.button if b.label == 'Đúng']) == 1
    assert not app.exception


def test_unavailable_ml_fixtures_do_not_block_non_ml_pages(monkeypatch):
    import mock_ml_client
    from ml_contract import MLContractError

    def broken_client():
        raise MLContractError('fixture unavailable')

    monkeypatch.setattr(mock_ml_client, 'MockMLContractClient', broken_client)
    app = open_demo()
    assert not app.exception and not app.error
    app.sidebar.radio[0].set_value('Thu chi').run()
    assert not app.exception and not app.error
    app.sidebar.radio[0].set_value('Tiết kiệm').run()
    assert not app.exception and not app.error
    app.sidebar.radio[0].set_value('Dự báo').run()
    assert any('Không tải được dữ liệu mẫu ML' in error.value for error in app.error)
    assert not app.exception


def test_ui_savings_displays_three_correct_scenarios():
    app = open_demo()
    app.sidebar.radio[0].set_value('Tiết kiệm').run()
    markup = '\n'.join(element.value for element in app.markdown)
    assert all(name in markup for name in ['Giữ nguyên', 'Giảm 10% chi tùy chọn', 'Giảm 20% chi tùy chọn'])
    assert [element.value for element in app.metric] == ['10 tháng', '8 tháng', '7 tháng']
    assert not app.exception
