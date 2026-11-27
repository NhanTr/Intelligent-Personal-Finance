# Danh sách ca kiểm thử D1

Đây là kế hoạch kiểm thử, **chưa phải kết quả thực hiện**. Mỗi lần chạy cần ghi phiên bản, dữ liệu đầu vào, bước thực hiện, kết quả thực tế, đạt/không đạt và đường dẫn ảnh hoặc bằng chứng. Một số ca cần backend, mô hình hoặc bản tích hợp nên chưa áp dụng được cho khung D1.

| Mã | Nhóm | Đầu vào / bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| T01 | Thu chi | Thêm giao dịch hợp lệ | Lưu và hiển thị đúng tài khoản. |
| T02 | Thu chi | Thêm số tiền 0 | Từ chối và báo lỗi. |
| T03 | Thu chi | Nhập số tiền âm | Từ chối và báo lỗi. |
| T04 | Thu chi | Bỏ trống danh mục | Từ chối và báo trường thiếu. |
| T05 | Thu chi | Sửa giao dịch của mình | Thông tin mới được lưu đúng. |
| T06 | Thu chi | Xóa giao dịch của mình | Giao dịch không còn trong danh sách. |
| T07 | Thu chi | Lọc theo ngày, loại và danh mục | Chỉ hiển thị giao dịch thỏa điều kiện. |
| T08 | CSV | Nhập file hợp lệ | Nhập đúng số dòng theo hợp đồng. |
| T09 | CSV | Nhập file có ngày sai, số âm, thiếu trường | Báo dòng lỗi và lý do theo hợp đồng. |
| T10 | CSV | Nhập lại file đã nhập | Không tạo bản ghi trùng theo khóa đã chốt. |
| T11 | Đăng nhập | Nhập tài khoản demo đúng | Đăng nhập thành công. |
| T12 | Đăng nhập | Nhập sai mật khẩu | Không đăng nhập; hiện lỗi. |
| T13 | Phân quyền | Tài khoản A xem giao dịch B | Bị từ chối; không lộ dữ liệu. |
| T14 | Phân quyền | Tài khoản A sửa/xóa giao dịch B | Bị từ chối; dữ liệu B không đổi. |
| T15 | Phân quyền | Chưa đăng nhập gọi API dữ liệu | Bị từ chối theo hợp đồng xác thực. |
| T16 | Dashboard | Bộ mẫu thu 8 triệu, chi 750 nghìn | Tổng thu 8 triệu, chi 750 nghìn, số dư 7,25 triệu nếu số dư đầu kỳ bằng 0. |
| T17 | Dashboard | Kỳ không có chi | Hiện trạng thái phù hợp; không chia 0. |
| T18 | Mô phỏng | Mục tiêu 12 triệu, có 2 triệu, tiết kiệm 2 triệu/tháng | Giữ nguyên cần 5 tháng. |
| T19 | Mô phỏng | Đã có đủ mục tiêu | Cả ba kịch bản là 0 tháng. |
| T20 | Mô phỏng | Còn thiếu nhưng tiết kiệm mỗi tháng không dương | Báo chưa thể đạt theo giả định. |
| T21 | Dự báo | Lịch sử dưới 28 ngày | Báo chưa đủ dữ liệu. |
| T22 | Dự báo | Đủ lịch sử, API trả kết quả | Hiển thị giá trị VND, thời điểm và khoảng 7 ngày đúng. |
| T23 | Dự báo | API hoặc file mô hình không sẵn sàng | Hiển thị lỗi/trạng thái dự phòng đúng, không bịa kết quả. |
| T24 | Cảnh báo | API trả danh sách cảnh báo | Hiển thị đúng giao dịch và ngữ cảnh. |
| T25 | Cảnh báo | Gửi phản hồi đúng/sai thành công | Hiển thị xác nhận và backend lưu phản hồi theo hợp đồng. |
| T26 | Cảnh báo | Lưu phản hồi thất bại | Báo lỗi, không khẳng định đã lưu. |
| T27 | Khởi chạy | Chạy theo README trên môi trường đủ phụ thuộc | Ứng dụng khởi chạy và mở được. |
| T28 | Khởi chạy | Thiếu file dữ liệu demo | Báo lỗi có thể xác định nguyên nhân; không làm mất dữ liệu khác. |
| T29 | Xử lý lỗi | CSV sai định dạng hoặc mã hóa | Báo không đọc được, ứng dụng không dừng toàn bộ. |
| T30 | Xử lý lỗi | Backend không truy cập được | Thông báo lỗi phù hợp, không hiển thị dữ liệu giả là dữ liệu thật. |

## Mẫu ghi kết quả thực tế

| Mã ca | Phiên bản / ngày chạy | Dữ liệu và các bước | Kết quả thực tế | Đạt / không đạt / chưa chạy | Bằng chứng / mã lỗi |
|---|---|---|---|---|---|
| Ví dụ: T01 | Chưa chạy | Theo mô tả T01 | Chưa có | Chưa chạy | Chưa có |

## Ca bổ sung theo review — chưa chạy trên hệ thống tích hợp

| Mã | Liên kết | Điều kiện / dữ liệu | Kết quả mong đợi | Ưu tiên |
|---|---|---|---|---|
| T31 | F1/F2 | Chuyển nội bộ 500.000 VND | Không cộng vào thu hoặc chi theo quy tắc nháp. | Cao |
| T32 | F1 | CSV có hai transaction_id giống nhau | Báo các dòng trùng theo khóa nháp. | Cao |
| T33 | F1 | CSV user_id khác phiên | Cảnh báo, bỏ qua ID trong file; backend thật phải gán chủ sở hữu từ phiên. | Cao |
| T34 | F1 | CSV thiếu note | Chấp nhận nếu các trường khác hợp lệ. | Cao |
| T35 | F1 | File rỗng, sai cột, sai encoding hoặc dấu phân cách | Thông báo lỗi hoặc không có dữ liệu, không lưu. | Cao |
| T36 | F1 | CSV số tiền có dấu phân cách nghìn | Báo định dạng số nguyên không phân cách. | Vừa |
| T37 | F2 | Kỳ trước bằng 0 hoặc không có giao dịch | Không chia 0, hiển thị trạng thái phù hợp. | Cao |
| T38 | F5 | Chi tùy chọn bằng 0 | Ba kịch bản bằng nhau. | Vừa |
| T39 | F5 | Mục tiêu bằng 0, hoặc chi lớn hơn thu | Tương ứng 0 tháng hoặc chưa thể đạt. | Cao |
| T40 | F3 | 28 ngày lịch sử; baseline | Kiểm điều kiện biên và nhãn baseline theo API. | Cao |
| T41 | F4 | Không cảnh báo; gửi hai lần | Trạng thái rỗng rõ; quy tắc lưu lặp cần API chốt. | Vừa |
| T42 | F1 | Hai phiên/tài khoản | Không truy cập chéo trên backend thật. | Cao |

Các ca T31–T42 đều **chưa chạy trên hệ thống tích hợp**. Bằng chứng: điền bảng kết quả ở trên sau khi chạy. Ca số tiền âm qua CSV hoặc kiểm thử hàm, vì ô nhập UI không cho giá trị âm.

## Ma trận truy vết theo chức năng

| Chức năng | Màn hình | Ca thử liên quan |
|---|---|---|
| F1 | Đăng nhập, Thu chi, nhập CSV | T01–T15, T31–T36, T42 |
| F2 | Dashboard | T16–T17, T31, T37 |
| F3 | Dự báo | T21–T23, T40 |
| F4 | Cảnh báo | T24–T26, T41 |
| F5 | Tiết kiệm | T18–T20, T38–T39 |
| Vận hành | Khởi chạy và lỗi | T27–T30, T42 |

Các kiểm thử tự động trong `tests/test_d1.py` xác minh một số quy tắc CSV, mock và tiết kiệm, cùng smoke giao diện; chúng không chứng minh toàn bộ 42 ca đã chạy trên hệ thống tích hợp. Xem kết quả lệnh pytest mới nhất để xác định trạng thái; các ca thủ công vẫn chờ chạy và lưu bằng chứng.
