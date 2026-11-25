# Sổ tay Theo dõi của Nhân (Những thông tin bắt buộc phải nhớ)

Tài liệu này tổng hợp toàn bộ trách nhiệm, quy tắc kỹ thuật, mốc bàn giao và điểm cần lưu ý dành riêng cho **Nhân**.

---

## 1. Vai trò & Phạm vi Phụ trách

- **Chức năng chủ trì:**
  - **F3:** Dự báo tổng chi 7 ngày tiếp theo (Linear Regression, RandomForestRegressor, Baseline).
  - **F4:** Phát hiện giao dịch bất thường bằng Isolation Forest + vòng phản hồi đúng/sai.
- **Nội dung môn học phụ trách:**
  - **Dữ liệu và độ đo** (chủ trì): Nguồn dữ liệu, từ điển dữ liệu, EDA, cách chia tập và độ đo.
  - **Triển khai mô hình** (cùng Khoa): Pipeline huấn luyện, mô hình lưu được, API suy luận và UI dùng kết quả.
  - **Theo dõi và cải thiện** (cùng Khoa): Nhật ký suy luận, phản hồi cảnh báo, kịch bản lỗi và huấn luyện lại.
- **Vai trò Rà soát (Reviewer):**
  - Rà soát độc lập toàn bộ các gói của **Duy** (`D1`, `D2`, `D3`, `D4`).
  - Kiểm tra phần liên quan đến **ML** trong các Pull Request của **Khoa**.
  - Người rà soát các gói của Nhân (`N1`–`N4`) là **Khoa**.

---

## 2. Các Gói Công việc của Nhân (Tổng 75 giờ)

| Gói | Giai đoạn | Giờ | Phụ thuộc | Yêu cầu bàn giao & Điều kiện hoàn thành |
| :--- | :--- | :--- | :--- | :--- |
| **N1** | GĐ 1 (12–15/11) | 12h | Yêu cầu sơ bộ K1 ngày 1 | Khảo sát nguồn dữ liệu, EDA, từ điển dữ liệu và kế hoạch thực nghiệm. **Chốt nguồn ngày 3**; nêu rõ thời gian bao phủ, chất lượng, nguồn gốc và phương án thiếu dữ liệu. |
| **N2** | GĐ 2 (16–21/11) | 18h | N1; schema K1 | Pipeline làm sạch, đặc trưng, baseline, Linear Regression, `RandomForestRegressor` và `IsolationForest` bản đầu. Có script chạy lại, `seed`, chia tập cố định, metrics và file mô hình. |
| **N3** | GĐ 3 (22–27/11) | 18h | N2; hợp đồng K3 ngày 11 | Đánh giá theo thời gian, điều chỉnh trên validation, chốt mô hình/ngưỡng và **mở test một lần**. Có bảng so sánh, phân tích lỗi, model card và script huấn luyện lại; **không sửa theo test**. |
| **N4** | GĐ 4 (28/11–03/12) | 18h | N3; kết quả D4 từ ngày 17 | Khóa kết quả thực nghiệm, biểu đồ, mô tả dữ liệu và hạn chế; kiểm chứng khả năng tái lập. Hoàn thành chương dữ liệu/ML/đánh giá và phần slide kỹ thuật. |
| **GĐ 5** | 04–06/12 | 9h | Toàn bộ | Kiểm tra dữ liệu/mô hình, rà kết quả, trả lời câu hỏi ML, diễn tập bảo vệ. |

---

## 3. Quy tắc Dữ liệu & Phòng ngừa Rò rỉ (Không được vi phạm)

### 3.1. Nguồn dữ liệu & Điểm kiểm soát Ngày 3
- **Ưu tiên:** Dữ liệu công khai có điều kiện sử dụng rõ ràng, hoặc lịch sử thu chi tự nguyện đã ẩn danh.
- **Lưu ý:** Dữ liệu gian lận thẻ (credit card fraud) **không mặc nhiên phù hợp** cho dự báo chi tiêu cá nhân (cần có lịch sử theo thời gian và định danh người dùng).
- **Mục tiêu thu thập:**
  - Tối thiểu **180 ngày liên tục** cho mỗi hồ sơ đưa vào đánh giá dự báo (có cả ngày không phát sinh chi).
  - Khoảng **1.000+ giao dịch** là mục tiêu bổ trợ (không phải bảo đảm mô hình tốt).
  - Ghi rõ: số hồ sơ, số ngày, số giao dịch thực tế, tỷ lệ thiếu dữ liệu.
- **Phương án dự phòng (nếu hết Ngày 3 thiếu nguồn):** Khoa chốt với giảng viên dùng dữ liệu mô phỏng hoặc thu hẹp đánh giá. Dữ liệu mô phỏng phải có **bộ sinh, seed, kịch bản** và **tách khỏi dữ liệu thật** trong báo cáo (chỉ minh họa kỹ thuật).

### 3.2. Schema dữ liệu tối thiểu
- **Giao dịch:** `transaction_id`, `user_id` ẩn danh, thời điểm, loại thu/chi, số tiền dương, danh mục, ghi chú tùy chọn.
  - **VND là đơn vị duy nhất.**
  - Phân biệt chuyển khoản nội bộ để **không cộng hai lần**.
- **Tổng hợp theo ngày:** Tổng chi/ngày, số giao dịch, tỷ trọng danh mục. **Chỉ điền `0`** nếu ngày đó được xác nhận nằm trong khoảng theo dõi đầy đủ.
- **Nguồn và phiên bản:** Ghi URL/nguồn, điều kiện sử dụng, ngày lấy, phạm vi thời gian, phiên bản dữ liệu, danh sách lỗi và cách xử lý.
- **Bảo mật:** Tuyệt đối **không đưa dữ liệu cá nhân chưa ẩn danh vào repo**.

### 3.3. Chia tập & Chống Data Leakage
- **Tỷ lệ:** Chia theo mốc thời gian lịch, dự kiến **60% train / 20% validation / 20% test**. Các hồ sơ dùng cùng mốc thời gian khi huấn luyện chung.
- **Dự báo 7 ngày tới:**
  - Bỏ các mẫu huấn luyện có khoảng nhãn chạm vào kỳ validation/test.
  - Chừa khoảng cách **ít nhất 7 ngày** giữa các gốc dự báo.
  - Chỉ đánh giá mẫu có **đủ 7 ngày kết quả thực tế**.
- **Quy tắc Fit & Feature:**
  - Chỉ fit bộ xử lý dữ liệu (scaler, encoder, imputer...) và mô hình trên **train**.
  - Chọn đặc trưng, tham số và ngưỡng trên **validation**.
  - **Khóa tập test đến Ngày 14** — chỉ mở test một lần sau khi khóa cấu hình. Nếu phát hiện lỗi triển khai sau đó, phải ghi rõ lỗi và lần chạy lại; không tối ưu tham số theo kết quả test.
  - Đặc trưng trễ (lag) hoặc trung bình trượt (rolling) **chỉ dùng thông tin đã có tại thời điểm dự báo**.
  - Đợt này ưu tiên người dùng đã có lịch sử (nếu tuyên bố cho người dùng mới phải có đánh giá tách người dùng).

---

## 4. Quy tắc Thiết kế Mô hình (F3, F4 & Feedback Loop)

### 4.1. F3 — Dự báo chi tiêu 7 ngày tiếp theo (Hồi quy)
- **Mô hình:**
  1. **Baseline:** Tổng chi 7 ngày gần nhất.
  2. **Linear Regression**
  3. **RandomForestRegressor** (nhấn mạnh: đây là **hồi quy**, không tự tạo thêm bài toán phân loại khi chưa có nhãn).
- **Đặc trưng đầu vào:** Tổng chi trễ 7 / 14 / 28 ngày, trung bình và độ biến động quá khứ, số giao dịch, đặc trưng lịch (thứ, cuối tuần, ngày trong tháng...).
- **Độ đo:** **MAE** và **RMSE** (đơn vị **VND**). Báo thêm số mẫu và kết quả theo hồ sơ. **Không dùng MAPE làm độ đo chính** khi chi tiêu có thể bằng 0.
- **Mục tiêu nội bộ:** MAE trên validation **thấp hơn baseline ít nhất 10%** (đây là mục tiêu thử nghiệm, báo cáo đạt/chưa đạt trung thực).
- **Fallback:** Nếu mô hình không tốt hơn baseline → dùng baseline cho demo và trình bày kết quả thực, nguyên nhân cùng hướng cải thiện.
- **Điều kiện lịch sử:** Người có **dưới 28 ngày lịch sử** nhận trạng thái **"Chưa đủ dữ liệu"**.

### 4.2. F4 — Phát hiện bất thường bằng Isolation Forest
- **Đặc trưng dự kiến:** `log(số tiền)`, mức lệch so với lịch sử của chính người dùng, tần suất giao dịch, danh mục.
- **Ngưỡng:** Chọn ngưỡng trên **validation**; ghi lại tỷ lệ cảnh báo.
- **Nguyên tắc nghiệp vụ:** Điểm bất thường **không phải** xác suất gian lận. Cảnh báo chỉ để người dùng xem xét, **không tự xóa hoặc chặn giao dịch**.
- **Đánh giá:**
  - Nếu có nhãn độc lập: báo Precision, Recall, F1 và số cảnh báo.
  - Nếu **không có nhãn**: Duy cùng Khoa rà độc lập **30 giao dịch cảnh báo cao nhất** (hoặc toàn bộ nếu ít hơn) + **30 giao dịch ngẫu nhiên**; ghi tiêu chí, bất đồng và kết quả rà soát. **Không gọi** kết quả này là "độ chính xác phát hiện gian lận".
  - Ca bất thường chèn có chủ đích chỉ đánh giá trong nhóm kiểm thử mô phỏng.

### 4.3. Vòng phản hồi (Feedback Loop)
- Khoa lưu phản hồi đúng/sai của cảnh báo và phiên bản mô hình.
- Nhân cung cấp **lệnh/script huấn luyện lại** với dữ liệu cập nhật.
- Chỉ thay thế mô hình sau khi đánh giá lại đạt yêu cầu.

---

## 5. Các Mốc Phối hợp Quan trọng của Nhân

| Ngày | Việc Nhân cần giao / chốt với nhóm |
| :--- | :--- |
| **Ngày 3 (14/11)** | Bàn giao nguồn dữ liệu, EDA sơ bộ và giới hạn; Khoa duyệt nguồn / chốt phương án nếu thiếu. |
| **Ngày 4 (15/11)** | Khóa từ điển dữ liệu, mốc chia tập và kế hoạch ML (Nghiệm thu **M1 / N1**). |
| **Ngày 8 (19/11)** | **Giao định dạng đầu vào/đầu ra mô hình (mẫu)** để Khoa chuẩn bị bộ nạp; chạy Random Forest. |
| **Ngày 10 (21/11)** | **Giao mô hình bản đầu**, metrics và script chạy (Nghiệm thu **M2 / N2**). |
| **Ngày 11 (22/11)** | Chốt hợp đồng API suy luận với Khoa (K3). |
| **Ngày 14 (25/11)** | **Khóa cấu hình, mở test một lần**, lưu kết quả cuối (Khoa kiểm tra đồng bộ đặc trưng & phiên bản mô hình). |
| **Ngày 15 (26/11)** | Viết **Model Card** & kiểm tra script huấn luyện lại. |
| **Ngày 18 (29/11)** | Đánh giá cảnh báo cùng Khoa & Duy, ghi minh chứng. |
| **Ngày 22 (03/12)** | Cài lại trên môi trường sạch; xác minh mô hình (Nghiệm thu **M4**). |

---

## 6. Rủi ro Nhân trực tiếp Xử lý

1. **Ngày 3 thiếu dữ liệu theo thời gian:** Đổi nguồn hoặc trình phương án mô phỏng có ghi nhãn để Khoa chốt với giảng viên.
2. **Ngày 13 mô hình kém baseline:** Rà lại đặc trưng / rò rỉ trên validation; giữ baseline nếu cần; báo cáo kết quả thực thay vì hứa hẹn độ chính xác.

---

## 7. Hồ sơ Bàn giao & Bảo vệ Cuối kỳ của Nhân

- **Gói Dữ liệu & Mô hình (Nhân tổng hợp):** Nguồn/điều kiện dùng, từ điển dữ liệu, EDA, script train/evaluate, file mô hình, bảng metrics, cấu hình & seed, Model Card (mục tiêu, dữ liệu, giới hạn, thời điểm huấn luyện).
- **Phần Báo cáo cuối môn (Nhân viết & xác nhận số liệu ML):** Chương Dữ liệu, Tiền xử lý, Mô hình, Thực nghiệm và Hạn chế.
- **Phần Slide & Demo (10 phút):** Nhân hoàn thiện slide kỹ thuật ML và trình bày **3 phút** phần **Dự báo, Cảnh báo và Thực nghiệm** (cùng cả nhóm trình bày 2 phút hạn chế & hướng cải thiện).
