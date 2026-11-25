# Kế hoạch Dự án: Intelligent Personal Finance Decision Support System

> **Nguồn:** `Ke_hoach_Phan_cong_PTHTTM_Khoa_Nhan_Duy_25_ngay.docx` (Phiên bản 1.0 · Ngày lập: 12/11/2026)  
> **Môn học:** Phát triển hệ thống thông minh  
> **Nhóm thực hiện:** Khoa (Team Leader / Điều phối), **Nhân**, Duy

---

## 1. Mục tiêu và Thời hạn

Trong **25 ngày lịch liên tục** (tính cả ngày bắt đầu và cuối tuần, giờ Việt Nam), nhóm xây dựng bản ứng dụng có thể chạy và trình diễn đầy đủ:
- Luồng thu chi
- Phân tích hành vi
- Dự báo chi tiêu
- Cảnh báo giao dịch bất thường
- Mô phỏng tiết kiệm

**Sản phẩm bàn giao cuối kỳ:** Mã nguồn, dữ liệu có nguồn gốc rõ ràng, mô hình đã đánh giá, báo cáo, slide và video demo dự phòng.

| Nội dung | Mốc thực hiện |
| :--- | :--- |
| **Bắt đầu** | 12/11/2026 — Ngày 1 |
| **Tích hợp đủ chức năng** | 27/11/2026 — Hết Ngày 16 |
| **Bản sẵn sàng bàn giao** | 03/12/2026 — Hết Ngày 22 |
| **Hoàn thiện và dự phòng** | 04–06/12/2026 — Ngày 23–25 |
| **Kết thúc** | 06/12/2026 — Ngày 25, bàn giao nội bộ trước **20:00** |

> [!NOTE]
> Mốc 06/12 là hạn hoàn thành theo kế hoạch nội bộ; hạn nộp chính thức thực hiện theo thông báo của giảng viên (Khoa chốt với giảng viên ngay Ngày 1).

---

## 2. Nguồn lực và Lựa chọn Triển khai

- **Nguồn lực dự kiến:** Trung bình **3 giờ/ngày/người** → **75 giờ/người** → **225 giờ cả nhóm**.
  - Ngày 1–22: 66 giờ/người cho công việc phân bổ.
  - Ngày 23–25: 9 giờ/người để sửa lỗi cuối, diễn tập và bàn giao.
- **Ngăn xếp công nghệ (Tech Stack):**
  - Ứng dụng Python: **Streamlit** (giao diện), **FastAPI** (nghiệp vụ & suy luận), **SQLite** (lưu trữ), **pandas** và **scikit-learn** (xử lý dữ liệu & ML).
  - UI gọi API; mô hình huấn luyện ngoại tuyến rồi nạp vào backend.
  - Chốt phiên bản thư viện trong Ngày 2 và giữ nhất quán giữa huấn luyện và demo.
- **Ngoài phạm vi 25 ngày:** Liên kết ngân hàng thật, thanh toán, OCR hóa đơn, chatbot, ứng dụng di động, microservice, tự động giao dịch. Demo chạy local (không bắt buộc thuê server).

---

## 3. Chức năng Bắt buộc (F1–F5)

| Mã | Phạm vi nghiệm thu | Chủ trì |
| :--- | :--- | :--- |
| **F1** | Đăng nhập tài khoản demo; thêm, sửa, xóa, lọc thu chi; nhập CSV; dữ liệu tách theo người dùng. | Khoa |
| **F2** | Dashboard tổng thu, chi, số dư; tỷ trọng danh mục; so sánh hai kỳ và xu hướng chi tiêu. | Duy |
| **F3** | Dự báo tổng chi 7 ngày tiếp theo; so sánh Linear Regression, Random Forest và mô hình cơ sở. | **Nhân** |
| **F4** | Isolation Forest chấm điểm bất thường; UI giải thích ngữ cảnh và cho xác nhận đúng/sai. | **Nhân** |
| **F5** | So sánh ít nhất 3 kịch bản tiết kiệm dựa trên thu nhập, chi phí và mục tiêu người dùng nhập. | Duy |

---

## 4. Các Mốc Nghiệm thu Chính (M1–M5)

| Mốc | Hạn cuối | Điều kiện qua mốc |
| :--- | :--- | :--- |
| **M1** | 15/11 · Ngày 4 | K1/N1/D1 được rà soát; phạm vi và dữ liệu khả thi. |
| **M2** | 21/11 · Ngày 10 | CRUD/CSV/dashboard chạy; có mô hình bản đầu và metrics. |
| **M3** | 27/11 · Ngày 16 | F1–F5 chạy xuyên suốt; có kết quả ML và phương án lỗi. |
| **M4** | 03/12 · Ngày 22 | Có báo cáo, slide, kiểm thử, README và bản demo cài lại được. |
| **M5** | 06/12 · Ngày 25 | Gói bàn giao kiểm tra đầy đủ; lưu dấu vết nộp hoặc bàn giao. |

> [!IMPORTANT]
> Khoa chịu trách nhiệm chốt mốc; người rà soát xác nhận theo minh chứng. Mọi mục mới phát sinh sau **Ngày 16** chuyển sang hướng phát triển sau môn học.

---

## 5. Quy trình Làm việc & Quy tắc Nhóm

- **Cập nhật hàng ngày:** Cập nhật bảng việc trước **21:00** mỗi ngày; họp trao đổi **10 phút lúc 21:00**.
- **Trạng thái thẻ việc:** `Chưa làm` → `Đang làm` → `Chờ rà soát` → `Hoàn thành`. Mỗi thẻ ghi: mã gói, người làm, hạn, phụ thuộc, tiêu chí và link minh chứng.
- **Xử lý vướng mắc (Blocker):** Người gặp blocker báo trong **12 giờ**; Khoa xử lý hoặc phân lại trong **24 giờ**.
- **Quy tắc Git & Review:**
  - Dùng nhánh riêng và Pull Request (PR); **không tự duyệt phần mình**.
  - Khoa duyệt tích hợp. PR của Khoa do **Duy rà soát**, **Nhân kiểm tra phần liên quan ML**.
  - Một đầu việc chỉ đánh dấu Hoàn thành khi: có sản phẩm + kiểm tra tương ứng + tài liệu đã cập nhật + người rà soát xác nhận.

---

## 6. Cấu trúc Thư mục Kế hoạch

- [nhan-checklist-and-notes.md](file:///Users/nhantr/Documents/PTIT/Intelligent%20Personal%20Finance%20Decision%20Support%20System/plans/nhan-checklist-and-notes.md) — **Sổ tay riêng của Nhân**: các quy tắc dữ liệu, ML, chống rò rỉ, mốc phối hợp, trách nhiệm review & bàn giao cần nhớ.
- [team-work-packages.md](file:///Users/nhantr/Documents/PTIT/Intelligent%20Personal%20Finance%20Decision%20Support%20System/plans/team-work-packages.md) — Chi tiết các gói việc `K1–K4`, `N1–N4`, `D1–D4`, `GĐ 5` và cơ chế phối hợp.
- [schedule-25-days.md](file:///Users/nhantr/Documents/PTIT/Intelligent%20Personal%20Finance%20Decision%20Support%20System/plans/schedule-25-days.md) — Lịch trình chi tiết từng ngày từ Ngày 01 (12/11) đến Ngày 25 (06/12).
- [qa-risks-and-deliverables.md](file:///Users/nhantr/Documents/PTIT/Intelligent%20Personal%20Finance%20Decision%20Support%20System/plans/qa-risks-and-deliverables.md) — Tiêu chí kiểm thử, quản lý rủi ro, hồ sơ bàn giao và kịch bản demo 10 phút.

---

## 7. Tài liệu Tham khảo Gốc

1. Tài liệu giảng viên, `C3 - Xay dung va Trien khai HT thong minh - 1(1).pdf`, trang PDF 3–13: bài toán, mục tiêu, dữ liệu, độ đo, học máy và cải thiện hệ thống.
2. Tài liệu giảng viên, `C3 - Xay dung va Trien khai HT thong minh - 2(1).pdf`, trang PDF 1–2: phối hợp thành phần, tích hợp, giám sát và tương tác người dùng.
3. Tài liệu giảng viên, `C4 - Phat trien ung dung(1).pdf`, trang PDF 3, 8–11 và 14: quy trình, module quản lý/học máy, lưu và dùng mô hình, đánh giá hệ thống.
4. scikit-learn, *Common pitfalls and recommended practices*: https://scikit-learn.org/stable/common_pitfalls.html (tránh rò rỉ dữ liệu).
5. scikit-learn, *IsolationForest*: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html (điểm bất thường và ngưỡng).
