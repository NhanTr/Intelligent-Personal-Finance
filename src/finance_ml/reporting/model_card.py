"""Model Card markdown renderer keeping synthetic and real_public strictly separated."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finance_ml.models.registry import resolve_pointer_bundle_dir


def _format_stream_card(dataset_name: str, ds_dir: Path) -> str:
    label = (
        "Luồng A — Mô phỏng Đa người dùng VND (`synthetic` — Minh họa kỹ thuật)"
        if dataset_name == "synthetic"
        else "Luồng B — Dữ liệu Công khai Kaggle (`real_public` — Benchmark thực tế 1 hộ gia đình)"
    )
    active_ptr = ds_dir / "models" / "active.json"
    val_path = ds_dir / "metrics" / "validation_metrics.json"
    test_path = ds_dir / "metrics" / "test_metrics.json"
    inj_path = ds_dir / "metrics" / "synthetic_anomaly_eval.json"
    lat_path = ds_dir / "metrics" / "latency_benchmark.json"

    if not active_ptr.exists() or not val_path.exists():
        return f"## {label}\n\n*Chưa có mô hình huấn luyện cho luồng `{dataset_name}`.*\n"

    ptr = json.loads(active_ptr.read_text(encoding="utf-8"))
    meta = json.loads((resolve_pointer_bundle_dir(active_ptr) / "metadata.json").read_text(encoding="utf-8"))
    val = json.loads(val_path.read_text(encoding="utf-8"))

    lines: list[str] = [
        f"## {label}",
        "",
        f"- **Phiên bản đang kích hoạt (`active`):** `{ptr['version']}`",
        f"- **Thời điểm huấn luyện:** `{meta.get('trained_at')}` | **scikit-learn:** `{meta.get('sklearn_version')}` | **Seed:** `{meta.get('seed')}`",
        f"- **Mốc chia tập (60/20/20):** `{json.dumps(meta.get('cutoffs', {}), ensure_ascii=False)}`",
        f"- **Mô hình F3 được chọn trên Validation:** `{val['selected_forecast_model']}` (Fallback cơ sở: `{meta.get('forecast_fallback_used')}`)",
        "",
        "### Kết quả F3 trên Validation (Đơn vị: VND — Không dùng MAPE)",
        "",
        "| Mô hình | MAE (VND) | RMSE (VND) | Số mẫu | Cải thiện vs Baseline (%) | Đạt mục tiêu >= 10%? |",
        "| :--- | ---: | ---: | ---: | ---: | :---: |",
    ]

    for m_name, m_val in val["forecast_validation"].items():
        imp = m_val.get("improvement_vs_baseline_pct")
        imp_str = f"{imp:+.2f}%" if imp is not None else "—"
        target_ok = m_val.get("meets_10pct_target")
        ok_str = "Đạt" if target_ok is True else ("Chưa đạt" if target_ok is False else "—")
        lines.append(
            f"| `{m_name}` | {float(m_val['mae_vnd']):,.0f} | {float(m_val['rmse_vnd']):,.0f} | {int(m_val['n_samples'])} | {imp_str} | {ok_str} |"
        )

    anom_v: dict[str, Any] = val["anomaly_validation"]
    lines.extend(
        [
            "",
            "### Kết quả F4 (Isolation Forest) trên Validation",
            f"- **Ngưỡng bất thường (`threshold`):** `{float(anom_v['threshold']):.6f}`",
            f"- **Tỷ lệ cảnh báo trên Validation:** `{float(anom_v['alert_rate']) * 100:.2f}%` (`{anom_v['flagged_count']}/{anom_v['total_evaluated']}` giao dịch)",
            "- **Lưu ý nghiệp vụ:** Điểm bất thường không phải xác suất gian lận; chỉ cảnh báo để người dùng xem xét và xác nhận đúng/sai.",
        ]
    )

    if inj_path.exists():
        inj = json.loads(inj_path.read_text(encoding="utf-8"))
        lines.extend(
            [
                "",
                "### Kết quả Nhóm Kiểm thử Chèn Bất thường Mô phỏng (Tách riêng)",
                f"- **Precision:** `{inj['precision']:.3f}` | **Recall:** `{inj['recall']:.3f}` | **F1:** `{inj['f1']:.3f}` | **Số cảnh báo:** `{inj['alert_count']}/{inj['total_evaluated']}`",
            ]
        )

    if lat_path.exists():
        lat = json.loads(lat_path.read_text(encoding="utf-8"))
        lines.extend(
            [
                "",
                "### Hiệu năng Suy luận (1 người dùng sau khi nạp mô hình)",
                f"- **Số lần đo:** `{lat['n_runs']}` | **Mean:** `{lat['mean_latency_sec']*1000:.2f} ms` | **P95:** `{lat['p95_latency_sec']*1000:.2f} ms` | **Max:** `{lat['max_latency_sec']*1000:.2f} ms` (Mục tiêu `<= 3.0s`: `{'Đạt' if lat['meets_3s_sla'] else 'Chưa đạt'}`)",
                f"- **Cấu hình máy:** `{lat['machine_info']['platform']} ({lat['machine_info']['machine']}) — Python {lat['machine_info']['python_version']}`",
            ]
        )

    lines.append("")
    lines.append("### Kết quả trên Tập Test Độc lập")
    if not test_path.exists():
        lines.append(
            "- **Trạng thái:** **ĐANG KHÓA (Quy tắc 2A — Pre-Test / Validation Ready)** — Tập `test` chưa mở để bảo toàn tính độc lập tuyệt đối. Khi nhóm chốt cấu hình cuối, chạy `scripts/evaluate.py --dataset "
            f"{dataset_name} --unlock-test --reason '<lý do>'` đúng 1 lần để cập nhật mục này."
        )
    else:
        t_data = json.loads(test_path.read_text(encoding="utf-8"))
        lines.extend(
            [
                f"- **Số lần mở khóa Test:** `{t_data['unlock_count']}`",
                "",
                "| Mô hình | Test MAE (VND) | Test RMSE (VND) | Số mẫu | Cải thiện vs Baseline (%) |",
                "| :--- | ---: | ---: | ---: | ---: |",
            ]
        )
        for m_name, m_val in t_data["forecast_test"].items():
            imp = m_val.get("improvement_vs_baseline_pct")
            imp_str = f"{imp:+.2f}%" if imp is not None else "—"
            lines.append(
                f"| `{m_name}` | {float(m_val['mae_vnd']):,.0f} | {float(m_val['rmse_vnd']):,.0f} | {int(m_val['n_samples'])} | {imp_str} |"
            )
    lines.append("")
    return "\n".join(lines)


def render_model_card(out_path: Path, artifacts_root: Path) -> Path:
    out_path = Path(out_path)
    artifacts_root = Path(artifacts_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    syn_block = _format_stream_card("synthetic", artifacts_root / "synthetic")
    pub_block = _format_stream_card("real_public", artifacts_root / "real_public")

    content = "\n".join(
        [
            "# Model Card — Hệ thống Dự báo Chi tiêu (F3) & Cảnh báo Bất thường (F4)",
            "",
            "## 1. Mục tiêu và Phạm vi Sử dụng",
            "- **F3 (Hồi quy):** Dự báo tổng chi tiêu (VND) trong **7 ngày tiếp theo** cho người dùng có tối thiểu **28 ngày lịch sử**.",
            "- **F4 (Isolation Forest):** Chấm điểm mức độ bất thường cho từng giao dịch chi tiêu (không tính chuyển khoản nội bộ) kèm lời giải thích ngữ cảnh để người dùng tự kiểm tra.",
            "- **Giới hạn quan trọng:**",
            "  - Không dự đoán cho người dùng `< 28 ngày` lịch sử (`status = insufficient_data`).",
            "  - Không tự động quy đổi dự báo 7 ngày thành dự báo tháng.",
            "  - Điểm bất thường **không phải** xác suất gian lận; hệ thống tuyệt đối không tự xóa hay chặn giao dịch.",
            "  - Kết quả trên dữ liệu mô phỏng (`synthetic`) chỉ mang tính minh họa kỹ thuật, không chứng minh hiệu quả thực tế bên ngoài.",
            "",
            syn_block,
            "---",
            "",
            pub_block,
        ]
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path
