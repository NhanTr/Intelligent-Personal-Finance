import copy
from datetime import datetime
import pytest
from api_client import ApiError, MockApiClient
from contract_adapter import AdapterError, CATEGORY_LABELS, to_ml_transaction, from_ml_transaction
from core import money


def row(**kwargs):
    return {'transaction_id':'x', 'user_id':'U001', 'date':'2026-11-01', 'type':'expense', 'amount':150000, 'category':'Ăn uống', 'note':'', **kwargs}


def test_categories_are_complete_and_resolve_both_ways():
    assert len(CATEGORY_LABELS) == 12
    for code, label in CATEGORY_LABELS.items():
        kind = 'transfer' if code == 'transfer' else 'expense'
        result = to_ml_transaction(row(category=label, type=kind), assume_midnight=True, transfer_direction='expense')
        assert result['category'] == code
        assert from_ml_transaction(result)['category'] == label


def test_date_only_and_transfer_require_explicit_assumptions():
    with pytest.raises(AdapterError): to_ml_transaction(row())
    with pytest.raises(AdapterError): to_ml_transaction(row(type='transfer', category='Chuyển nội bộ'), assume_midnight=True)
    with pytest.raises(AdapterError): to_ml_transaction(row(type='transfer', category='Ăn uống'), assume_midnight=True, transfer_direction='expense')
    result = to_ml_transaction(row(type='transfer', category='Chuyển nội bộ'), assume_midnight=True, transfer_direction='income')
    assert result['timestamp'].endswith('T00:00:00+07:00') and result['type'] == 'income' and result['is_internal_transfer']
    assert from_ml_transaction(result)['transfer_direction'] == 'income'


def test_timestamp_is_preserved_and_unknown_fields_not_guessed():
    item = row(timestamp='2026-11-01T18:35:00+07:00')
    assert to_ml_transaction(item)['timestamp'].endswith('T18:35:00+07:00')
    with pytest.raises(AdapterError): to_ml_transaction(row(timestamp='2026-11-01T18:35:00'))
    with pytest.raises(AdapterError): to_ml_transaction(row(timestamp='2026-11-02T00:00:00+07:00'))
    with pytest.raises(AdapterError): to_ml_transaction(row(category='not-a-category'), assume_midnight=True)
    with pytest.raises(AdapterError): to_ml_transaction(row(amount='150.000'), assume_midnight=True)
    with pytest.raises(AdapterError): from_ml_transaction({'transaction_id':'x','user_id':'U001','timestamp':'2026-11-01T00:00:00+07:00','type':'expense','amount_vnd':1.5,'category':'food','is_internal_transfer':False})


@pytest.mark.parametrize('patch', [{'amount':-2}, {'amount':0}, {'amount':'150.000'}, {'date':'bad'}, {'type':'wrong'}, {'category':''}])
def test_mock_add_update_reject_bad_values_without_mutation(patch):
    client=MockApiClient()
    before=copy.deepcopy(client.transactions)
    with pytest.raises(ApiError): client.add_transaction('U001', {**row(), **patch})
    assert client.transactions == before
    tx = client.get_transactions('U001')[0]
    with pytest.raises(ApiError): client.update_transaction('U001', tx['transaction_id'], patch)
    assert client.transactions == before


def test_mock_duplicate_add_and_rounding():
    client=MockApiClient()
    tx=client.get_transactions('U001')[0]
    with pytest.raises(ApiError): client.add_transaction('U001',tx)
    assert money(3937556.5) == '3.937.557 VND'
    assert money(-2.5) == '-3 VND'
