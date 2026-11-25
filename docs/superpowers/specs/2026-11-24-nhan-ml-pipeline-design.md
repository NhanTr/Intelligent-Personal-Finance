# Design Document: Hệ thống Dữ liệu & Học máy cho Quản lý Tài chính Cá nhân (Phần của Nhân — N1–N4)

- **Ngày lập:** 2026-11-24
- **Phụ trách:** Nhân (Chủ trì Dữ liệu & Độ đo, F3 Dự báo chi tiêu 7 ngày, F4 Phát hiện bất thường, đồng phối hợp triển khai & theo dõi mô hình với Khoa)
- **Căn cứ:** `Ke_hoach_Phan_cong_PTHTTM_Khoa_Nhan_Duy_25_ngay.docx` và các file kế hoạch trong `plans/`

---

## 1. Mục đích và Lý do (Intent & Why)

Xây dựng trọn gói nền tảng dữ liệu, pipeline đặc trưng, mô hình học máy, hệ thống đánh giá không rò rỉ dữ liệu, giao diện suy luận tích hợp và bộ tài liệu minh chứng cho toàn bộ phần việc của **Nhân (`N1–N4`)** trong dự án môn *Phát triển hệ thống thông minh*.

Vì hiện tại nhóm đã dời ngày bắt đầu, chưa khởi tạo repo chung hay hợp đồng API từ Khoa, và giảng viên không yêu cầu bắt buộc 100% dữ liệu thật, thiết kế này nhằm giải quyết 3 bài toán cùng lúc:
1. **Chủ động chạy độc lập ngay từ đầu** mà không bị tắc vì chờ backend hay dữ liệu.
2. **Đảm bảo chuẩn mực khoa học dữ liệu theo yêu cầu môn học:** chống rò rỉ dữ liệu tuyệt đối, tách bạch dữ liệu mô phỏng và dữ liệu thật, tái lập được 100% trên môi trường sạch.
3. **Sẵn sàng tích hợp ngay với Khoa (`FastAPI`) và Duy (`Streamlit`)** nhờ dùng chung mã nguồn đặc trưng giữa huấn luyện và suy luận, khóa phiên bản thư viện, kèm đặc tả contract + JSON mẫu và một notebook Colab trên Google Drive để trực quan hóa/huấn luyện thuận tiện.

---

## 2. Mục tiêu, Phi mục tiêu và Phản mục tiêu

### Mục tiêu (Goals)
- **G1 — Dữ liệu minh bạch & 2 luồng tách biệt:** Có bộ sinh dữ liệu mô phỏng đa người dùng bằng VND với `seed` cố định chạy được ngay lập tức, đồng thời có sẵn adapter chuẩn hóa cho bộ dữ liệu giao dịch hộ gia đình công khai trên Kaggle (`Daily Household Transactions`) khi người dùng đặt file CSV vào `data/raw/`. Hai luồng dữ liệu được đánh giá và báo cáo **tách biệt hoàn toàn**.
- **G2 — F3 (Dự báo tổng chi 7 ngày tiếp theo):** Xây dựng và so sánh **Baseline** (tổng chi 7 ngày gần nhất), **Linear Regression** và **RandomForestRegressor** bằng **MAE** và **RMSE** (đơn vị VND); báo cáo trung thực mức cải thiện so với mục tiêu nội bộ ≥ 10% MAE trên validation; tự động fallback về Baseline nếu mô hình không vượt Baseline; trả trạng thái `insufficient_data` cho người dùng có `< 28 ngày` lịch sử.
- **G3 — F4 (Phát hiện bất thường):** Huấn luyện **Isolation Forest** với đặc trưng nhân quả theo từng người dùng; chọn ngưỡng trên validation; xuất ngữ cảnh giải thích dễ hiểu cho UI; không tự xóa/chặn giao dịch; hỗ trợ xuất mẫu kiểm định thủ công (top 30 cảnh báo + 30 ngẫu nhiên) cho Khoa & Duy và đánh giá Precision/Recall/F1 trên tập kiểm thử chèn bất thường mô phỏng riêng.
- **G4 — Sẵn sàng tích hợp & Vòng phản hồi:** Cung cấp module suy luận Python sạch (`predict_next_7d`, `detect_anomalies`), `ModelBundleLoader` xử lý lỗi thiếu/hỏng file model, script huấn luyện lại (`retrain.py`) nhận dữ liệu cập nhật + phản hồi người dùng và chỉ thay model khi đánh giá lại đạt yêu cầu, đáp ứng độ trễ suy luận `≤ 3 giây` (đo trên ≥ 20 lần chạy).
- **G5 — Notebook Google Colab & Trực quan hóa:** Cung cấp 1 notebook `.ipynb` mỏng (gọi lại chính package `finance_ml`, không nhân bản logic) được đẩy lên Google Drive dưới dạng Google Colab để Nhân xem biểu đồ EDA/thực nghiệm và chạy huấn luyện thuận tiện trên Colab, đồng thời vẫn đảm bảo khóa đúng phiên bản thư viện tương thích với backend local.
- **G6 — Đủ hồ sơ nghiệm thu `N1–N4`:** Tự động tạo/cập nhật Từ điển dữ liệu, Báo cáo EDA + biểu đồ, Manifest nguồn dữ liệu & mốc chia tập, Bảng metrics, Model Card, Hợp đồng tích hợp ML (`ML_INTEGRATION_CONTRACT.md` + JSON mẫu) và kịch bản kiểm chứng tái lập trên môi trường sạch.

### Phi mục tiêu (Non-Goals)
- Không xây dựng giao diện Streamlit (`F2`, `F5`, UI của `F3/F4` — phần của Duy).
- Không xây dựng FastAPI server, SQLite database, xác thực đăng nhập, CRUD hay API nhập CSV (`F1`, `K2–K3` — phần của Khoa).
- Không làm microservice ML chạy server riêng.
- Không mở rộng thêm bài toán phân loại cho Random Forest, không tính lãi suất, không OCR/chatbot/liên kết ngân hàng thật.

### Phản mục tiêu (Anti-Goals — Làm hỏng dự án dù code chạy)
- **Rò rỉ dữ liệu (Data Leakage):** Tuyệt đối không fit scaler/encoder/thống kê người dùng trên `validation`/`test`; không để nhãn 7 ngày của `train` chạm kỳ `validation`; không để gốc dự báo cách nhau `< 7 ngày`; không tối ưu tham số dựa trên kết quả `test`.
- **Trộn lẫn dữ liệu mô phỏng và dữ liệu thật:** Không gộp bảng metrics của synthetic vào dữ liệu thật, không tuyên bố kết quả mô phỏng chứng minh hiệu quả thực tế, không gọi kết quả rà soát thủ công F4 là "độ chính xác phát hiện gian lận".
- **Lệch đặc trưng & lệch phiên bản (Train-Serving Skew):** Không để notebook Colab tự viết lại logic feature khác với `src/finance_ml`, và không xuất file `.joblib` từ phiên bản `scikit-learn` khác với file khóa phiên bản của Khoa.
- **Lộ dữ liệu cá nhân:** Không commit bất kỳ dữ liệu cá nhân chưa ẩn danh nào vào repo.

---

## 3. Ràng buộc Dự án (Constraints)

Sao chép chính xác từ bản kế hoạch 25 ngày:
- **Ngôn ngữ & Stack cốt lõi:** Python, `pandas`, `scikit-learn`, `joblib` (tương thích để Khoa nạp trực tiếp vào `FastAPI` + `SQLite` và Duy gọi từ `Streamlit`).
- **Phiên bản Python & quản lý gói:** Khóa ở **Python 3.12** qua `uv` (`pyproject.toml` + `uv.lock`) kèm file `requirements-ml.txt` xuất ra có pin version chính xác (`==`) để Khoa, Duy và Google Colab dùng chung một phiên bản thư viện.
- **Đơn vị tiền tệ:** **VND** là đơn vị duy nhất; `amount_vnd > 0`; phân biệt chuyển khoản nội bộ (`is_internal_transfer`) để không cộng hai lần vào tổng chi.
- **Ngưỡng lịch sử tối thiểu:**
  - Hồ sơ đưa vào đánh giá dự báo: tối thiểu **180 ngày liên tục** (có ngày không phát sinh chi); tổng giao dịch mục tiêu bổ trợ **≥ 1.000 giao dịch**.
  - Người dùng khi suy luận F3: dưới **28 ngày** lịch sử phải trả trạng thái **chưa đủ dữ liệu**.
- **Quy tắc điền `0` tổng hợp ngày:** Chỉ điền `0` cho những ngày được xác nhận nằm trong khoảng theo dõi đầy đủ của hồ sơ đó (`[tracking_start_date, tracking_end_date]`).
- **Chia tập thời gian:** Dự kiến **60% train / 20% validation / 20% test** theo mốc lịch chung khi huấn luyện gộp nhiều hồ sơ; `test` giữ nguyên và chỉ mở **1 lần** sau khi khóa cấu hình.
- **Độ đo F3:** **MAE** và **RMSE** (VND), báo thêm số mẫu và kết quả theo hồ sơ; **không dùng MAPE làm độ đo chính**. Mục tiêu nội bộ: MAE validation thấp hơn baseline **≥ 10%**.
- **Đánh giá F4:** Chọn ngưỡng trên validation, ghi tỷ lệ cảnh báo; nếu không có nhãn độc lập, xuất **top 30 giao dịch cảnh báo cao nhất** (hoặc toàn bộ nếu `< 30`) + **30 giao dịch chọn ngẫu nhiên** để Khoa và Duy rà độc lập; ca bất thường chèn có chủ đích chỉ đánh giá trong nhóm kiểm thử mô phỏng.
- **Hiệu năng suy luận:** Mục tiêu phản hồi suy luận **≤ 3 giây** ở 1 người dùng sau khi nạp mô hình; ghi cấu hình máy và kết quả **≥ 20 lần thử**.

---

## 4. Các Phương án Đã Cân nhắc (Approaches)

| Phương án | Mô tả ngắn | Đánh đổi | Quyết định |
| :--- | :--- | :--- | :--- |
| **1. Package Python độc lập + CLI Scripts + Inference Contract + Thin Colab Notebook** | Toàn bộ logic dữ liệu, đặc trưng, train, đánh giá, suy luận nằm trong `src/finance_ml/`. Các lệnh CLI chạy qua `uv`. Kèm 1 notebook `.ipynb` mỏng gọi lại chính `finance_ml` để đẩy lên Google Drive/Colab. | Tốn công thiết kế cấu trúc sạch ban đầu; đổi lại chống train-serving skew tuyệt đối, dễ test tự động chống leakage, Khoa import trực tiếp vào FastAPI, tái lập 100% trên máy sạch, vẫn có Colab tiện xem & chạy. | **Đã chọn** (theo đề xuất và xác nhận của Nhân về việc kèm Colab notebook). |
| **2. Notebook-first (Jupyter/Colab làm trung tâm)** | Code EDA, feature, train nằm hết trong `.ipynb`, export `.joblib` và 1 script `predict.py` rời. | Trực quan nhanh lúc đầu, nhưng rất dễ lệch đặc trưng giữa notebook và backend, khó test chống leakage, khó đáp ứng `retrain` và tái lập môi trường sạch (`M4`). | Loại. |
| **3. Package ML + FastAPI Micro-service riêng** | Ngoài package ML, dựng thêm một server HTTP FastAPI riêng cho ML. | Tiện đo độ trễ HTTP sớm, nhưng vi phạm phạm vi ngoài 25 ngày (không làm microservice) và chồng chéo nhiệm vụ `K2–K3` của Khoa. | Loại. |

---

## 5. Kiến trúc & Thiết kế Chi tiết (The How)

### 5.1. Cấu trúc Thư mục Dự án

```text
.
├── pyproject.toml                   # Python 3.12, dependencies & pytest config (uv)
├── uv.lock                          # File khóa môi trường tái lập 100%
├── requirements-ml.txt              # Danh sách gói pin cứng (==) dùng cho Khoa & Colab
├── configs/
│   └── default.yaml                 # Toàn bộ tham số: seed, split ratios, grid RF, IF thresholds
├── src/finance_ml/
│   ├── __init__.py
│   ├── config.py                    # Load & validate cấu hình (Pydantic)
│   ├── schema.py                    # Canonical Transaction, ProfileMeta, ForecastResult, AnomalyResult
│   ├── data/
│   │   ├── synthetic.py             # Bộ sinh mô phỏng đa user VND (6-8 user >=240d + 1 user <28d + tập chèn bất thường)
│   │   ├── public_adapter.py        # Adapter chuẩn hóa Kaggle Daily Household Transactions -> schema chuẩn VND
│   │   ├── cleaning.py              # Làm sạch, kiểm tra schema, khử trùng theo transaction_id, tách chuyển khoản nội bộ
│   │   └── daily.py                 # Tổng hợp theo ngày, điền 0 nghiêm ngặt trong khoảng theo dõi đầy đủ
│   ├── features/
│   │   ├── forecast_features.py     # Đặc trưng nhân quả F3 (lag 7/14/28, rolling mean/std, tx_count, lịch)
│   │   └── anomaly_features.py      # Đặc trưng nhân quả F4 (log_amount, user z-score/ratio, category ratio, freq 24h/7d)
│   ├── evaluation/
│   │   ├── split.py                 # Chia tập 60/20/20 theo lịch, purge overlap 7 ngày, origin spacing >= 7 ngày
│   │   ├── metrics.py               # MAE, RMSE tổng & theo hồ sơ, % cải thiện vs Baseline, P/R/F1 cho synthetic anomaly
│   │   ├── rolling_cv.py            # Đánh giá cuốn chiếu (expanding-window CV) chỉ trong train+validation
│   │   └── test_guard.py            # Cơ chế khóa tập test (1-shot lock file + audit log)
│   ├── models/
│   │   ├── forecast.py              # Last7DaysBaseline, LinearRegression, RandomForestRegressor + chọn model/fallback
│   │   ├── anomaly.py               # IsolationForest + chọn ngưỡng trên validation + tạo lý do giải thích tiếng Việt
│   │   └── registry.py              # Lưu/nạp bundle (.joblib + metadata.json), quản lý phiên bản model & promotion gate
│   ├── inference/
│   │   ├── loader.py                # ModelBundleLoader (xử lý thiếu/hỏng file model, fallback baseline an toàn)
│   │   ├── predictor.py             # predict_next_7d(...) và detect_anomalies(...) — API Python cho Khoa import
│   │   └── benchmark.py             # Đo độ trễ suy luận >= 20 lần chạy sau khi nạp model + thông tin cấu hình máy
│   └── reporting/
│       ├── eda.py                   # Sinh báo cáo EDA markdown + biểu đồ PNG (tách synthetic & real_public)
│       ├── model_card.py            # Sinh docs/model_card.md từ metadata & metrics thực đo
│       └── review_export.py         # Xuất CSV top 30 cảnh báo + 30 ngẫu nhiên cho Khoa & Duy rà độc lập
├── scripts/
│   ├── generate_data.py             # Sinh dữ liệu mô phỏng + CSV mẫu cho Khoa/Duy + manifest
│   ├── prepare_public_data.py       # Chạy adapter nếu có data/raw/daily_household_transactions.csv
│   ├── run_eda.py                   # Chạy EDA & xuất biểu đồ
│   ├── train.py                     # Train F3 + F4 trên train, tune & chọn trên validation, lưu bundle
│   ├── evaluate.py                  # Đánh giá validation; cờ --unlock-test để mở test đúng 1 lần
│   ├── retrain.py                   # Vòng phản hồi: huấn luyện lại với dữ liệu + feedback mới, chỉ promote nếu đạt
│   └── build_colab_notebook.py      # Tạo notebooks/finance_ml_colab.ipynb sạch bằng nbformat (kèm hướng dẫn/đẩy Drive)
├── contracts/
│   ├── ML_INTEGRATION_CONTRACT.md   # Đặc tả schema, input/output, mã lỗi, phiên bản thư viện gửi Khoa & Duy
│   └── samples/                     # JSON mẫu cho request/response F3 (đủ & thiếu lịch sử) và F4
├── notebooks/
│   └── finance_ml_colab.ipynb       # Notebook Colab mỏng gọi thẳng src/finance_ml
├── data/
│   ├── raw/                         # .gitkeep (+ file Kaggle nếu tải về; bỏ qua file cá nhân qua .gitignore)
│   ├── processed/                   # Dữ liệu sạch tách thư mục synthetic/ và real_public/
│   ├── demo/                        # CSV hợp lệ/demo sạch gửi Khoa & Duy
│   └── manifest.json                # Nguồn, điều kiện dùng, ngày tạo, phạm vi, số lượng, lỗi đã xử lý
├── artifacts/
│   ├── models/
│   │   └── active.json              # Con trỏ tới bundle triển khai mặc định cho FastAPI (mặc định trỏ tới synthetic)
│   ├── synthetic/                   # Tách biệt hoàn toàn mọi artifact theo từng luồng dữ liệu
│   │   ├── models/<version>/        # Bundle mô hình (.joblib + metadata.json) + active.json riêng của luồng
│   │   ├── metrics/                 # validation_metrics.json, test_metrics.json, test_evaluation_lock.json, synthetic_anomaly_eval.json, latency.json
│   │   ├── figures/                 # Biểu đồ EDA, so sánh MAE/RMSE, phân phối điểm bất thường
│   │   └── anomaly_manual_review_<split>.csv
│   └── real_public/                 # Cấu trúc tương tự artifacts/synthetic/, hoàn toàn không ghi đè lẫn nhau
│       ├── models/<version>/
│       ├── metrics/
│       ├── figures/
│       └── anomaly_manual_review_<split>.csv
├── docs/
│   ├── data_dictionary.md           # Từ điển dữ liệu đầy đủ
│   ├── eda_report.md                # Báo cáo EDA (tách rõ 2 mục: synthetic & real_public)
│   └── model_card.md                # Model Card (tách rõ kết quả & giới hạn của từng luồng)
└── tests/                           # Bộ unit test + anti-leakage test + contract test + reproducibility test
```

### 5.2. Schema Dữ liệu Chuẩn (Canonical Schema)

Tất cả nguồn dữ liệu (mô phỏng, công khai Kaggle, dữ liệu từ DB/CSV của Khoa) đều chuẩn hóa về đúng 1 schema bảng giao dịch:

| Trường | Kiểu | Quy tắc bắt buộc |
| :--- | :--- | :--- |
| `transaction_id` | `str` | Khóa định danh duy nhất; dùng để khử trùng khi nhập lại CSV. |
| `user_id` | `str` | Mã người dùng đã ẩn danh (vd: `user_001`, `public_hh_001`), không chứa PII. |
| `timestamp` | `datetime` | Thời điểm giao dịch theo giờ Việt Nam (`Asia/Ho_Chi_Minh`, chuẩn hóa về ISO-8601 `YYYY-MM-DDTHH:MM:SS+07:00` khi trao đổi JSON). |
| `type` | `str` | Chỉ nhận `"income"` hoặc `"expense"`. |
| `amount_vnd` | `float` | Số thực **dương (`> 0`)**, đơn vị duy nhất là **VND**. |
| `category` | `str` | Danh mục chuẩn hóa về bộ từ điển cố định (`food`, `transport`, `housing`, `utilities`, `shopping`, `entertainment`, `health`, `education`, `salary`, `bonus`, `transfer`, `other`). Giá trị lạ map về `"other"` ở inference để không sập pipeline. |
| `is_internal_transfer` | `bool` | `True` nếu là chuyển khoản nội bộ (nạp ví, chuyển sang tiết kiệm, `Transfer-Out`); mặc định `False`. Giao dịch có `is_internal_transfer == True` **không** tính vào tổng chi tiêu và không chạy phát hiện bất thường chi tiêu. |
| `note` | `str \| None` | Ghi chú tùy chọn. |

**Metadata khoảng theo dõi hồ sơ (`profile_windows`):**
- Mỗi `user_id` có `(tracking_start_date, tracking_end_date)` rõ ràng.
- Khi tổng hợp theo ngày (`daily.py`), hệ thống sinh chuỗi ngày liên tục từ `tracking_start_date` đến `tracking_end_date` và chỉ điền `total_expense_vnd = 0.0`, `tx_count = 0` trong đúng khoảng này.

### 5.3. Hai Luồng Dữ liệu Tách biệt

1. **Luồng A — Bộ sinh Mô phỏng VND (`data/synthetic.py`, `source_type = "synthetic"`):**
   - `seed = 42` (cấu hình được trong `configs/default.yaml`).
   - **8 hồ sơ chính (`user_001`..`user_008`):** 300 ngày liên tục (từ `2026-01-01` đến `2026-10-27`), tổng ~3.000–4.500 giao dịch, đa dạng hành vi (sinh viên, nhân viên văn phòng, freelancer, hộ gia đình trẻ): có chu kỳ lương, tiền nhà đầu tháng, chi cuối tuần cao hơn, có **15%–30% ngày không phát sinh chi**, và có **~5% chuyển khoản nội bộ**.
   - **1 hồ sơ lịch sử ngắn (`user_short_001`):** chỉ có **14 ngày** lịch sử để kiểm thử trạng thái `< 28 ngày` (`insufficient_data`).
   - **Tập kiểm thử chèn bất thường tách riêng (`synthetic_anomaly_eval`):** sinh dựa trên phân phối nền của 4 hồ sơ trong kỳ đánh giá, sau đó chèn có kiểm soát ~3% ca bất thường có nhãn (`is_injected_anomaly = True`) gồm 3 dạng: (i) số tiền vọt gấp 5–12 lần mức bình thường của user, (ii) số tiền vọt bất thường trong danh mục thường chi nhỏ, (iii) chuỗi giao dịch dồn dập bất thường trong 24 giờ. Tập này **không bao giờ** dùng để train và chỉ báo cáo trong mục *Kiểm thử mô phỏng*.
   - **Ghi chú quy ước:** Toàn bộ kết quả từ Luồng A luôn gắn nhãn rõ là *Dữ liệu mô phỏng (minh họa kỹ thuật, không chứng minh hiệu quả ngoài thực tế)*.

2. **Luồng B — Adapter Dữ liệu Công khai Kaggle (`data/public_adapter.py`, `source_type = "real_public"`):**
   - Hỗ trợ đọc bộ **Daily Household Transactions** (`prasad22/daily-transactions-dataset`) nếu file CSV được đặt tại `data/raw/daily_household_transactions.csv`.
   - Ánh xạ: `Date` → `timestamp`, `Income/Expense == "Transfer-Out"` → `is_internal_transfer = True`, `Amount` (INR) × tỷ giá cố định có ghi nhận trong `manifest.json` (mặc định `300 VND/INR`, lưu trong config) → `amount_vnd`, `Category` → bộ danh mục chuẩn, `user_id = "public_hh_001"`.
   - Nếu file chưa có trên máy, pipeline báo thông tin rõ ràng và vẫn chạy hoàn chỉnh Luồng A mà không lỗi; khi Nhân tải file về bỏ vào `data/raw/`, chạy `scripts/prepare_public_data.py` và `scripts/train.py --dataset real_public` sẽ tự động tạo bộ kết quả thực nghiệm dữ liệu thật tách biệt hoàn toàn.

### 5.4. Chia tập theo Thời gian & Phòng ngừa Rò rỉ (Anti-Leakage Design)

- **Mốc chia lịch chung (`split.py`):**
  - Với tập 300 ngày (`2026-01-01` → `2026-10-27`), chia đúng tỷ lệ **60% / 20% / 20%**:
    - `train`: 180 ngày đầu (`Day 1..180`)
    - `validation`: 60 ngày tiếp theo (`Day 181..240`)
    - `test`: 60 ngày cuối (`Day 241..300`)
  - Áp dụng chung mốc lịch cho mọi hồ sơ khi huấn luyện gộp (tự động tính theo tỷ lệ 60/20/20 cho mọi dataset có độ dài khác).
- **Quy tắc sinh mẫu cho F3 (Dự báo tổng chi 7 ngày `[t+1, t+7]`):**
  - Gốc dự báo $t$ phải có đủ **≥ 28 ngày lịch sử** trước và gồm ngày $t$ (`t >= tracking_start_date + 27 days`).
  - Gốc dự báo $t$ phải có đủ **7 ngày thực tế** sau $t$ (`t + 7 <= tracking_end_date`).
  - **Loại mẫu chạm ranh giới (Boundary Purge):**
    - Mẫu thuộc `train` chỉ hợp lệ khi `t + 7 <= train_end_date`.
    - Mẫu thuộc `validation` chỉ hợp lệ khi `t >= val_start_date` và `t + 7 <= val_end_date`.
    - Mẫu thuộc `test` chỉ hợp lệ khi `t >= test_start_date` và `t + 7 <= test_end_date`.
  - **Giãn cách gốc dự báo ≥ 7 ngày:** Bước nhảy giữa các gốc dự báo liên tiếp của cùng một user là **7 ngày** (`origin_step_days = 7`), đảm bảo các cửa sổ nhãn `[t+1, t+7]` không chồng lấn nhau.
- **Đánh giá cuốn chiếu (Rolling/Expanding CV — Ngày 11):**
  - Thực hiện expanding-window time-series splits **chỉ nằm gọn trong `train + validation`** (tuyệt đối không đụng `test`) để kiểm tra độ ổn định của Linear Regression và RandomForestRegressor theo thời gian.
- **Khóa tập Test (1-shot Test Lock — `test_guard.py`) *(Chốt theo quyết định 2A của Nhân)*:**
  - `scripts/evaluate.py` mặc định chỉ chạy trên `validation`.
  - **Mốc dừng đợt triển khai đầu tiên:** Chạy đầy đủ pipeline đến hết bước `validation` + đánh giá cuốn chiếu (rolling CV), **giữ khóa tập `test`** (`test_evaluation_lock.json` chưa mở), xuất `anomaly_manual_review_validation.csv` và sinh `docs/model_card.md` ở trạng thái *Pre-Test / Validation Ready* (đánh dấu rõ phần Test chưa mở).
  - Chuẩn bị sẵn đúng 1 lệnh CLI để Nhân tự mở test 1 lần duy nhất sau khi chốt cấu hình với Khoa: `uv run python scripts/evaluate.py --dataset synthetic --unlock-test --reason "<lý do>"`. Khi chạy lệnh này, hệ thống đánh giá tập `test`, ghi `artifacts/<dataset>/metrics/test_evaluation_lock.json` (config hash, timestamp, số lần mở, lý do) và tự động cập nhật `docs/model_card.md` sang bản Final. Nếu chạy lại lần thứ 2 trở đi, bắt buộc ghi lý do sửa lỗi triển khai (audit trail minh bạch theo yêu cầu Ngày 14).

### 5.5. Thiết kế Mô hình F3 & F4

#### F3 — Dự báo Tổng chi 7 Ngày Tiếp theo (Hồi quy)
- **Đầu vào (Causal Features tại gốc $t$, chỉ dùng dữ liệu `<= t`):**
  - Tổng chi trễ: `spend_last_7d`, `spend_last_14d`, `spend_last_28d`
  - Trung bình & độ biến động chi tiêu ngày: `daily_mean_7d`, `daily_std_7d`, `daily_mean_28d`, `daily_std_28d`
  - Số giao dịch chi tiêu: `tx_count_7d`, `tx_count_28d`, `zero_spend_days_28d`
  - Tỷ trọng nhóm chi tiêu thiết yếu / tùy chọn trong 28 ngày gần nhất (`essential_share_28d`)
  - Đặc trưng lịch của gốc $t$ và cửa sổ dự báo `[t+1, t+7]`: `origin_day_of_week`, `origin_day_of_month`, `days_to_month_end`, `spans_month_start` (cửa sổ 7 ngày tới có giao với ngày 1–5 đầu tháng không), `spans_month_end` (có giao với ngày 25–31 không).
- **3 Mô hình so sánh trên cùng tập gốc dự báo:**
  1. `Last7DaysBaseline`: $\hat{y}(t) = \text{spend\_last\_7d}(t)$.
  2. `LinearRegression`: `Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", LinearRegression())])`, clip dự báo không âm (`max(0.0, pred)`).
  3. `RandomForestRegressor`: `Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", RandomForestRegressor(random_state=seed))])`, chọn siêu tham số gọn trên validation (lưới nhỏ kiểm soát overfitting: `n_estimators` ∈ {100, 200}, `max_depth` ∈ {4, 6, 10, None}, `min_samples_leaf` ∈ {2, 5, 10}), clip không âm.
- **Độ đo & Quyết định chọn mô hình:**
  - Tính **MAE** và **RMSE** (VND) tổng thể + theo từng `user_id` + số mẫu $N$. Không dùng MAPE làm độ đo chính.
  - Tính `% cải thiện MAE so với Baseline` trên validation; ghi rõ cờ `meets_10pct_target: bool`.
  - Chọn mô hình có **MAE validation thấp nhất**. Nếu cả Linear Regression và Random Forest đều không tốt hơn Baseline → chọn **Baseline** làm mô hình triển khai và ghi rõ lý do trong báo cáo & Model Card.

#### F4 — Phát hiện Bất thường bằng Isolation Forest
- **Đầu vào (Causal Transaction Features cho mỗi giao dịch chi tiêu không phải chuyển khoản nội bộ):**
  - `log_amount`: $\ln(1 + \text{amount\_vnd})$
  - `user_amount_ratio`: $\text{amount\_vnd} / (\text{user\_prior\_median} + 1)$ (tính từ các giao dịch chi tiêu **trước thời điểm hiện tại** của chính user đó; nếu user có `< 5` giao dịch trước đó thì fallback về median toàn bộ tập `train` đã fit!)
  - `user_amount_zscore`: $(\ln(1+\text{amount}) - \mu_{\text{user,prior}}) / \max(\sigma_{\text{user,prior}}, 0.1)$ (tương tự, chỉ dùng lịch sử trước thời điểm giao dịch)
  - `user_cat_amount_ratio`: tỷ lệ so với mức trung vị lịch sử của chính user ở cùng danh mục (fallback về mức chung của user → mức train)
  - `tx_freq_24h`, `tx_freq_7d`: số giao dịch của user trong 24 giờ và 7 ngày trước thời điểm giao dịch
  - `hour_of_day`, `is_weekend`
  - `category`: `OneHotEncoder(handle_unknown="ignore")` chỉ fit trên `train`.
- **Chấm điểm & Chọn ngưỡng trên Validation:**
  - Fit `IsolationForest(n_estimators=200, random_state=seed, contamination="auto")` **chỉ trên tập `train`**.
  - Định nghĩa `anomaly_score = -decision_function(X)` để điểm càng cao → càng bất thường.
  - **Chọn ngưỡng trên `validation`:** lấy phân vị theo mục tiêu tỷ lệ cảnh báo hợp lý (mặc định mục tiêu alert rate trên validation nằm trong khoảng `3%–5%`, tức quantile `0.95` của `anomaly_score` trên validation, cấu hình được trong `default.yaml`), ghi nhận rõ ngưỡng `threshold` và `validation_alert_rate`.
  - **Giải thích ngữ cảnh cho UI:** Với mỗi giao dịch vượt ngưỡng, tạo danh sách 1–3 lý do cụ thể từ giá trị đặc trưng (ví dụ: *"Số tiền gấp 4.5 lần mức chi trung bình của bạn"*, *"Cao hơn 3.8 lần mức chi thường lệ ở danh mục shopping"*, *"Có 5 giao dịch trong 24 giờ qua"*), kèm lời nhắc rõ *"Điểm bất thường để tham khảo, không phải xác suất gian lận"*.
- **Đánh giá F4:**
  - **Không có nhãn độc lập:** `review_export.py --dataset <stream> --split validation|test` xuất `artifacts/<dataset>/anomaly_manual_review_<split>.csv` gồm **top 30 giao dịch có `anomaly_score` cao nhất** (hoặc toàn bộ nếu `< 30`) và **30 giao dịch chọn ngẫu nhiên** (seed cố định), kèm sẵn cột `khoa_label`, `duy_label`, `reviewer_notes` để Khoa và Duy rà độc lập vào Ngày 18. *(Quyết định kỹ thuật đề xuất: mặc định xuất từ `validation` khi tập `test` đang khóa, và hỗ trợ xuất từ `test` sau khi mở khóa `test` để Khoa/Duy rà trên tập cuối mà không làm rò rỉ sớm.)*
  - **Có nhãn mô phỏng (tập `synthetic_anomaly_eval`):** Tính Precision, Recall, F1 và số lượng cảnh báo, lưu riêng tại `artifacts/synthetic/metrics/synthetic_anomaly_eval.json`.

### 5.6. Giao diện Tích hợp cho Khoa (`inference/`) & Vòng Phản hồi (`retrain.py`)

- **Cô lập Artifact & Con trỏ mặc định *(Quyết định kỹ thuật đề xuất)*:**
  - Toàn bộ model, metrics, test lock, biểu đồ và file rà soát được tách theo namespace `artifacts/<dataset>/` (`synthetic` vs `real_public`) nên hai luồng không bao giờ ghi đè lẫn nhau.
  - Con trỏ triển khai mặc định `artifacts/models/active.json` cho FastAPI trỏ tới bundle hoạt động của luồng **`synthetic` (đa người dùng VND)** để khớp với ứng dụng demo nhiều tài khoản VND; `ModelBundleLoader` nhận đường dẫn thư mục bất kỳ để có thể chuyển sang bundle khác khi nhóm có dữ liệu thật đa người dùng.
- **API Python công khai (Khoa import thẳng vào FastAPI ở `K3`):**
  - `bundle = ModelBundleLoader("artifacts/models/active.json").load()` — nạp mô hình 1 lần khi FastAPI khởi động; nếu thiếu file hoặc file hỏng, trả trạng thái rõ ràng (`MODEL_UNAVAILABLE`) và hỗ trợ cờ fallback về Baseline cho F3 mà không làm sập API.
  - `predict_next_7d(transactions_df: pd.DataFrame, user_id: str, as_of_date: date, bundle: ModelBundle, tracking_start_date: date | None = None) -> ForecastResult`
    - **Quy tắc xác định cửa sổ theo dõi & `days_available` khi suy luận *(Quyết định kỹ thuật đề xuất)*:**
      - Nếu backend truyền `tracking_start_date`: cửa sổ hợp lệ là `[tracking_start_date, as_of_date]`.
      - Nếu `tracking_start_date` là `None`: lấy `effective_start = min(tx_date <= as_of_date)` của `user_id` đó (trả `days_available = 0` nếu không có giao dịch `<= as_of_date`), và `effective_end = as_of_date`. Các ngày không có giao dịch giữa `effective_start` và `as_of_date` (kể cả các ngày im lặng sát `as_of_date`) được điền `0` qua chính hàm `daily.py` dùng chung với lúc train; các ngày **trước** `effective_start` tuyệt đối không điền `0`.
      - Tính `days_available = (as_of_date - effective_start).days + 1`. Nếu `days_available < 28`, trả ngay `status = "insufficient_data"` (không gọi mô hình hồi quy).
    - Trả về Pydantic model/dict gồm: `status` (`"ok"` | `"insufficient_data"` | `"fallback_baseline"`), `user_id`, `as_of_date`, `horizon_days` (`7`), `forecast_start_date`, `forecast_end_date`, `predicted_total_vnd` (hoặc `None`), `unit` (`"VND"`), `model_name`, `model_version`, `days_available`, `min_days_required` (`28`), `limitations_note`.
  - `detect_anomalies(transactions_df: pd.DataFrame, user_id: str, bundle: ModelBundle, target_transaction_ids: list[str] | None = None) -> AnomalyBatchResult`
    - Trả về danh sách các giao dịch kèm: `transaction_id`, `anomaly_score`, `threshold`, `is_anomaly`, `reasons: list[str]`, `model_version`, `disclaimer`.
- **Vòng phản hồi & Huấn luyện lại (`scripts/retrain.py`) *(Quyết định kỹ thuật đề xuất)*:**
  - **Đầu vào:** Tập giao dịch cập nhật + file phản hồi người dùng tùy chọn (`transaction_id`, `user_id`, `is_confirmed_anomaly: bool`, `model_version`, `created_at`).
  - **Cách tận dụng phản hồi `is_confirmed_anomaly` (không rò rỉ):** Chia phản hồi theo đúng mốc thời gian `train`/`validation` mới. Trong kỳ `train`, loại bỏ các giao dịch đã xác nhận `is_confirmed_anomaly == True` trước khi fit `IsolationForest` để mô hình học nền hành vi bình thường sạch hơn. Trong kỳ `validation`, hiệu chỉnh/kiểm tra ngưỡng sao cho tỷ lệ cảnh báo nằm trong biên hợp lý (`[1%, 10%]`) và kiểm soát tỷ lệ báo sai trên các dòng `is_confirmed_anomaly == False` (nếu kỳ validation có `< 10` dòng phản hồi thì dùng lại quy tắc phân vị mặc định).
  - **So sánh công bằng trên cùng cửa sổ mới:** Khi dữ liệu mới mở rộng làm dịch chuyển mốc 60/20/20, luôn đánh giá lại **cả mô hình đang active lẫn mô hình candidate** trên **cùng tập validation mới** (không so với số MAE validation cũ từ khoảng thời gian khác).
  - **Cổng kiểm duyệt nguyên tử (Atomic Bundle Promotion):** Vì F3 và F4 dùng chung một `model_version` trong log của Khoa, promotion cập nhật đồng bộ cả bundle chỉ khi F3 không tệ hơn active quá dung sai (`candidate_val_mae <= active_val_mae * 1.02` hoặc cải thiện) **và** F4 vượt qua biên tỷ lệ cảnh báo + smoke test (hỗ trợ cờ `--force-promote` khi có xác nhận thủ công). Luôn giữ nguyên thư mục các phiên bản cũ để rollback.

### 5.7. Notebook Google Colab & Đồng bộ Google Drive *(Chốt theo quyết định 1A của Nhân)*

- **Tệp & Gói tạo ra:**
  - `notebooks/finance_ml_colab.ipynb` (được sinh tự động và kiểm tra hợp lệ bằng `scripts/build_colab_notebook.py` dùng `nbformat`, đảm bảo không lỗi JSON).
  - `artifacts/colab/finance_ml_colab_package.zip` (gói gọn `pyproject.toml`, `requirements-ml.txt`, `configs/`, `src/finance_ml/` và `scripts/` — sinh tự động bởi `scripts/build_colab_notebook.py` để Colab cài thẳng không cần GitHub repo).
- **Thư mục đích trên Google Drive:** Tạo thư mục riêng trong **My Drive của Nhân** là `My Drive/PTHTTM_Nhan_ML_Colab/` (tách khỏi thư mục chia sẻ chung của nhóm) và tải lên 2 tệp:
  1. `finance_ml_colab.ipynb` với `--mime-type "application/vnd.google.colaboratory"` (mở trực tiếp bằng Google Colab).
  2. `finance_ml_colab_package.zip` (chứa đúng mã nguồn `src/finance_ml`, `configs/` và `requirements-ml.txt`).
- **Cấu trúc Notebook (Mỏng — Thin Wrapper):**
  1. **Cell 1 — Mount Google Drive & Giải nén/Cài đặt `finance_ml` đúng phiên bản khóa:** Mount Drive tới `/content/drive/MyDrive/PTHTTM_Nhan_ML_Colab`, giải nén `finance_ml_colab_package.zip` vào `/content/finance_ml_work`, chạy `pip install -q -r requirements-ml.txt` và `pip install -q --no-deps -e /content/finance_ml_work`, sau đó in thông tin CPU/GPU Colab cùng phiên bản `scikit-learn`/`pandas`/`numpy` (ghi chú minh bạch rằng `scikit-learn` chạy trên CPU ngay cả khi bật GPU runtime, nhưng khóa phiên bản đảm bảo `.joblib` tương thích 100% với backend local của Khoa).
  2. **Cell 2 — Sinh dữ liệu & Kiểm tra EDA trực quan:** Gọi trực tiếp `finance_ml.data.synthetic` (hoặc `public_adapter` nếu người dùng bỏ CSV Kaggle vào thư mục Drive), hiển thị bảng thống kê và biểu đồ phân bố chi tiêu, ngày chi = 0, tỷ trọng danh mục.
  3. **Cell 3 — Huấn luyện, Rolling CV & So sánh mô hình F3 (Baseline vs Linear Regression vs RandomForestRegressor):** In bảng MAE/RMSE trên validation (tổng & theo hồ sơ) + biểu đồ so sánh dự báo vs thực tế.
  4. **Cell 4 — Huấn luyện F4 (Isolation Forest) & Phân tích cảnh báo:** Biểu đồ phân phối điểm bất thường, đường ngưỡng validation, bảng top cảnh báo kèm lý do giải thích tiếng Việt và kết quả trên tập kiểm thử chèn bất thường mô phỏng.
  5. **Cell 5 — Xuất Bundle mô hình & Artifacts về Google Drive:** Lưu bundle `.joblib` + `metadata.json` + hình ảnh + `anomaly_manual_review_validation.csv` vào `/content/drive/MyDrive/PTHTTM_Nhan_ML_Colab/outputs/` (giữ nguyên tập `test` bị khóa theo quy tắc 2A; có sẵn 1 cell cuối bị comment/khóa cờ để mở `test` 1 lần khi Nhân sẵn sàng).

---

## 6. Những phần để lại cho Người lập Kế hoạch / Thực thi (Left to Builder)

Các chi tiết kỹ thuật nhỏ sau đây không làm thay đổi thiết kế tổng thể và để builder tự chọn hợp lý trong quá trình viết plan & code:
- Kiểu dáng chi tiết của biểu đồ `matplotlib` (bảng màu, kích thước hình, bố cục subplot) miễn đảm bảo rõ đơn vị VND, tiêu đề và chú thích tiếng Việt/Anh nhất quán.
- Định dạng lưu bảng dữ liệu trung gian trong `data/processed/` (Parquet hoặc CSV — ưu tiên CSV cho `data/demo/` để Duy/Khoa mở dễ dàng, còn `data/processed/` chọn CSV hoặc Parquet nhất quán).
- Cấu trúc chia nhỏ các test file cụ thể trong `tests/` miễn bao phủ đủ các kiểm thử chống leakage, schema, edge case `< 28 ngày`, chuyển khoản nội bộ, fallback khi thiếu model, hiệu năng `≤ 3 giây` (20 lần) và tái lập theo `seed`.
- Chi tiết tham số lưới tuning nhỏ cho `RandomForestRegressor` và `IsolationForest` trong `configs/default.yaml` miễn đảm bảo thời gian chạy nhanh và chỉ chọn trên `validation`.
