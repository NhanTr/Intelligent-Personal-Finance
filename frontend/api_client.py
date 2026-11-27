import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from core import validate

ROOT = Path(__file__).parent

class ApiError(Exception):
    pass

class MockApiClient:
    """Mock thu chi theo phiên; các hàm ML cũ chỉ giữ cho kiểm thử lịch sử.

    F3/F4 của giao diện dùng MockMLContractClient; không dùng các hàm legacy
    này làm contract cho backend thật.
    """
    def __init__(self):
        try:
            self.transactions = json.loads((ROOT / "fixtures" / "transactions.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ApiError(f"Không đọc được dữ liệu giả lập: {e}") from e
        self._forecasts = None
        self._anomalies = None
        self.feedback = {}
        self.feedback_metadata = {}
        self.simulate_error = False

    def _legacy_fixture(self, name):
        try:
            return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ApiError(f"Không đọc được dữ liệu ML giả lập phiên bản cũ: {e}") from e

    @property
    def forecasts(self):
        """Legacy fixture, not used by current F3 UI."""
        if self._forecasts is None:
            self._forecasts = self._legacy_fixture("forecast.json")
        return self._forecasts

    @property
    def anomalies(self):
        """Legacy fixture, not used by current F4 UI."""
        if self._anomalies is None:
            self._anomalies = self._legacy_fixture("anomalies.json")
        return self._anomalies

    def check_error(self):
        if self.simulate_error:
            raise ApiError("Lỗi kết nối giả lập để kiểm tra giao diện.")

    def get_transactions(self, user_id, filters=None):
        self.check_error()
        rows = [x.copy() for x in self.transactions if x["user_id"] == user_id]
        filters = filters or {}
        return [x for x in rows if (not filters.get("type") or x["type"] == filters["type"]) and (not filters.get("from") or x["date"] >= filters["from"]) and (not filters.get("to") or x["date"] <= filters["to"]) and (not filters.get("category") or x["category"] == filters["category"])]

    def add_transaction(self, user_id, item):
        self.check_error()
        existing = [x['transaction_id'] for x in self.transactions if x['user_id'] == user_id]
        item = self._validate_transaction(user_id, item, existing)
        self.transactions.append(item)

    def _validate_transaction(self, user_id, item, existing=()):
        if not isinstance(user_id, str) or not user_id.strip() or not isinstance(item, dict):
            raise ApiError('Thiếu tài khoản hoặc dữ liệu giao dịch không hợp lệ.')
        fields = {key: item[key] for key in ('transaction_id', 'date', 'type', 'amount', 'category', 'note') if key in item}
        for key in ('transaction_id', 'date', 'type', 'category'):
            if isinstance(fields.get(key), str): fields[key] = fields[key].strip()
        data, errors, _ = validate(pd.DataFrame([fields]), user_id, existing)
        if errors:
            raise ApiError('Dữ liệu giao dịch không hợp lệ: ' + errors[0]['message'])
        record = data.iloc[0].to_dict()
        record['amount'] = int(str(record['amount']).strip())
        record['note'] = '' if pd.isna(record.get('note')) else str(record.get('note', ''))
        return record

    def import_transactions(self, user_id, dataframe):
        """Validate and import all rows atomically into the mock session.

        User identity always comes from the caller's demo session, never the CSV.
        This method simulates application behaviour, not backend authorization.
        """
        self.check_error()
        if dataframe.empty:
            return {"accepted": 0, "errors": [{"line": "file", "message": "File không có dòng dữ liệu."}], "warnings": []}

        data = dataframe.copy()
        for field in ("transaction_id", "date", "type", "category"):
            if field in data:
                data[field] = data[field].map(lambda value: value.strip() if isinstance(value, str) else value)
        existing = [str(item["transaction_id"]).strip() for item in self.transactions if item["user_id"] == user_id]
        normalized, errors, warnings = validate(data, user_id, existing)
        if errors:
            return {"accepted": 0, "errors": errors, "warnings": warnings}

        rows = []
        for item in normalized.to_dict(orient="records"):
            note = item.get("note", "")
            rows.append({
                "transaction_id": item["transaction_id"],
                "user_id": user_id,
                "date": item["date"],
                "type": item["type"],
                "amount": int(str(item["amount"]).strip()),
                "category": item["category"],
                "note": "" if pd.isna(note) else str(note),
            })
        self.transactions.extend(rows)
        return {"accepted": len(rows), "errors": [], "warnings": warnings}

    def update_transaction(self, user_id, transaction_id, fields):
        self.check_error()
        allowed = {"date", "type", "amount", "category", "note"}
        for item in self.transactions:
            if item["user_id"] == user_id and item["transaction_id"] == transaction_id:
                if not isinstance(fields, dict):
                    raise ApiError('Dữ liệu cập nhật không hợp lệ.')
                proposed = {**item, **{key: value for key, value in fields.items() if key in allowed}}
                validated = self._validate_transaction(user_id, proposed)
                item.update(validated)
                return item.copy()
        raise ApiError("Không tìm thấy giao dịch thuộc tài khoản hiện tại.")

    def delete_transaction(self, user_id, transaction_id):
        self.check_error()
        for i, item in enumerate(self.transactions):
            if item["user_id"] == user_id and item["transaction_id"] == transaction_id:
                del self.transactions[i]
                return
        raise ApiError("Không tìm thấy giao dịch thuộc tài khoản hiện tại.")

    def get_stats(self, user_id, filters=None):
        rows = self.get_transactions(user_id, filters)
        income = sum(x["amount"] for x in rows if x["type"] == "income")
        expense = sum(x["amount"] for x in rows if x["type"] == "expense")
        spend = [x for x in rows if x["type"] == "expense"]
        categories, weeks = {}, {}
        for x in spend:
            categories[x["category"]] = categories.get(x["category"], 0) + x["amount"]
            week = str(pd.Timestamp(x["date"]).to_period("W"))
            weeks[week] = weeks.get(week, 0) + x["amount"]
        return {"income": income, "expense": expense, "balance": income-expense, "categories": categories, "weeks": dict(sorted(weeks.items()))}

    def forecast(self, user_id):
        self.check_error()
        result = self.forecasts.get(user_id, {"status": "insufficient_history", "min_days": 28}).copy()
        if result.get("status") == "insufficient_history":
            return result
        if result.get("status") != "ok":
            raise ApiError("Trạng thái dự báo không hợp lệ.")
        try:
            amount = result["value"]
            if isinstance(amount, bool) or not isinstance(amount, (float, int)) or not (0 <= amount < float("inf")):
                raise ValueError("value")
            if result["unit"] != "VND":
                raise ValueError("unit")
            start, end = pd.Timestamp(result["from"]), pd.Timestamp(result["to"])
            generated = pd.Timestamp(result["generated_at"])
            if pd.isna(start) or pd.isna(end) or pd.isna(generated) or (end - start).days != 6 or generated.tzinfo is None:
                raise ValueError("dates")
            if not isinstance(result["used_fallback"], bool) or not result["model_version"]:
                raise ValueError("model metadata")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ApiError("Dữ liệu dự báo không đầy đủ hoặc sai đơn vị, thời gian.") from exc
        return result

    def get_anomalies(self, user_id):
        self.check_error()
        return [x for x in self.anomalies if x["user_id"] == user_id]

    def save_feedback(self, user_id, transaction_id, value):
        if value not in ("correct", "incorrect"):
            raise ApiError("Phản hồi không hợp lệ.")
        alert = next((x for x in self.get_anomalies(user_id) if x["transaction_id"] == transaction_id), None)
        if alert is None:
            raise ApiError("Không tìm thấy cảnh báo thuộc phiên hiện tại.")
        key = (user_id, transaction_id)
        self.feedback[key] = value
        self.feedback_metadata[key] = {
            "feedback": value,
            "model_version": alert.get("model_version"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": "saved_in_mock_session", **self.feedback_metadata[key]}
