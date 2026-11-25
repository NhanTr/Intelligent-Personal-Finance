# Hợp đồng Tích hợp Học máy (ML Integration Contract — K3 & D3)

Tài liệu này khóa giao diện giữa package `finance_ml` (Nhân), backend `FastAPI` (Khoa — `K2/K3`) và giao diện `Streamlit` (Duy — `D2/D3`).

---

## 1. Môi trường & Khóa Phiên bản Thư viện

- **Python:** `3.12.x`
- **Cài đặt đồng bộ:** Cài đúng danh sách pin cứng trong `requirements-ml.txt` (`scikit-learn==1.9.1`, `pandas==2.3.3`, `numpy==2.5.5`, `joblib==1.6.0`, `pydantic==2.14.4`) và cài package `pip install --no-deps -e .` để đảm bảo nạp `.joblib` không lệch phiên bản.
- **Nạp mô hình 1 lần khi khởi động FastAPI:**

```python
from pathlib import Path
from finance_ml.inference.loader import ModelBundleLoader

# Nạp 1 lần trong lifespan/startup của FastAPI; tự động fallback về Baseline nếu thiếu file model
ML_BUNDLE = ModelBundleLoader(Path("artifacts/models/active.json"), allow_baseline_fallback=True).load()
```

---

## 2. API Python Suy luận cho Khoa (`FastAPI`)

### 2.1. F3 — Dự báo tổng chi 7 ngày tiếp theo

```python
from datetime import date
import pandas as pd
from finance_ml.inference.predictor import predict_next_7d

result = predict_next_7d(
    transactions_df=user_tx_df,          # DataFrame giao dịch của user_id lấy từ SQLite
    user_id="user_001",
    as_of_date=date(2026, 9, 15),
    bundle=ML_BUNDLE,
    tracking_start_date=None,            # Tùy chọn: truyền ngày tạo tài khoản nếu DB có lưu
)
payload_dict = result.model_dump(mode="json")
```

**Các trạng thái `status` trả về cho UI của Duy (`D3`):**
- `"ok"`: Dự báo thành công từ mô hình đã chọn trên validation (`predicted_total_vnd` là số thực `>= 0`, đơn vị `"VND"`).
- `"fallback_baseline"`: Đang trả dự báo bằng tổng chi 7 ngày gần nhất (`baseline_last_7d`) do chưa có file model hoặc mô hình ML không vượt baseline.
- `"insufficient_data"`: Người dùng có `< 28` ngày lịch sử (`predicted_total_vnd = null`, kèm `days_available` và `min_days_required = 28`). UI hiển thị rõ thông báo chưa đủ lịch sử thay vì vẽ số `0`.

### 2.2. F4 — Chấm điểm bất thường giao dịch & Giải thích ngữ cảnh

```python
from finance_ml.inference.predictor import detect_anomalies

batch = detect_anomalies(
    transactions_df=user_tx_df,          # Toàn bộ lịch sử của user để tính đặc trưng nhân quả chính xác
    user_id="user_001",
    bundle=ML_BUNDLE,
    target_transaction_ids=None,         # Hoặc truyền danh sách ID mới nhập để chỉ lấy kết quả các dòng đó
)
payload_dict = batch.model_dump(mode="json")
```

**Các trạng thái `status` trả về:**
- `"ok"`: Trả danh sách `items`, mỗi phần tử gồm `anomaly_score`, `threshold`, `is_anomaly` và `reasons: list[str]` (tiếng Việt giải thích lý do để UI hiển thị kèm nút xác nhận **Đúng / Sai**).
- `"model_unavailable"`: File model chưa sẵn sàng; trả danh sách rỗng an toàn, không làm lỗi luồng thêm giao dịch.

---

## 3. Lưu Phản hồi & Huấn luyện lại (`Feedback Loop`)

Khi người dùng bấm xác nhận cảnh báo đúng/sai trên UI (`D3`), backend của Khoa (`K3`) lưu bảng phản hồi với đúng 5 trường:
- `transaction_id` (`str`)
- `user_id` (`str`)
- `is_confirmed_anomaly` (`bool`: `true` nếu người dùng xác nhận đúng là bất thường, `false` nếu báo nhầm)
- `model_version` (`str`: lấy từ `AnomalyBatchResult.model_version`)
- `created_at` (`ISO-8601 datetime`)

Khi cần huấn luyện lại mô hình từ dữ liệu cập nhật + file CSV phản hồi xuất từ DB, chạy:

```bash
uv run python scripts/retrain.py \
  --dataset synthetic \
  --version v1.1.0 \
  --feedback-csv path/to/feedback.csv
```

Script tự động kiểm định phiên bản mới so với phiên bản đang chạy trên **cùng cửa sổ validation mới** và chỉ cập nhật `artifacts/models/active.json` nếu vượt qua cổng chất lượng.

---

## 4. Tệp JSON Mẫu (`contracts/samples/`)

Duy (`D1–D3`) và Khoa (`K1–K3`) có thể dùng trực tiếp các mẫu JSON đã kiểm tra hợp lệ bằng Pydantic tại:
- `contracts/samples/forecast_request.json`
- `contracts/samples/forecast_response_ok.json`
- `contracts/samples/forecast_response_insufficient.json`
- `contracts/samples/anomaly_request.json`
- `contracts/samples/anomaly_response.json`
