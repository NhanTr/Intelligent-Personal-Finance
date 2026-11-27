# Wireframe ứng dụng tài chính cá nhân

Bản phác thảo D1 để rà bố cục và luồng thao tác. Xem [sơ đồ wireframe](../wireframe-tong-quan.svg). Khung Streamlit thể hiện cả năm luồng bằng dữ liệu giả lập. Các trường thu chi và cách gọi API cần đối chiếu với hợp đồng K1 khi Khoa chốt.

## 1. Đăng nhập và giao dịch — F1

```text
ĐĂNG NHẬP                         QUẢN LÝ THU CHI
[Tài khoản demo     ]             [Từ ngày] [Đến ngày] [Loại] [Danh mục]
[Mật khẩu           ]             Ngày | Loại | Danh mục | Số tiền | Ghi chú
[Đăng nhập]                       -----------------------------------------
Thông báo lỗi                     Dưới bảng: [Thu] [Chi] [Chênh lệch]
                                  [Thêm giao dịch hoặc nhập CSV]
                                  [Sửa hoặc xóa giao dịch]
```

Form giao dịch gồm ngày, loại, số tiền dương, danh mục và ghi chú tùy chọn. Tab CSV cho xem trước và chỉ nhập khi toàn bộ file hợp lệ theo quy tắc nháp. Nếu file sai, hiển thị số dòng và lý do. Danh sách trống có nút thêm giao dịch hoặc đổi khoảng ngày. Khoa cần xác nhận khóa chống trùng, cách xử lý file lỗi và quyền sở hữu khi tích hợp.

## 2. Dashboard — F2

```text
DASHBOARD  [Từ ngày] [Đến ngày]
[Chênh lệch thu − chi: ... VND] [Tổng thu: ... VND] [Tổng chi: ... VND]

Chi theo danh mục                     So sánh thu và chi [Tuần] [Tháng]
[Số tiền · Tỷ trọng · Thanh]          [Cột Thu và Chi cho kỳ trước và kỳ này]
[So với khoảng trước cùng độ dài]     [Chỉ số | Kỳ trước | Kỳ này | Chênh lệch]

Trống: [Thêm giao dịch] [Đổi khoảng ngày]
```

Không có dữ liệu: thông báo thay biểu đồ rỗng. Tỷ lệ khi tổng chi bằng 0 không được chia cho 0. Định nghĩa “tăng mạnh” chờ nhóm chốt.

## 3. Dự báo — F3

```text
DỰ BÁO 7 NGÀY TỚI
[Tổng chi dự báo: ... VND]    Khoảng dự báo: ... đến ...
Ngày gốc dự báo · Lịch sử · Phương pháp · Phiên bản
Thông tin và giới hạn của kết quả
```

Dưới 28 ngày lịch sử thì hiện thông báo và không hiện số tiền dự báo. Có nhãn khi dùng dự báo cơ sở và thông báo khi không tải được dữ liệu. JSON của Nhân có ngày gốc dự báo. Thời điểm tạo kết quả chờ phía API cung cấp khi cần.

## 4. Cảnh báo — F4

```text
CẢNH BÁO GIAO DỊCH
Số giao dịch chi đã chấm · Số được đánh dấu · Phiên bản
[Danh mục · Số tiền]          [Đúng] [Sai]
Thời điểm · Điểm · Ngưỡng     [Đã ghi trong phiên]
Lý do cần xem xét
```

Giải thích cảnh báo chỉ để người dùng xem xét, không khẳng định gian lận. Hiện trạng thái không có cảnh báo và lỗi lưu phản hồi. Ý nghĩa đúng/sai, ngữ cảnh và hợp đồng API chờ xác nhận.

## 5. Mô phỏng tiết kiệm — F5

```text
MÔ PHỎNG TIẾT KIỆM
[Mục tiêu]                   [Giữ nguyên] · Chi, tiết kiệm và số tháng
[Đã có]                      [Giảm 10% chi tùy chọn] · Chi, tiết kiệm và số tháng
[Thu nhập/tháng]             [Giảm 20% chi tùy chọn] · Chi, tiết kiệm và số tháng
[Chi thiết yếu/tháng]
[Chi tùy chọn/tháng]
```

Nếu đã đủ mục tiêu: 0 tháng. Nếu chưa đủ và tiết kiệm không dương: chưa thể đạt với giả định hiện tại. Không tính lãi. Đầu vào chia chi thiết yếu/tùy chọn là giả định giao diện để minh họa.
