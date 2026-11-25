# Báo cáo Khám phá Dữ liệu (EDA)

> **Nguyên tắc tách biệt:** Kết quả giữa dữ liệu mô phỏng (`synthetic`) và dữ liệu công khai (`real_public`) được báo cáo hoàn toàn độc lập; dữ liệu mô phỏng chỉ dùng để minh họa kỹ thuật và kiểm thử luồng đa người dùng VND.

<!-- EDA_SECTION:synthetic:START -->
## Luồng A — Dữ liệu Mô phỏng Đa người dùng VND (`synthetic`)

- **Nguồn / Bộ sinh:** `finance_ml.data.synthetic.generate_synthetic_dataset`
- **Điều kiện sử dụng:** Internal academic simulation dataset; technical illustration only (not real-world efficacy proof).
- **Số hồ sơ:** `9` | **Khoảng thời gian:** `2026-01-01` → `2026-10-27`
- **Tổng giao dịch hợp lệ:** `4,182` | **Giao dịch chuyển khoản nội bộ (đã tách):** `116`
- **Tỷ lệ thiếu / lỗi bị loại:** `0.00%` | **Tỷ lệ ngày chi = 0 VND:** `19.88%`
- **Ghi chú tiền tệ:** Generated natively in VND.

### Phân bố chi tiêu theo danh mục (đã loại chuyển khoản nội bộ)

| Danh mục | Số giao dịch | Tổng chi (VND) |
| :--- | ---: | ---: |
| `housing` | 81 | 369,759,000 |
| `food` | 2869 | 304,273,000 |
| `utilities` | 80 | 55,429,000 |
| `transport` | 696 | 49,554,000 |
| `health` | 72 | 18,724,000 |
| `entertainment` | 70 | 16,663,000 |
| `education` | 62 | 14,384,000 |
| `shopping` | 55 | 14,138,000 |

### Biểu đồ EDA
- Xu hướng chi tiêu ngày: `artifacts/synthetic/figures/daily_spending_trend.png`
- Tỷ trọng danh mục: `artifacts/synthetic/figures/category_share.png`
- Phân phối log số tiền giao dịch: `artifacts/synthetic/figures/amount_log_distribution.png`
<!-- EDA_SECTION:synthetic:END -->

---

<!-- EDA_SECTION:real_public:START -->
## Luồng B — Dữ liệu Công khai Kaggle (`real_public`)

*Chưa có tệp `data/raw/daily_household_transactions.csv` — chạy `prepare_public_data.py` và `run_eda.py --dataset real_public` khi tải CSV về.*
<!-- EDA_SECTION:real_public:END -->
