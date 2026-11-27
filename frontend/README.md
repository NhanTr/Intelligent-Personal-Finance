# Sổ Mây · Wireframe D1

## Cài lần đầu

Mở PowerShell tại thư mục gốc `Intelligent-Personal-Finance`. Cần có Python 3.12. Nếu đã có `.venv`, bỏ qua lệnh tạo môi trường.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r frontend\requirements.txt -c requirements-ml.txt
```

## Chạy và chọn màn

Nếu [127.0.0.1:8502](http://127.0.0.1:8502) đã mở được thì vào thẳng. Khi chưa chạy app, mở PowerShell tại thư mục gốc và chạy:

```powershell
cd frontend
..\.venv\Scripts\python.exe -m streamlit run .\wireframe_d1.py --server.address 127.0.0.1 --server.port 8502
```

Giữ PowerShell mở. Vào [127.0.0.1:8502](http://127.0.0.1:8502) và kiểm tra tab có tên **Sổ Mây · Wireframe D1**. Chọn `U001`, nhập mật khẩu `demo` và bấm **Vào không gian tài chính**.

Chọn màn ở thanh bên trái, ngay trong tab đang mở. Nếu thanh bên đang ẩn, bấm `»` ở góc trên bên trái.

- **Nghiệp vụ** — Dashboard, Thu chi. Muốn nhập CSV, vào **Thu chi → Thêm giao dịch hoặc nhập CSV → Nhập CSV**.
- **Thông minh** — Dự báo, Cảnh báo, Tiết kiệm.

## Rà soát

Nhân mở [phiếu bàn giao D1](docs/00-ban-giao-d1.md) để đối chiếu năm luồng, thử CSV và ghi góp ý. Đây là bản mock dùng dữ liệu giả lập trong phiên.
