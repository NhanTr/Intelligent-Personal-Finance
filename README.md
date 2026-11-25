# Intelligent Personal Finance Decision Support System — Data & ML Package (`N1–N4`)

Gói dữ liệu, đặc trưng nhân quả, huấn luyện/đánh giá mô hình (`F3` Dự báo chi tiêu 7 ngày & `F4` Phát hiện giao dịch bất thường bằng `IsolationForest`) và hợp đồng tích hợp cho dự án môn **Phát triển hệ thống thông minh**.

---

## 1. Yêu cầu Hệ thống & Cài đặt trên Môi trường Sạch (`M4`)

- **Python:** `3.12`
- **Quản lý gói:** `uv` (hoặc `pip` với `requirements-ml.txt`)

```bash
# Cài đặt môi trường khóa phiên bản 100% từ uv.lock
uv sync --python 3.12 --frozen

# Chạy toàn bộ kiểm thử tự động (schema, chống rò rỉ dữ liệu, đặc trưng nhân quả, mô hình, contract)
uv run pytest -v
```

---

## 2. Quy trình Tái lập Toàn bộ Kết quả (Validation Ready — Giữ khóa Test theo `2A`)

```bash
# Bước 1: Sinh dữ liệu mô phỏng đa người dùng VND (seed=42) + CSV demo cho Khoa & Duy
uv run python scripts/generate_data.py

# Bước 2 (Tùy chọn): Chuẩn hóa dataset Kaggle nếu đã tải data/raw/daily_household_transactions.csv
uv run python scripts/prepare_public_data.py

# Bước 3: Xuất báo cáo EDA & biểu đồ vào docs/eda_report.md và artifacts/synthetic/figures/
uv run python scripts/run_eda.py --dataset synthetic

# Bước 4: Huấn luyện F3 (Baseline, LinearRegression, RandomForestRegressor) & F4 (IsolationForest)
uv run python scripts/train.py --dataset synthetic --version v1.0.0

# Bước 5: Đánh giá Validation, Rolling CV, Benchmark bất thường mô phỏng, Độ trễ <=3s & cập nhật Model Card
uv run python scripts/evaluate.py --dataset synthetic

# Bước 6: Đóng gói Notebook mỏng & gói mã nguồn cho Google Colab
uv run python scripts/build_colab_notebook.py
```

---

## 3. Mở khóa Tập Test Đúng 1 Lần Duy nhất (Sau khi chốt cấu hình với Khoa)

Tập `test` mặc định bị khóa bởi `TestLockGuard` để ngăn tối ưu tham số dựa trên tập kiểm tra cuối. Chỉ chạy lệnh dưới đây **1 lần duy nhất** khi cấu hình đã khóa:

```bash
uv run python scripts/evaluate.py \
  --dataset synthetic \
  --unlock-test \
  --reason "Khóa cấu hình cuối kỳ cùng Khoa và mở tập test lần đầu"
```

Lệnh này ghi dấu vết kiểm toán vào `artifacts/synthetic/metrics/test_evaluation_lock.json`, xuất `test_metrics.json`, `anomaly_manual_review_test.csv` và tự động cập nhật `docs/model_card.md`.

---

## 4. Tài liệu & Hồ sơ Bàn giao chính

- `docs/data_dictionary.md` — Từ điển dữ liệu và đặc trưng.
- `docs/eda_report.md` — Báo cáo EDA tách riêng 2 luồng `synthetic` và `real_public`.
- `docs/model_card.md` — Model Card cập nhật trực tiếp từ kết quả thực đo.
- `contracts/ML_INTEGRATION_CONTRACT.md` & `contracts/samples/` — Hợp đồng tích hợp FastAPI/Streamlit & JSON mẫu.
- `notebooks/finance_ml_colab.ipynb` — Notebook Google Colab mỏng dùng chung mã nguồn `src/finance_ml`.
