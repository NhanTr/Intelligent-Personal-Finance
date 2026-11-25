# Kiểm thử, Quản lý Rủi ro và Hồ sơ Bàn giao Cuối kỳ

---

## 1. Tiêu chí Chất lượng Nội bộ & Kiểm thử

**Bộ kiểm thử tối thiểu 30 ca (Duy duy trì):**
- 10 ca thu chi / nhập CSV
- 5 ca đăng nhập và tách dữ liệu theo người dùng
- 5 ca thống kê / mô phỏng tiết kiệm
- 6 ca dự báo / cảnh báo bất thường
- 4 ca khởi chạy và xử lý lỗi
- *Mỗi ca phải ghi rõ:* dữ liệu vào, bước thực hiện, kết quả mong đợi, kết quả thực tế và bằng chứng.

| Hạng mục | Điều kiện nghiệm thu |
| :--- | :--- |
| **Luồng bắt buộc** | 100% ca quan trọng của F1–F5 đạt; tổng số ca đạt tối thiểu **95%**; không còn lỗi gây mất dữ liệu, lộ dữ liệu chéo hoặc chặn demo. |
| **Tính đúng** | Dashboard và 3 kịch bản tiết kiệm khớp bộ dữ liệu kiểm tra tay; nhập CSV không nhân đôi dữ liệu ngoài quy tắc đã chốt. |
| **ML và tái lập** | Có baseline, chia tập theo thời gian, metrics thực đo và phân tích hạn chế; người thứ hai chạy lại được. Mục tiêu cải thiện 10% được báo đạt/chưa đạt rõ ràng. |
| **Khả năng dùng** | 3–5 người tự nguyện thử 5 luồng, ghi số luồng tự hoàn thành và phản hồi; nếu chỉ thử nội bộ phải nêu đúng đối tượng. |
| **Khởi chạy & Hiệu năng** | Có dữ liệu demo và hướng dẫn; mục tiêu phản hồi suy luận **không quá 3 giây** ở 1 người dùng sau khi nạp mô hình. Ghi cấu hình máy và kết quả **ít nhất 20 lần thử**. |

---

## 2. Quản lý Rủi ro

| Rủi ro và Dấu hiệu | Người xử lý | Hành động ứng phó |
| :--- | :--- | :--- |
| **Ngày 3 thiếu dữ liệu theo thời gian** | **Nhân**; Khoa chốt | Đổi nguồn hoặc trình phương án mô phỏng có ghi nhãn; thống nhất phạm vi đánh giá với giảng viên. |
| **Ngày 13 mô hình kém baseline** | **Nhân** | Rà đặc trưng/rò rỉ trên validation; giữ baseline khi cần; báo kết quả thực thay vì hứa độ chính xác. |
| **Bàn giao API hoặc UI trễ quá 1 ngày** | Khoa | Dùng JSON mẫu; chia nhỏ PR; ưu tiên một luồng chạy được rồi mở rộng. |
| **Thành viên bận từ 2 ngày liên tiếp** | Khoa | Nhận bàn giao phần chưa xong; phân lại theo giờ còn trống; bỏ phần tùy chọn, không tăng âm thầm tải người khác. |
| **Ngày 22 lỗi môi trường demo** | Duy + Khoa | Dùng bản phụ thuộc đã khóa, kiểm tra máy dự phòng, video và bộ dữ liệu cố định. |

---

## 3. Hồ sơ Bàn giao Cuối kỳ

| Sản phẩm | Người tổng hợp | Minh chứng hoàn thành |
| :--- | :--- | :--- |
| **Mã nguồn và ứng dụng** | Khoa | Repo có lịch sử đóng góp; bản phát hành cuối; `requirements` đã khóa; `README`; cấu hình mẫu; dữ liệu demo; hướng dẫn khởi chạy từ đầu. |
| **Dữ liệu và mô hình** | **Nhân** | Nguồn/điều kiện dùng; từ điển; EDA; script train/evaluate; mô hình; metrics; seed; model card. **Không đưa dữ liệu cá nhân chưa ẩn danh vào repo.** |
| **Báo cáo cuối môn** | Khoa | Khoa ghép và rà tính nhất quán; **Nhân xác nhận số liệu ML**; Duy xác nhận giao diện và kết quả kiểm thử. |
| **Slide và demo** | Duy | Slide có kết quả thực nghiệm; video dự phòng; kịch bản demo; cả ba người hiểu luồng hệ thống và phần mình phụ trách. |
| **Hồ sơ kiểm thử và đóng góp** | Duy | Danh sách test, lỗi đã sửa, phản hồi người dùng; Khoa tổng hợp task/commit/PR và giờ thực tế của từng thành viên. |

---

## 4. Phân công Viết Báo cáo & Kịch bản Demo 10 Phút

### 4.1. Phân công Nội dung Báo cáo
- **Khoa:** Bài toán, mục tiêu, yêu cầu, kiến trúc và triển khai; tổng hợp kết luận cùng cả nhóm.
- **Nhân:** Dữ liệu, tiền xử lý, mô hình, thực nghiệm và hạn chế.
- **Duy:** Giao diện, kịch bản sử dụng, kiểm thử và phản hồi.
*(Cấu trúc cuối cùng điều chỉnh theo mẫu giảng viên đã chốt Ngày 1.)*

### 4.2. Kịch bản Demo Đề xuất (10 phút)
1. **Khoa (2 phút):** Trình bày bài toán và kiến trúc.
2. **Duy (3 phút):** Thao tác thu chi, phân tích và mô phỏng.
3. **Nhân (3 phút):** Trình bày dự báo, cảnh báo và thực nghiệm.
4. **Cả nhóm (2 phút):** Nêu hạn chế và hướng cải thiện.
*(Điều chỉnh thời lượng theo yêu cầu giảng viên.)*
