"""Contract behavior of the session-local ML mock, not real ML inference."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pytest
from ml_contract import MLContractError
from mock_ml_client import MockMLContractClient

SAMPLES = Path(__file__).resolve().parents[2] / 'contracts' / 'samples'


def read_sample(filename):
    return json.loads((SAMPLES / filename).read_text(encoding='utf-8-sig'))


def test_forecast_ok_is_contract_sample_with_demo_user_remapped_only():
    client = MockMLContractClient()
    source = read_sample('forecast_response_ok.json')
    result = client.forecast('U001')
    assert result == {**source, 'user_id': 'U001'}
    assert result['status'] == 'ok' and result['unit'] == 'VND'
    assert result['forecast_start_date'] == '2026-09-16'
    assert result['forecast_end_date'] == '2026-09-22'
    assert result['predicted_total_vnd'] == 845000.0
    assert client._forecast_ok == source


def test_forecast_three_states_are_explicit_and_isolated():
    client = MockMLContractClient()
    insufficient = client.forecast('U002', 'insufficient_data')
    baseline = client.forecast('U001', 'fallback_baseline')
    ok = client.forecast('U001', 'ok')
    assert insufficient == {**read_sample('forecast_response_insufficient.json'), 'user_id': 'U002'}
    assert insufficient['predicted_total_vnd'] is None
    assert baseline['status'] == 'fallback_baseline' and baseline['model_name'] == 'baseline_last_7d'
    assert 'minh họa' in baseline['limitations_note']
    assert ok['status'] == 'ok' and ok['model_name'] != baseline['model_name']
    assert client.forecast('U003')['status'] == 'insufficient_data'
    with pytest.raises(MLContractError): client.forecast('U001', 'not_a_status')


def test_anomaly_samples_preserve_flags_counts_and_do_not_mix_identities():
    client = MockMLContractClient()
    source = read_sample('anomaly_response.json')
    first = client.anomaly_batch('U001', 'ok')
    other = client.anomaly_batch('U002', 'ok')
    assert first == {**source, 'user_id': 'U001'}
    assert other == {**source, 'user_id': 'U002'}
    assert first['total_evaluated'] == 2 and first['flagged_count'] == 1
    assert [item['is_anomaly'] for item in first['items']] == [True, False]
    first['items'][0]['reasons'].clear()
    assert client.anomaly_batch('U001', 'ok')['items'][0]['reasons'] == source['items'][0]['reasons']
    assert client._anomaly_ok == source


def test_anomaly_empty_vs_unavailable_are_not_conflated():
    client = MockMLContractClient()
    empty = client.anomaly_batch('U002', 'empty')
    unavailable = client.anomaly_batch('U002', 'model_unavailable')
    assert empty['status'] == 'ok' and empty['items'] == [] and empty['flagged_count'] == 0
    assert unavailable['status'] == 'model_unavailable' and unavailable['items'] == []
    assert unavailable['threshold'] is None and unavailable['total_evaluated'] == 0
    with pytest.raises(MLContractError): client.anomaly_batch('U001', 'unknown')


@pytest.mark.parametrize('answer', [True, False])
def test_feedback_five_contract_fields_and_session_isolation(answer):
    client = MockMLContractClient()
    batch = client.anomaly_batch('U001', 'ok')
    tx_id = next(item['transaction_id'] for item in batch['items'] if item['is_anomaly'])
    result = client.save_feedback('U001', tx_id, answer, batch)
    assert set(result) == {'transaction_id', 'user_id', 'is_confirmed_anomaly', 'model_version', 'created_at'}
    assert result['transaction_id'] == tx_id and result['user_id'] == 'U001'
    assert result['is_confirmed_anomaly'] is answer and result['model_version'] == batch['model_version']
    assert datetime.fromisoformat(result['created_at']).utcoffset() is not None
    assert client.feedback[('U001', tx_id, batch['model_version'])] == result
    assert MockMLContractClient().feedback == {}
    result['model_version'] = 'tampered'
    assert client.feedback[('U001', tx_id, batch['model_version'])]['model_version'] == batch['model_version']


def test_feedback_rejects_wrong_user_unflagged_and_bad_value():
    client = MockMLContractClient()
    batch = client.anomaly_batch('U001', 'ok')
    flagged = next(item['transaction_id'] for item in batch['items'] if item['is_anomaly'])
    normal = next(item['transaction_id'] for item in batch['items'] if not item['is_anomaly'])
    with pytest.raises(MLContractError): client.save_feedback('U002', flagged, True, batch)
    with pytest.raises(MLContractError): client.save_feedback('U001', normal, True, batch)
    with pytest.raises(MLContractError): client.save_feedback('U001', flagged, 'true', batch)
    assert client.feedback == {}


def test_simulated_error_prevents_reads_and_feedback():
    client = MockMLContractClient()
    batch = client.anomaly_batch('U001', 'ok')
    flagged = next(item['transaction_id'] for item in batch['items'] if item['is_anomaly'])
    client.simulate_error = True
    for operation in (
        lambda: client.forecast('U001'),
        lambda: client.anomaly_batch('U001'),
        lambda: client.save_feedback('U001', flagged, True, batch),
    ):
        with pytest.raises(MLContractError): operation()
    assert client.feedback == {}
