import copy
import pytest
from api_client import ApiError, MockApiClient

@pytest.mark.parametrize("field, value", [("unit", "USD"), ("value", -1), ("value", "1200"), ("to", "2026-11-23"), ("generated_at", "2026-11-16T09:00:00"), ("model_version", ""), ("used_fallback", "yes")])
def test_forecast_rejects_bad_contract(field, value):
    client = MockApiClient()
    client.forecasts["U001"] = copy.deepcopy(client.forecasts["U001"])
    client.forecasts["U001"][field] = value
    with pytest.raises(ApiError):
        client.forecast("U001")

def test_forecast_valid_and_insufficient():
    client = MockApiClient()
    result = client.forecast("U001")
    assert result["unit"] == "VND" and result["from"] == "2026-11-16" and result["to"] == "2026-11-22"
    assert client.forecast("U002")["status"] == "insufficient_history"
