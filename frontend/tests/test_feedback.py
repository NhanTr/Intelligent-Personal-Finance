import pytest
from api_client import ApiError, MockApiClient


def test_feedback_records_model_version_and_time_in_mock_session():
    client = MockApiClient()
    alert = client.get_anomalies('U001')[0]
    result = client.save_feedback('U001', alert['transaction_id'], 'correct')
    assert result['feedback'] == 'correct'
    assert result['model_version'] == alert['model_version']
    assert result['created_at'].endswith('+00:00')
    assert client.feedback_metadata[('U001', alert['transaction_id'])] == {k:result[k] for k in ('feedback', 'model_version', 'created_at')}
    assert MockApiClient().feedback_metadata == {}


def test_feedback_rejects_invalid_cross_user_and_error():
    client = MockApiClient()
    alert = client.get_anomalies('U001')[0]
    with pytest.raises(ApiError): client.save_feedback('U001', alert['transaction_id'], 'unknown')
    with pytest.raises(ApiError): client.save_feedback('U002', alert['transaction_id'], 'correct')
    client.simulate_error = True
    with pytest.raises(ApiError): client.save_feedback('U001', alert['transaction_id'], 'correct')
    assert not client.feedback and not client.feedback_metadata
