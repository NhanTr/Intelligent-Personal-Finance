"""ML contract-shaped sample responses; no model inference or network calls.

Load the JSON examples shipped with the repository's ML contract. Sample IDs
are remapped to the active wireframe account for D1 UI checks.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from ml_contract import parse_forecast, parse_anomaly_batch, parse_feedback, MLContractError

SAMPLES = Path(__file__).resolve().parents[1] / "contracts" / "samples"


class MockMLContractClient:
    def __init__(self):
        try:
            self._forecast_ok = json.loads((SAMPLES / "forecast_response_ok.json").read_text(encoding="utf-8-sig"))
            self._forecast_short = json.loads((SAMPLES / "forecast_response_insufficient.json").read_text(encoding="utf-8-sig"))
            self._anomaly_ok = json.loads((SAMPLES / "anomaly_response.json").read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise MLContractError("Không đọc được dữ liệu mẫu theo contract ML.") from exc
        self.feedback = {}
        self.simulate_error = False

    def _check(self):
        if self.simulate_error:
            raise MLContractError("Không kết nối được nguồn dữ liệu giả lập.")

    def forecast(self, user_id, scenario="auto"):
        self._check()
        if scenario == "auto":
            scenario = "ok" if user_id == "U001" else "insufficient_data"
        if scenario not in {"ok", "fallback_baseline", "insufficient_data"}:
            raise MLContractError("Kịch bản dự báo không hợp lệ.")
        result = deepcopy(self._forecast_short if scenario == "insufficient_data" else self._forecast_ok)
        result["user_id"] = user_id
        if scenario == "fallback_baseline":
            result.update(status="fallback_baseline", model_name="baseline_last_7d", predicted_total_vnd=900000.0,
                          limitations_note="Kịch bản minh họa: dự báo cơ sở dùng tổng chi 7 ngày gần nhất; số liệu này không phải kết quả suy luận thực tế.")
        return parse_forecast(result, expected_user_id=user_id)

    def anomaly_batch(self, user_id, scenario="auto"):
        self._check()
        if scenario == "auto":
            scenario = "ok" if user_id == "U001" else "empty"
        if scenario not in {"ok", "empty", "model_unavailable"}:
            raise MLContractError("Kịch bản cảnh báo không hợp lệ.")
        result = deepcopy(self._anomaly_ok)
        result["user_id"] = user_id
        if scenario != "ok":
            result.update(items=[], total_evaluated=0, flagged_count=0)
        if scenario == "model_unavailable":
            result.update(status="model_unavailable", threshold=None)
        return parse_anomaly_batch(result, expected_user_id=user_id)

    def save_feedback(self, user_id, transaction_id, is_confirmed_anomaly, batch):
        self._check()
        checked = parse_anomaly_batch(batch, expected_user_id=user_id)
        if checked["status"] != "ok" or not any(item["transaction_id"] == transaction_id and item["is_anomaly"] for item in checked["items"]):
            raise MLContractError("Không tìm thấy cảnh báo phù hợp trong phiên hiện tại.")
        payload = {"transaction_id": transaction_id, "user_id": user_id,
                   "is_confirmed_anomaly": is_confirmed_anomaly,
                   "model_version": checked["model_version"],
                   "created_at": datetime.now(timezone.utc).isoformat()}
        payload = parse_feedback(payload, expected_user_id=user_id)
        self.feedback[(user_id, transaction_id, checked["model_version"])] = payload
        return deepcopy(payload)
