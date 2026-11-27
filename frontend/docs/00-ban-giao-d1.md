# Sổ Mây · Bàn giao D1

- **Người thực hiện** Duy
- **Người rà soát theo phân công** Nhân
- **Trạng thái** Sẵn sàng để Nhân rà soát wireframe và mock. Khoa cần xác nhận hợp đồng K1 trước khi chốt việc đối chiếu API.

## Đầu ra theo phân công

- **Wireframe 5 luồng** gồm F1 đăng nhập và thu chi, F2 dashboard, F3 dự báo, F4 cảnh báo và F5 mô phỏng tiết kiệm. [Sơ đồ wireframe](../wireframe-tong-quan.svg) · [Luồng sử dụng](01-luong-su-dung.md) · [Đặc tả màn hình](02-wireframe.md)
- **Khung giao diện gọi mock** có luồng chính và các trạng thái lỗi, trống, thiếu dữ liệu. Mock là các đối tượng Python trong phiên. F3 và F4 đọc mẫu JSON của contract ML của Nhân. [Mã giao diện](../wireframe_d1.py) · [Cách chạy Windows](../chay-wireframe-d1.bat) · [Hợp đồng API nháp](04-hop-dong-api-nhap.md)
- **CSV mẫu** có file hợp lệ, file có lỗi theo dòng và file trùng khóa. [File hợp lệ](../data/giao-dich-hop-le.csv) · [File có lỗi](../data/giao-dich-co-loi.csv) · [File trùng khóa](../data/giao-dich-trung-khoa.csv)
- **Ca kiểm thử** có mã ca, kết quả mong đợi và điều kiện. Ảnh chạy mock gồm [đăng nhập](images/01-dang-nhap.png), [Thu chi](images/02-thu-chi.png), [Dashboard](images/03-dashboard.png), [Dự báo](images/04-du-bao.png), [Cảnh báo](images/05-canh-bao.png) và [Tiết kiệm](images/06-tiet-kiem.png). [Danh sách ca kiểm thử](03-test-case.md)

## Lượt rà soát đề nghị cho Nhân

1. Mở sơ đồ trước, sau đó đăng nhập wireframe bằng `U001`, mật khẩu `demo`. Đi qua cả năm màn hình và đối chiếu tên trường, thứ tự thao tác và thông báo.
2. Chọn `U003` để xem trạng thái trống trước khi nhập. Trong Thu chi, thử CSV có lỗi rồi CSV hợp lệ. Mẫu hợp lệ có 7 dòng. Tổng thu 8.000.000 VND, tổng chi 750.000 VND và chênh lệch 7.250.000 VND theo quy tắc nháp loại chuyển nội bộ.
3. Ở Dự báo, chọn **Chưa đủ dữ liệu** trong mục **Kiểm thử wireframe D1** và kiểm tra màn hình để trống số dự báo. Ở Cảnh báo, kiểm tra lý do và nút **Đúng/Sai**. Phản hồi lưu trong phiên demo.
4. Ở Tiết kiệm, kiểm tra ba kịch bản cho mục tiêu 12 triệu, đã có 2 triệu, thu 8 triệu/tháng, chi thiết yếu 4 triệu/tháng và chi tùy chọn 3 triệu/tháng. Kết quả lần lượt là 10, 8 và 7 tháng.
5. Ghi nhận từng phát hiện theo mẫu sau và chuyển cho Duy sửa trước khi Khoa chốt tích hợp.

```text
Người rà soát / Ngày
Màn hình hoặc mã ca
Bước tái hiện
Kết quả quan sát
Góp ý hoặc điều cần chốt
```

## Các mục còn chờ

- **Nhân** rà soát độc lập năm luồng, trạng thái và kết quả trong gói. Mục rà soát đang mở.
- **Khoa** xác nhận hợp đồng HTTP K1, các trường giao dịch, khóa chống trùng và cách xử lý lỗi nhập CSV. Kiểm thử API, xác thực, lưu cơ sở dữ liệu và phản hồi ngoài phiên thuộc phần tích hợp sau.
