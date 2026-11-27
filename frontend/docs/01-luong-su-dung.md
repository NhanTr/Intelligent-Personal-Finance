# Năm luồng sử dụng hệ thống hỗ trợ quản lý tài chính cá nhân

## Mục đích và phạm vi

Tài liệu mô tả các bước người dùng thực hiện trong bản demo chạy trên máy cá nhân. Đây là đầu ra đầu tiên của gói D1, dùng làm cơ sở vẽ wireframe, thiết kế giao diện và viết ca kiểm thử. Các chức năng và quy tắc bám theo kế hoạch phân công; chi tiết màn hình và một số cách xử lý bên dưới là đề xuất cần nhóm xác nhận.

**Vai trò chính:** người dùng có tài khoản demo. Mỗi người chỉ được xem và thao tác trên dữ liệu của mình.

**Năm luồng:** F1 quản lý thu chi; F2 dashboard và phân tích hành vi; F3 dự báo chi tiêu; F4 cảnh báo bất thường; F5 mô phỏng tiết kiệm.

---

## F1 — Đăng nhập và quản lý thu chi

**Mục tiêu:** người dùng đăng nhập và quản lý các giao dịch thu, chi của mình, bao gồm nhập từ CSV.

**Điều kiện trước:** có tài khoản demo và ứng dụng đang chạy. Dữ liệu giao dịch thuộc tài khoản đang đăng nhập.

### Luồng chính

1. Người dùng mở ứng dụng và nhập thông tin tài khoản demo.
2. Hệ thống xác thực. Nếu thành công, người dùng vào màn hình chính và nhìn thấy khu vực quản lý thu chi.
3. Người dùng mở danh sách giao dịch. Mỗi dòng thể hiện tối thiểu thời điểm, loại thu/chi, số tiền, danh mục và ghi chú nếu có.
4. Người dùng chọn thêm giao dịch, nhập thời điểm, loại thu/chi, số tiền dương, danh mục và ghi chú tùy chọn.
5. Người dùng xác nhận lưu. Hệ thống kiểm tra dữ liệu, lưu giao dịch thuộc người dùng hiện tại và cập nhật danh sách.
6. Người dùng có thể chọn một giao dịch của mình để sửa hoặc xóa; có thể lọc danh sách theo các điều kiện được giao diện hỗ trợ.
7. Thay vì nhập từng dòng, người dùng chọn nhập CSV, chọn file và gửi dữ liệu. Hệ thống hiển thị kết quả nhập và lỗi theo từng dòng nếu có.

**Kết quả:** dữ liệu hợp lệ được lưu và hiển thị cho đúng tài khoản; giao dịch bị xóa không còn trong danh sách. Nhập lại không tạo bản ghi trùng theo khóa mà nhóm thống nhất.

### Tình huống cần thể hiện

- Đăng nhập sai: hiển thị thông báo để người dùng thử lại, không vào dữ liệu tài khoản.
- Giao dịch thiếu trường bắt buộc hoặc số tiền không dương: từ chối lưu và chỉ ra lỗi.
- CSV có dòng sai: hiển thị dòng và nguyên nhân; cách xử lý các dòng hợp lệ trong cùng file cần Khoa xác nhận theo hợp đồng API.
- Danh sách rỗng hoặc không có kết quả lọc: thông báo rõ trạng thái.
- Không cho xem/sửa/xóa dữ liệu của tài khoản khác; backend phải kiểm tra quyền sở hữu.

**Màn hình dự kiến:** đăng nhập; danh sách và bộ lọc; biểu mẫu thêm/sửa; khu vực nhập CSV và kết quả nhập.

---

## F2 — Dashboard và phân tích hành vi

**Mục tiêu:** giúp người dùng nắm tình hình tài chính và nhìn thấy thay đổi trong chi tiêu.

**Điều kiện trước:** người dùng đã đăng nhập. Dashboard lấy dữ liệu của chính người dùng qua API thống kê.

### Luồng chính

1. Người dùng mở dashboard và chọn khoảng thời gian xem nếu giao diện hỗ trợ.
2. Hệ thống tổng hợp và hiển thị tổng thu, tổng chi và số dư tương ứng.
3. Người dùng xem tỷ trọng chi theo từng danh mục và xu hướng chi tiêu theo tuần.
4. Người dùng xem so sánh hai kỳ và danh mục có mức chi tăng mạnh giữa hai kỳ.
5. Khi người dùng đổi khoảng thời gian hoặc điều kiện xem, giao diện cập nhật kết quả tương ứng.

**Kết quả:** người dùng thấy các chỉ số và biểu đồ có đơn vị VND, gắn với kỳ đang xem. Kết quả tổng hợp phải đối soát được với dữ liệu giao dịch nguồn.

### Tình huống cần thể hiện

- Chưa có giao dịch hoặc không có dữ liệu trong kỳ: báo chưa có dữ liệu, không tạo biểu đồ gây hiểu nhầm.
- Một kỳ không có chi tiêu: trình bày số liệu phù hợp và tránh chia cho 0 khi tính tỷ trọng hoặc mức thay đổi.
- Dữ liệu chưa tải được: báo lỗi và cho người dùng biết có thể thử lại.
- Chuyển khoản nội bộ phải được phân biệt để không cộng hai lần theo quy tắc dữ liệu của nhóm.

**Màn hình dự kiến:** dashboard gồm bộ chọn kỳ, các chỉ số tổng hợp, biểu đồ danh mục, xu hướng tuần và khu vực so sánh hai kỳ.

**Lưu ý:** đây là thống kê mô tả; không trình bày các chỉ số này như kết quả học máy. Cách xác định và hiển thị “tăng mạnh” cần nhóm chốt.

---

## F3 — Xem dự báo chi tiêu 7 ngày

**Mục tiêu:** người dùng xem dự báo tổng chi cho 7 ngày tiếp theo để tham khảo.

**Điều kiện trước:** người dùng đã đăng nhập; backend có API suy luận và mô hình hoặc phương án dự phòng đã được nhóm chuẩn bị.

### Luồng chính

1. Người dùng mở trang dự báo chi tiêu.
2. Giao diện yêu cầu kết quả dự báo cho tài khoản hiện tại.
3. Hệ thống kiểm tra lịch sử và trả về kết quả nếu có đủ dữ liệu.
4. Giao diện hiển thị tổng chi dự báo cho 7 ngày tiếp theo, đơn vị VND và thời điểm dự báo; kèm mô tả ngắn về giới hạn của kết quả.
5. Người dùng dùng kết quả như thông tin tham khảo khi xem xét kế hoạch chi tiêu.

**Kết quả:** người dùng xem được dự báo đúng khoảng thời gian, hoặc thông báo giải thích vì sao hiện chưa có kết quả.

### Tình huống cần thể hiện

- Lịch sử dưới 28 ngày: hiển thị trạng thái chưa đủ dữ liệu theo kế hoạch.
- Mô hình hoặc dịch vụ dự báo không sẵn sàng: hiển thị lỗi/trạng thái phù hợp theo phản hồi API; không hiển thị kết quả giả như kết quả thật.
- Nếu nhóm dùng baseline làm phương án dự phòng, giao diện trình bày theo thông tin backend cung cấp.

**Màn hình dự kiến:** trang dự báo với giá trị dự báo, khoảng thời gian, thời điểm tạo dự báo, đơn vị và ghi chú giới hạn.

**Ranh giới trách nhiệm:** Nhân xây dựng và đánh giá mô hình; Khoa cung cấp API; Duy hiển thị kết quả và trạng thái. Không tự chuyển dự báo 7 ngày thành dự báo tháng.

---

## F4 — Xem và phản hồi cảnh báo giao dịch bất thường

**Mục tiêu:** giúp người dùng xem xét các giao dịch được hệ thống đánh dấu và gửi phản hồi.

**Điều kiện trước:** người dùng đã đăng nhập; API cảnh báo và lưu phản hồi sẵn sàng hoặc có JSON mẫu để dựng giao diện.

### Luồng chính

1. Người dùng mở trang cảnh báo.
2. Giao diện hiển thị danh sách giao dịch được đánh dấu cùng thông tin giao dịch và ngữ cảnh giải thích do backend cung cấp.
3. Người dùng chọn một cảnh báo để xem xét.
4. Người dùng xác nhận phản hồi theo lựa chọn đúng/sai mà nhóm thống nhất với API.
5. Giao diện gửi phản hồi, hiển thị kết quả lưu và cập nhật trạng thái tương ứng.

**Kết quả:** người dùng xem được cảnh báo thuộc tài khoản của mình và gửi được phản hồi; phản hồi được backend lưu cùng phiên bản mô hình theo thiết kế của Khoa.

### Tình huống cần thể hiện

- Không có cảnh báo: thông báo hiện không có giao dịch được đánh dấu.
- Không tải được danh sách hoặc lưu phản hồi thất bại: báo lỗi, không khẳng định đã lưu thành công.
- Cảnh báo chỉ là gợi ý để xem xét: không tự xóa hoặc chặn giao dịch.
- Điểm bất thường không phải xác suất gian lận; không gắn nhãn chắc chắn là gian lận.

**Màn hình dự kiến:** danh sách cảnh báo; thông tin chi tiết/ngữ cảnh; nút phản hồi và thông báo kết quả.

**Cần nhóm xác nhận:** nội dung ngữ cảnh giải thích, ý nghĩa chính xác của lựa chọn “đúng/sai” và cấu trúc API phản hồi.

---

## F5 — Mô phỏng mục tiêu tiết kiệm

**Mục tiêu:** giúp người dùng so sánh thời gian đạt mục tiêu theo các giả định thu nhập và chi tiêu khác nhau.

**Điều kiện trước:** người dùng có thể nhập hoặc chỉnh sửa các giả định cần thiết; không tự suy diễn thu nhập từ dữ liệu thiếu.

### Luồng chính

1. Người dùng mở trang mô phỏng tiết kiệm.
2. Người dùng nhập mục tiêu, số tiền đã có, thu nhập dự kiến mỗi tháng và các khoản chi phí theo giả định; xác định phần chi tùy chọn để áp dụng mức giảm.
3. Người dùng yêu cầu tính toán.
4. Giao diện hiển thị ba kịch bản: giữ nguyên chi tiêu; giảm 10% chi tùy chọn; giảm 20% chi tùy chọn.
5. Với mỗi kịch bản, hệ thống hiển thị mức tiết kiệm mỗi tháng và số tháng dự kiến đạt mục tiêu; hiển thị chênh lệch thời gian giữa các kịch bản khi có thể so sánh.
6. Người dùng chỉnh giả định và tính lại để xem kết quả thay đổi.

**Kết quả:** ba kịch bản có công thức minh bạch, hiển thị giả định và kết quả phù hợp; không tính lãi suất.

### Quy tắc tính

- Tiết kiệm mỗi tháng = thu nhập dự kiến mỗi tháng − chi phí mỗi tháng theo kịch bản.
- Tiền còn thiếu = mục tiêu − tiền đã có.
- Nếu đã đủ mục tiêu: số tháng bằng 0.
- Nếu còn thiếu tiền và tiết kiệm mỗi tháng không dương: báo chưa thể đạt mục tiêu với giả định hiện tại.
- Các trường hợp còn lại: số tháng = tiền còn thiếu / tiết kiệm mỗi tháng, làm tròn lên.
- Ví dụ kiểm tra: mục tiêu 12 triệu, đã có 2 triệu, tiết kiệm 2 triệu/tháng → 5 tháng.

### Tình huống cần thể hiện

- Thiếu dữ liệu hoặc số tiền không hợp lệ: chỉ rõ ô cần sửa.
- Không có chi tùy chọn: ba kịch bản có thể cho cùng kết quả.
- Kết quả là mô phỏng theo giả định người dùng nhập, không phải cam kết hay dự báo tháng từ mô hình 7 ngày.

**Màn hình dự kiến:** biểu mẫu giả định; bảng so sánh ba kịch bản; giải thích công thức và các trạng thái đặc biệt.

---

## Các điểm cần xác nhận trước khi nối API

1. Khoa cung cấp use case, hợp đồng API, JSON mẫu, thông tin tài khoản demo và quy tắc xác thực.
2. Khoa và Nhân chốt tên trường, định dạng thời gian, mã loại thu/chi, danh mục và khóa chống trùng cho CSV.
3. Khoa xác nhận cách API nhập CSV xử lý file có cả dòng hợp lệ và dòng lỗi; cấu trúc lỗi theo dòng.
4. Nhóm chốt cách chọn hai kỳ, định nghĩa “danh mục tăng mạnh” và cách xử lý chuyển khoản nội bộ.
5. Nhân và Khoa xác nhận dữ liệu đầu ra dự báo/cảnh báo, nội dung giải thích và ý nghĩa phản hồi đúng/sai.
6. Nhóm chốt các trường nhập cho mô phỏng, đặc biệt là cách xác định chi phí tùy chọn.

## Tiêu chí rà soát tài liệu

- Đủ 5 nhóm chức năng F1–F5 và các bước chính của người dùng.
- Nêu được màn hình dự kiến, đầu vào, kết quả và tình huống lỗi quan trọng.
- Phân biệt rõ thống kê, dự báo, cảnh báo và mô phỏng; không gán chức năng ngoài phạm vi kế hoạch.
- Các chi tiết chưa được kế hoạch quy định được ghi là điểm cần xác nhận, không coi là yêu cầu đã chốt.

Nguồn: Ke_hoach_Phan_cong_PTHTTM_Khoa_Nhan_Duy_25_ngay.docx, kế hoạch phiên bản 1.0 ngày 12/11/2026.
