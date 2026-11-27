# Hợp đồng API đề xuất — D1

**Trạng thái: bản nháp chờ Khoa/Nhân xác nhận.** MockApiClient là đối tượng Python trong phiên, không phải HTTP server; khi có API thực cần viết adapter tương ứng và không thể cam kết chỉ đổi URL.

- Phiên/token xác định chủ sở hữu ở backend; không tin user_id từ CSV hoặc query. CSV có user_id khác thì cảnh báo, bỏ qua cột và gán tài khoản phiên. Mock chỉ minh họa, không chứng minh bảo mật.
- CSV: UTF-8, dấu phẩy, `transaction_id,date,type,amount,category`, `note` và `user_id` tùy chọn; ngày YYYY-MM-DD, amount là số nguyên VND dương. Tạm đề xuất uniqueness `(user_id, transaction_id)`; không dùng tổ hợp số tiền/thời gian để tự xóa trùng vì hai giao dịch thật có thể giống nhau. Mock hiện nhập toàn bộ hoặc không nhập dòng nào; cách xử lý chính thức và khóa cần nhóm chốt.
- Chuyển nội bộ tạm biểu diễn `type=transfer` và loại khỏi thu/chi. Cần chốt mô hình cặp chuyển và ảnh hưởng số dư với Khoa/Nhân. Không suy ra kế hoạch đã quy định trường này.
- Kênh đề xuất: GET/POST `/transactions`, POST `/transactions/import`, GET `/stats`, GET `/forecast`, GET `/anomalies`, POST `/anomalies/{id}/feedback`. Các tham số, cấu trúc lỗi, phương thức xác thực, schema và các trạng thái là bản nháp cần thống nhất; mock hiện dùng interface Python trong `api_client.py`.
- `occurred_at` có múi giờ được đề xuất trong fixtures; CSV bản nháp vẫn dùng `date` để tương thích mẫu ban đầu. Chốt tên và độ chính xác thời gian giao dịch trước tích hợp. Contract ML yêu cầu `created_at` cho bản ghi **phản hồi**; thời điểm tạo dự báo và thời điểm tạo giao dịch chưa được quy định bởi contract đó.
- Danh mục cố định trong giao diện là danh sách demo, chưa là từ điển mã chính thức. Cần chuẩn hóa và định nghĩa nguồn mã trong dữ liệu/API thực.
- Số dư demo = tổng thu trừ tổng chi trong kỳ, không có số dư đầu kỳ. Khoảng mặc định demo là toàn bộ dữ liệu mẫu. Ngưỡng tăng mạnh chưa chốt.
- Dự báo hiển thị khoảng 7 ngày, thời điểm, đơn vị, phiên bản và trạng thái thiếu dữ liệu/baseline. Cảnh báo không phải xác suất gian lận. Không lưu phản hồi thật ở mock.

## Câu hỏi cho nhóm

1. Hợp đồng API và cách xác thực chính thức? 2. Khóa chống trùng và cách nhập một phần? 3. Biểu diễn chuyển nội bộ và số dư? 4. Trường thời gian và múi giờ? 5. Danh mục mã/nhãn? 6. Kỳ mặc định và ngưỡng tăng mạnh? 7. Cấu trúc lỗi và ý nghĩa phản hồi đúng/sai?

## Bổ sung mốc ngày 12

`MockApiClient.import_transactions(user_id, dataframe)` trả `accepted`, `errors` và `warnings`; dữ liệu chỉ nằm trong phiên. `forecast(user_id)` kiểm tra trạng thái, số tiền, VND, khoảng đủ 7 ngày, thời điểm có múi giờ và thông tin phiên bản/phương án dự phòng. Các quy tắc này vẫn là hợp đồng nháp; cần đối chiếu API thực trước khi tích hợp.
