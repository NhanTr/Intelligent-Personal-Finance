# Từ điển Dữ liệu (Data Dictionary)

Tài liệu đặc tả schema dữ liệu chuẩn dùng thống nhất cho toàn bộ pipeline làm sạch, tổng hợp ngày, huấn luyện mô hình (`F3`, `F4`), CSV import (`F1`) và API tích hợp (`K2–K3`).

---

## 1. Bảng Giao dịch Chuẩn (`transactions`)

| Trường | Kiểu dữ liệu | Bắt buộc | Miền giá trị / Quy tắc | Giải thích nghiệp vụ |
| :--- | :--- | :---: | :--- | :--- |
| `transaction_id` | `string` | Có | Chuỗi không rỗng, duy nhất | Khóa định danh giao dịch; khử trùng theo `keep="first"` khi nhập lại CSV. |
| `user_id` | `string` | Có | Chuỗi ẩn danh (`user_001`, `public_hh_001`...) | Định danh người dùng đã ẩn danh; tuyệt đối không chứa email/SĐT/tên thật. |
| `timestamp` | `datetime` | Có | ISO-8601 theo múi giờ Việt Nam (`UTC+07:00`) | Thời điểm phát sinh giao dịch; dùng để chia tập thời gian và tính đặc trưng nhân quả. |
| `type` | `string` | Có | `"income"` \| `"expense"` | Phân loại dòng tiền thu hoặc chi. |
| `amount_vnd` | `float` | Có | `> 0.0` (đơn vị duy nhất: **VND**) | Số tiền giao dịch dương bằng đồng Việt Nam. Mọi dòng `<= 0` hoặc `NaN` bị loại khi làm sạch. |
| `category` | `string` | Có | `food`, `transport`, `housing`, `utilities`, `shopping`, `entertainment`, `health`, `education`, `salary`, `bonus`, `transfer`, `other` | Danh mục chuẩn hóa; nhãn lạ ở lúc suy luận tự động ánh xạ về `"other"`. |
| `is_internal_transfer` | `bool` | Có | `true` \| `false` (tự động `true` nếu `category == "transfer"`) | Đánh dấu chuyển khoản nội bộ (ví dụ nạp ví, chuyển tiết kiệm, `Transfer-Out`) để **không cộng trùng** vào tổng chi tiêu và không báo bất thường chi tiêu. |
| `note` | `string \| null` | Không | Văn bản tự do hoặc `null` | Ghi chú bổ sung của giao dịch. |

---

## 2. Metadata Khoảng Theo dõi Hồ sơ (`profile_windows`)

| Trường | Kiểu dữ liệu | Quy tắc | Giải thích |
| :--- | :--- | :--- | :--- |
| `user_id` | `string` | Khớp `transactions.user_id` | Mã người dùng ẩn danh. |
| `tracking_start_date` | `date` (`YYYY-MM-DD`) | `<= tracking_end_date` | Ngày bắt đầu theo dõi đầy đủ của hồ sơ. |
| `tracking_end_date` | `date` (`YYYY-MM-DD`) | `>= tracking_start_date` | Ngày kết thúc theo dõi đầy đủ của hồ sơ. |

> **Quy tắc điền `0` nghiêm ngặt:** Chỉ điền `total_expense_vnd = 0.0` cho những ngày không phát sinh chi tiêu nằm **bên trong** đoạn `[tracking_start_date, tracking_end_date]`. Các ngày ngoài khoảng này không bao giờ được tự ý điền `0`.

---

## 3. Bảng Tổng hợp Chi tiêu Ngày (`daily_spending`)

| Trường | Kiểu dữ liệu | Công thức / Quy tắc |
| :--- | :--- | :--- |
| `user_id` | `string` | Mã người dùng ẩn danh. |
| `date` | `date` | Ngày lịch Việt Nam trong `[tracking_start_date, tracking_end_date]`. |
| `total_expense_vnd` | `float` | Tổng `amount_vnd` của các giao dịch thỏa `type == "expense"` và `is_internal_transfer == false` trong ngày. |
| `tx_count` | `int` | Số lượng giao dịch chi tiêu hợp lệ (không tính thu nhập và chuyển khoản nội bộ) trong ngày. |
| `essential_expense_vnd` | `float` | Tổng chi thuộc nhóm thiết yếu (`food`, `transport`, `housing`, `utilities`, `health`, `education`). |
| `cat_share_<category>` | `float` (`[0, 1]`) | Tỷ trọng chi tiêu của từng danh mục trong ngày (`0.0` nếu `total_expense_vnd == 0`). |

---

## 4. Đặc trưng Đầu vào Mô hình

### 4.1. F3 — Dự báo tổng chi 7 ngày tới (`FORECAST_FEATURE_COLUMNS`)
Tính hoàn toàn nhân quả từ dữ liệu `date <= origin_date` (yêu cầu tối thiểu **28 ngày** lịch sử):
- `spend_last_7d`, `spend_last_14d`, `spend_last_28d`: Tổng chi 7, 14, 28 ngày gần nhất (VND).
- `daily_mean_7d`, `daily_std_7d`, `daily_mean_28d`, `daily_std_28d`: Trung bình và độ lệch chuẩn chi tiêu ngày.
- `tx_count_7d`, `tx_count_28d`: Tổng số giao dịch chi tiêu 7 và 28 ngày qua.
- `zero_spend_days_28d`: Số ngày không phát sinh chi tiêu trong 28 ngày qua.
- `essential_share_28d`: Tỷ trọng chi thiết yếu trong 28 ngày qua.
- `origin_day_of_week`, `origin_day_of_month`, `days_to_month_end`: Đặc trưng lịch tại ngày gốc dự báo.
- `spans_month_start`, `spans_month_end`: Cờ báo cửa sổ 7 ngày dự báo `[t+1, t+7]` có giao với kỳ đầu tháng (`1..5`) hoặc cuối tháng (`25..31`) hay không.
- **Nhãn mục tiêu (`target_next_7d_vnd`):** Tổng `total_expense_vnd` trong 7 ngày kế tiếp `[t+1, t+7]`.

### 4.2. F4 — Phát hiện giao dịch bất thường (`IsolationForest`)
Tính hoàn toàn nhân quả từ các giao dịch chi tiêu **trước thời điểm hiện tại (`timestamp < current_tx.timestamp`)** của chính người dùng đó (fallback về thống kê `train` nếu `< 5` giao dịch lịch sử):
- `log_amount`: `ln(1 + amount_vnd)`.
- `user_amount_ratio`: Tỷ lệ số tiền so với trung vị chi tiêu lịch sử của chính người dùng.
- `user_amount_zscore`: Điểm chuẩn hóa log số tiền theo trung bình & độ lệch chuẩn lịch sử của người dùng.
- `user_cat_amount_ratio`: Tỷ lệ số tiền so với trung vị lịch sử của người dùng ở cùng danh mục.
- `tx_freq_24h`, `tx_freq_7d`: Số giao dịch chi tiêu của người dùng trong 24 giờ và 7 ngày liền trước.
- `hour_of_day`, `is_weekend` và vector One-Hot danh mục (`OneHotEncoder(handle_unknown="ignore")`).
