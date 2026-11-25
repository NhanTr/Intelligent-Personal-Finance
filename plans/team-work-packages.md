# Phân công Gói Công việc Toàn nhóm (Giai đoạn 1–5)

Mỗi gói có một người chịu trách nhiệm chính. **Rà soát** là người kiểm tra độc lập trước khi Khoa cho tích hợp. Giờ công đã bao gồm trao đổi, rà soát chéo và viết tài liệu liên quan.

---

## 1. Bảng Phân bổ Giờ công (Tổng 225 giờ)

| Thành viên | GĐ 1 (12–15/11) | GĐ 2 (16–21/11) | GĐ 3 (22–27/11) | GĐ 4 (28/11–03/12) | GĐ 5 (04–06/12) | Tổng |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Khoa** | 12 h | 18 h | 18 h | 18 h | 9 h | **75 h** |
| **Nhân** | 12 h | 18 h | 18 h | 18 h | 9 h | **75 h** |
| **Duy** | 12 h | 18 h | 18 h | 18 h | 9 h | **75 h** |
| **Cả nhóm** | **36 h** | **54 h** | **54 h** | **54 h** | **27 h** | **225 h** |

---

## 2. Giai đoạn 1: Chuẩn bị & Nền tảng (12/11 – 15/11 · Ngày 1–4)

| Gói & Người làm | Rà soát | Phụ thuộc | Bàn giao và Điều kiện hoàn thành |
| :--- | :--- | :--- | :--- |
| **K1 · Khoa** (12h) | Duy | Bắt đầu | Chốt yêu cầu, tiêu chí môn học, backlog, ERD và hợp đồng API. Có 5 nhóm chức năng, dữ liệu vào/ra, lỗi API, phân quyền và biên bản chốt phạm vi. |
| **N1 · Nhân** (12h) | Khoa | Yêu cầu sơ bộ K1 ngày 1 | Khảo sát nguồn dữ liệu, EDA, từ điển dữ liệu và kế hoạch thực nghiệm. Chốt nguồn ngày 3; nêu thời gian bao phủ, chất lượng, nguồn gốc và phương án thiếu dữ liệu. |
| **D1 · Duy** (12h) | Nhân | Use case K1 ngày 1 | Wireframe 5 luồng chức năng, bộ CSV mẫu và danh sách ca kiểm thử. Dựng khung UI gọi API giả lập theo hợp đồng được chốt ngày 2. |

---

## 3. Giai đoạn 2: Xây dựng Core & Mô hình Bản đầu (16/11 – 21/11 · Ngày 5–10)

| Gói & Người làm | Rà soát | Phụ thuộc | Bàn giao và Điều kiện hoàn thành |
| :--- | :--- | :--- | :--- |
| **K2 · Khoa** (18h) | Duy | K1; schema N1 | Backend, DB, tài khoản demo, CRUD và nhập CSV, API thống kê. Từ chối dữ liệu sai; không truy cập chéo tài khoản; nhập lại không tạo bản ghi trùng theo khóa đã thống nhất. |
| **N2 · Nhân** (18h) | Khoa | N1; schema K1 | Pipeline làm sạch, đặc trưng, baseline, Linear Regression, RandomForestRegressor và Isolation Forest bản đầu. Có script chạy lại, seed, chia tập cố định, metrics và file mô hình. |
| **D2 · Duy** (18h) | Nhân | D1; hợp đồng K1; API K2 từ ngày 6 | UI thu chi, nhập CSV, dashboard và mô phỏng tiết kiệm. Luồng dùng dữ liệu thật qua API; số liệu dashboard khớp bộ dữ liệu kiểm tra; công thức mô phỏng có kiểm chứng tay. |

### Cơ chế phối hợp để không chờ nhau
- **Ngày 2:** Khoa giao hợp đồng API và JSON mẫu; Duy dùng dữ liệu giả lập trong lúc Khoa xây backend.
- **Ngày 6:** Có API CRUD đầu tiên.
- **Ngày 8:** Nhân giao định dạng đầu vào/đầu ra mô hình để Khoa chuẩn bị bộ nạp.
- **Ngày 10:** Nhân giao mô hình bản đầu.
- **Quy tắc đổi schema:** Mọi thay đổi schema phải cập nhật đồng bộ cả **API, CSV và đặc trưng** trước khi merge.

---

## 4. Giai đoạn 3: Tích hợp ML & Hoàn thiện Tính năng (22/11 – 27/11 · Ngày 11–16)

| Gói & Người làm | Rà soát | Phụ thuộc | Bàn giao và Điều kiện hoàn thành |
| :--- | :--- | :--- | :--- |
| **K3 · Khoa** (18h) | Duy | K2; N2; D2 | Nạp mô hình, API dự báo/bất thường/phản hồi, phiên bản mô hình và log. Có phương án thiếu lịch sử, thiếu file mô hình, dữ liệu sai. Demo đủ F1–F5 ngày 16. |
| **N3 · Nhân** (18h) | Khoa | N2; hợp đồng K3 ngày 11 | Đánh giá theo thời gian, điều chỉnh trên validation, chốt mô hình/ngưỡng và mở test một lần. Có bảng so sánh, phân tích lỗi, model card và script huấn luyện lại; không sửa theo test. |
| **D3 · Duy** (18h) | Nhân | D2; API K3 từ ngày 12 | UI dự báo, cảnh báo, xác nhận phản hồi; hoàn thiện 3 kịch bản tiết kiệm. Hiển thị thời điểm dự báo, đơn vị, giới hạn và trạng thái chưa đủ dữ liệu; kiểm thử luồng xuyên suốt. |

### Chuỗi phụ thuộc cần bảo vệ
`Nguồn dữ liệu & đặc trưng được chốt` → `Mô hình bản đầu` → `Bộ nạp & API suy luận` → `Giao diện thông minh` → `Kiểm thử xuyên suốt`
- Khoa kiểm tra các bàn giao ngày **3, 8, 10, 12 và 16**; nếu trễ hơn 1 ngày phải điều chỉnh ngay.
- Không chờ đến cuối kỳ mới nối mô hình với ứng dụng.

---

## 5. Giai đoạn 4: Kiểm thử, Báo cáo & Đóng gói (28/11 – 03/12 · Ngày 17–22)

| Gói & Người làm | Rà soát | Phụ thuộc | Bàn giao và Điều kiện hoàn thành |
| :--- | :--- | :--- | :--- |
| **K4 · Khoa** (18h) | Duy | K3 + N3 + D3 | Sửa lỗi backend, kiểm tra quyền, tích hợp báo cáo, hướng dẫn chạy và đóng gói ứng dụng. Nhân hoặc Duy cài lại từ hướng dẫn thành công trên môi trường sạch. |
| **N4 · Nhân** (18h) | Khoa | N3; kết quả D4 từ ngày 17 | Khóa kết quả thực nghiệm, biểu đồ, mô tả dữ liệu và hạn chế; kiểm chứng khả năng tái lập. Hoàn thành chương dữ liệu/ML/đánh giá và phần slide kỹ thuật. |
| **D4 · Duy** (18h) | Nhân | D3; bản tích hợp K3 | Chạy bộ kiểm thử, ghi lỗi, thử với 3–5 người tự nguyện; hoàn thiện chương giao diện/kiểm thử, slide và video. Có kết quả thực tế kèm minh chứng, không ghi trước tỷ lệ đạt. |

---

## 6. Giai đoạn 5: Hoàn thiện, Diễn tập & Bàn giao (04/12 – 06/12 · Ngày 23–25)

Mỗi người dành **9 giờ cuối** cho phần mình sở hữu (ưu tiên lỗi chặn demo trước, **không thêm chức năng mới**):
- **Khoa:** Điều phối sửa lỗi, đóng gói và nộp.
- **Nhân:** Kiểm tra dữ liệu/mô hình, trả lời câu hỏi ML.
- **Duy:** Rà lại ca lỗi, quay demo và hỗ trợ trình diễn.

---

## 7. Quy tắc Phân tích Hành vi & Mô phỏng Tiết kiệm (F2 & F5 — Tham chiếu khi Review cho Duy)

- **Phân tích hành vi (F2):** Thống kê mô tả (tỷ trọng theo danh mục, xu hướng tuần, danh mục tăng mạnh giữa hai kỳ), đối soát số tiền với dữ liệu gốc; **không gắn nhãn là kết quả học máy**.
- **Mô phỏng tiết kiệm (F5):**
  - Công thức: `Tiết kiệm/tháng = Thu nhập dự kiến - Chi phí theo kịch bản`.
  - `Số tháng đạt mục tiêu = ceil((Mục tiêu - Đã có) / Tiết kiệm/tháng)`. Nếu đã đủ → `0`; nếu tiết kiệm ≤ 0 → báo chưa thể đạt mục tiêu với giả định hiện tại. Không tính lãi suất.
  - **3 kịch bản bắt buộc:** (1) Giữ nguyên mức chi; (2) Giảm 10% chi tùy chọn; (3) Giảm 20% chi tùy chọn.
  - **Ví dụ kiểm tra:** Mục tiêu 12 triệu, đã có 2 triệu, tiết kiệm 2 triệu/tháng → cần 5 tháng.
  - Dự báo 7 ngày hiển thị riêng, **không tự đổi thành dự báo tháng**.
