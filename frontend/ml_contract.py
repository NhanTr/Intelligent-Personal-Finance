"""Kiểm tra payload ML trước khi giao diện sử dụng.

Contract là Python/Pydantic giữa ML và backend; module này chỉ kiểm tra JSON
ở biên UI, không gọi mô hình, không suy ra endpoint hoặc xác thực HTTP.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
import math
import re
from typing import Any


class MLContractError(ValueError):
    """Payload không hợp lệ hoặc không thuộc người dùng được yêu cầu."""


def _object(value: Any, field: str) -> dict:
    if not isinstance(value, dict):
        raise MLContractError(f"{field} phải là object JSON")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MLContractError(f"{field} phải là chuỗi không rỗng")
    return value


def _number(value: Any, field: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MLContractError(f"{field} phải là số")
    try:
        valid = math.isfinite(value)
    except (OverflowError, TypeError):
        valid = False
    if not valid or (positive and value <= 0) or (nonnegative and value < 0):
        raise MLContractError(f"{field} nằm ngoài phạm vi hợp lệ")
    return value


def _int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MLContractError(f"{field} phải là số nguyên >= {minimum}")
    return value


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise MLContractError(f"{field} phải có dạng YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise MLContractError(f"{field} không phải ngày hợp lệ") from exc


def _datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        raise MLContractError(f"{field} phải là ISO-8601 datetime có múi giờ")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.utcoffset() is None:
            raise ValueError("missing timezone")
        return result
    except (ValueError, OverflowError) as exc:
        raise MLContractError(f"{field} phải là ISO-8601 datetime có múi giờ") from exc


def _check_user(payload: dict, expected_user_id: str | None) -> None:
    user_id = _string(payload.get("user_id"), "user_id")
    if expected_user_id is not None and user_id != expected_user_id:
        raise MLContractError("user_id không khớp người dùng đang yêu cầu")


def parse_forecast(payload: Any, expected_user_id: str | None = None) -> dict:
    """Trả payload F3 sau kiểm tra; giữ nguyên status và các trường ML.

    ``as_of_date`` là ngày gốc dự báo, không phải thời điểm tạo kết quả.
    Giá trị dự báo thiếu được giữ là None; không tự thay bằng 0.
    """
    payload = _object(payload, "forecast")
    _check_user(payload, expected_user_id)
    status = payload.get("status")
    if status not in ("ok", "fallback_baseline", "insufficient_data"):
        raise MLContractError("status dự báo không hợp lệ")
    as_of = _date(payload.get("as_of_date"), "as_of_date")
    start = _date(payload.get("forecast_start_date"), "forecast_start_date")
    end = _date(payload.get("forecast_end_date"), "forecast_end_date")
    if _int(payload.get("horizon_days"), "horizon_days", minimum=1) != 7:
        raise MLContractError("horizon_days phải bằng 7")
    try:
        expected_start, expected_end = as_of + timedelta(days=1), as_of + timedelta(days=7)
    except OverflowError as exc:
        raise MLContractError("ngày gốc dự báo vượt giới hạn thời gian") from exc
    if start != expected_start or end != expected_end:
        raise MLContractError("khoảng dự báo phải là ngày gốc +1 đến +7")
    if payload.get("unit") != "VND":
        raise MLContractError("đơn vị dự báo phải là VND")
    available = _int(payload.get("days_available"), "days_available")
    required = _int(payload.get("min_days_required"), "min_days_required", minimum=1)
    _string(payload.get("model_name"), "model_name")
    _string(payload.get("model_version"), "model_version")
    _string(payload.get("limitations_note"), "limitations_note")
    if status == "insufficient_data":
        if payload.get("predicted_total_vnd") is not None or available >= required:
            raise MLContractError("trạng thái thiếu dữ liệu phải có giá trị null và lịch sử dưới ngưỡng")
    else:
        _number(payload.get("predicted_total_vnd"), "predicted_total_vnd", nonnegative=True)
        if available < required:
            raise MLContractError("lịch sử không đủ cho kết quả dự báo")
    return deepcopy(payload)


def parse_anomaly_batch(payload: Any, expected_user_id: str | None = None) -> dict:
    """Trả payload F4 hợp lệ. Batch có cả dòng được và không được gắn cờ."""
    payload = _object(payload, "anomaly batch")
    _check_user(payload, expected_user_id)
    status = payload.get("status")
    if status not in ("ok", "model_unavailable"):
        raise MLContractError("status cảnh báo không hợp lệ")
    _string(payload.get("model_version"), "model_version")
    _string(payload.get("disclaimer"), "disclaimer")
    total = _int(payload.get("total_evaluated"), "total_evaluated")
    flagged_count = _int(payload.get("flagged_count"), "flagged_count")
    items = payload.get("items")
    if not isinstance(items, list):
        raise MLContractError("items phải là danh sách")
    threshold = payload.get("threshold")
    if threshold is not None:
        _number(threshold, "threshold")
    if total != len(items):
        raise MLContractError("total_evaluated không khớp items")
    if status == "model_unavailable" and (items or total != 0 or flagged_count != 0 or threshold is not None):
        raise MLContractError("model_unavailable phải có danh sách rỗng và không có ngưỡng")
    ids, actual_flagged = set(), 0
    for index, item in enumerate(items):
        item = _object(item, f"items[{index}]")
        txid = _string(item.get("transaction_id"), f"items[{index}].transaction_id")
        if txid in ids:
            raise MLContractError("transaction_id bị lặp trong batch")
        ids.add(txid)
        _datetime(item.get("timestamp"), f"items[{index}].timestamp")
        _number(item.get("amount_vnd"), f"items[{index}].amount_vnd", positive=True)
        _string(item.get("category"), f"items[{index}].category")
        _number(item.get("anomaly_score"), f"items[{index}].anomaly_score")
        item_threshold = _number(item.get("threshold"), f"items[{index}].threshold")
        if threshold is not None and item_threshold != threshold:
            raise MLContractError("ngưỡng của giao dịch không khớp ngưỡng batch")
        if not isinstance(item.get("is_anomaly"), bool):
            raise MLContractError("is_anomaly phải là boolean")
        reasons = item.get("reasons")
        if not isinstance(reasons, list) or not all(isinstance(r, str) for r in reasons):
            raise MLContractError("reasons phải là danh sách chuỗi")
        actual_flagged += int(item["is_anomaly"])
    if flagged_count != actual_flagged:
        raise MLContractError("flagged_count không khớp items")
    return deepcopy(payload)


def parse_feedback(payload: Any, expected_user_id: str | None = None) -> dict:
    """Kiểm tra năm trường feedback từ backend; không tự tạo created_at."""
    payload = _object(payload, "feedback")
    _check_user(payload, expected_user_id)
    _string(payload.get("transaction_id"), "transaction_id")
    _string(payload.get("model_version"), "model_version")
    if not isinstance(payload.get("is_confirmed_anomaly"), bool):
        raise MLContractError("is_confirmed_anomaly phải là boolean")
    _datetime(payload.get("created_at"), "created_at")
    return deepcopy(payload)
