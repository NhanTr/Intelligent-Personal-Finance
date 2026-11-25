# Model Card — Hệ thống Dự báo Chi tiêu (F3) & Cảnh báo Bất thường (F4)

## 1. Mục tiêu và Phạm vi Sử dụng
- **F3 (Hồi quy):** Dự báo tổng chi tiêu (VND) trong **7 ngày tiếp theo** cho người dùng có tối thiểu **28 ngày lịch sử**.
- **F4 (Isolation Forest):** Chấm điểm mức độ bất thường cho từng giao dịch chi tiêu (không tính chuyển khoản nội bộ) kèm lời giải thích ngữ cảnh để người dùng tự kiểm tra.
- **Giới hạn quan trọng:**
  - Không dự đoán cho người dùng `< 28 ngày` lịch sử (`status = insufficient_data`).
  - Không tự động quy đổi dự báo 7 ngày thành dự báo tháng.
  - Điểm bất thường **không phải** xác suất gian lận; hệ thống tuyệt đối không tự xóa hay chặn giao dịch.
  - Kết quả trên dữ liệu mô phỏng (`synthetic`) chỉ mang tính minh họa kỹ thuật, không chứng minh hiệu quả thực tế bên ngoài.

## Luồng A — Mô phỏng Đa người dùng VND (`synthetic` — Minh họa kỹ thuật)

- **Phiên bản đang kích hoạt (`active`):** `v1.0.0`
- **Thời điểm huấn luyện:** `2026-11-25T11:13:55.036190+07:00` | **scikit-learn:** `1.9.1` | **Seed:** `42`
- **Mốc chia tập (60/20/20):** `{"train_start": "2026-01-01", "train_end": "2026-06-29", "val_start": "2026-06-30", "val_end": "2026-08-28", "test_start": "2026-08-29", "test_end": "2026-10-27"}`
- **Mô hình F3 được chọn trên Validation:** `random_forest` (Fallback cơ sở: `False`)

### Kết quả F3 trên Validation (Đơn vị: VND — Không dùng MAPE)

| Mô hình | MAE (VND) | RMSE (VND) | Số mẫu | Cải thiện vs Baseline (%) | Đạt mục tiêu >= 10%? |
| :--- | ---: | ---: | ---: | ---: | :---: |
| `baseline_last_7d` | 2,325,125 | 3,281,353 | 64 | — | — |
| `linear_regression` | 1,009,690 | 1,446,200 | 64 | +56.57% | Đạt |
| `random_forest` | 500,308 | 1,024,847 | 64 | +78.48% | Đạt |

### Kết quả F4 (Isolation Forest) trên Validation
- **Ngưỡng bất thường (`threshold`):** `0.079266`
- **Tỷ lệ cảnh báo trên Validation:** `5.12%` (`40/782` giao dịch)
- **Lưu ý nghiệp vụ:** Điểm bất thường không phải xác suất gian lận; chỉ cảnh báo để người dùng xem xét và xác nhận đúng/sai.

### Kết quả Nhóm Kiểm thử Chèn Bất thường Mô phỏng (Tách riêng)
- **Precision:** `0.657` | **Recall:** `0.958` | **F1:** `0.780` | **Số cảnh báo:** `70/461`

### Hiệu năng Suy luận (1 người dùng sau khi nạp mô hình)
- **Số lần đo:** `25` | **Mean:** `75.73 ms` | **P95:** `105.62 ms` | **Max:** `113.93 ms` (Mục tiêu `<= 3.0s`: `Đạt`)
- **Cấu hình máy:** `macOS-27.2.1-arm64-arm-64bit (arm64) — Python 3.12.11`

### Kết quả trên Tập Test Độc lập
- **Trạng thái:** **ĐANG KHÓA (Quy tắc 2A — Pre-Test / Validation Ready)** — Tập `test` chưa mở để bảo toàn tính độc lập tuyệt đối. Khi nhóm chốt cấu hình cuối, chạy `scripts/evaluate.py --dataset synthetic --unlock-test --reason '<lý do>'` đúng 1 lần để cập nhật mục này.

---

## Luồng B — Dữ liệu Công khai Kaggle (`real_public` — Benchmark thực tế 1 hộ gia đình)

*Chưa có mô hình huấn luyện cho luồng `real_public`.*
