import copy
import json
from pathlib import Path
import pytest
from ml_contract import MLContractError, parse_anomaly_batch, parse_feedback, parse_forecast

SAMPLES = Path(__file__).resolve().parents[2] / 'contracts' / 'samples'


def sample(filename):
    return json.loads((SAMPLES / filename).read_text(encoding='utf-8'))


def test_forecast_samples_and_baseline_keep_contract_fields():
    ok = sample('forecast_response_ok.json')
    assert parse_forecast(ok, 'user_001') == ok
    insufficient = sample('forecast_response_insufficient.json')
    assert parse_forecast(insufficient)['predicted_total_vnd'] is None
    baseline = dict(ok, status='fallback_baseline', model_name='baseline_last_7d')
    assert parse_forecast(baseline)['status'] == 'fallback_baseline'
    assert 'generated_at' not in parse_forecast(ok)


@pytest.mark.parametrize('change', [
    {'unit':'USD'}, {'horizon_days':30}, {'forecast_start_date':'2026-09-15'},
    {'forecast_end_date':'2026-09-23'}, {'predicted_total_vnd':-1},
    {'predicted_total_vnd':float('nan')}, {'predicted_total_vnd':True},
    {'status':'invalid'}, {'days_available':3}, {'model_version':''},
    {'as_of_date':'2026/09/15'}, {'limitations_note':''},
])
def test_forecast_rejects_bad_payload(change):
    ok = sample('forecast_response_ok.json'); ok.update(change)
    with pytest.raises(MLContractError): parse_forecast(ok)


def test_forecast_insufficient_does_not_invent_zero():
    row = sample('forecast_response_insufficient.json')
    row['predicted_total_vnd'] = 0
    with pytest.raises(MLContractError): parse_forecast(row)
    row['predicted_total_vnd'] = None; row['days_available'] = 28
    with pytest.raises(MLContractError): parse_forecast(row)


def test_anomaly_batch_uses_real_sample_including_nonflagged():
    row = sample('anomaly_response.json')
    result = parse_anomaly_batch(row, 'user_001')
    assert len(result['items']) == 2
    assert [item['is_anomaly'] for item in result['items']] == [True, False]
    assert result['items'][0]['anomaly_score'] == 0.11842
    assert result['items'][1]['anomaly_score'] == -0.0841
    result['items'].clear()
    assert len(row['items']) == 2


def test_anomaly_unavailable_and_empty_ok_are_distinct():
    row = sample('anomaly_response.json')
    row.update(status='model_unavailable', items=[], total_evaluated=0, flagged_count=0, threshold=None)
    assert parse_anomaly_batch(row)['status'] == 'model_unavailable'
    row.update(status='ok', threshold=0.04215)
    assert parse_anomaly_batch(row)['status'] == 'ok'


@pytest.mark.parametrize('change', [
    {'status':'unknown'}, {'flagged_count':2}, {'total_evaluated':1},
    {'items':'wrong'}, {'model_version':''}, {'threshold':float('nan')},
])
def test_anomaly_rejects_bad_batch(change):
    row = sample('anomaly_response.json'); row.update(change)
    with pytest.raises(MLContractError): parse_anomaly_batch(row)


@pytest.mark.parametrize('field,value', [
    ('amount_vnd', 0), ('anomaly_score', float('inf')), ('is_anomaly', 'true'),
    ('timestamp','2026-09-14T19:30:00'), ('reasons','wrong'), ('threshold', 0.5),
])
def test_anomaly_rejects_bad_item(field, value):
    row = sample('anomaly_response.json'); row['items'][0][field] = value
    with pytest.raises(MLContractError): parse_anomaly_batch(row)


def test_user_scope_and_feedback_timestamp():
    with pytest.raises(MLContractError): parse_anomaly_batch(sample('anomaly_response.json'), 'someone_else')
    row = dict(transaction_id='t01', user_id='user_001', is_confirmed_anomaly=False, model_version='v1.0.0', created_at='2026-11-26T10:00:00+07:00')
    assert parse_feedback(row, 'user_001') == row
    for field, invalid in [('is_confirmed_anomaly', 'false'), ('model_version', ''), ('created_at', None), ('created_at', '2026-11-26T10:00:00')]:
        bad = copy.deepcopy(row); bad[field] = invalid
        with pytest.raises(MLContractError): parse_feedback(bad)
