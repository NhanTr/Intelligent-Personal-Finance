"""EDA plot and separated markdown report generator."""

from __future__ import annotations

import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from finance_ml.schema import DataManifest


def _build_stream_section(
    dataset_name: str,
    clean_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    manifest: DataManifest,
    figures_rel_dir: str,
) -> str:
    exp_df = clean_df[(clean_df["type"] == "expense") & (~clean_df["is_internal_transfer"].astype(bool))]
    zero_rate = float((daily_df["total_expense_vnd"] == 0.0).mean() * 100.0) if not daily_df.empty else 0.0
    transfer_cnt = int(clean_df["is_internal_transfer"].astype(bool).sum()) if not clean_df.empty else 0

    cat_summary = (
        exp_df.groupby("category", as_index=False)["amount_vnd"]
        .agg(total_vnd="sum", count="count")
        .sort_values("total_vnd", ascending=False)
    )
    cat_lines = [
        f"| `{row['category']}` | {int(row['count'])} | {float(row['total_vnd']):,.0f} |"
        for _, row in cat_summary.iterrows()
    ]

    title_label = (
        "Luồng A — Dữ liệu Mô phỏng Đa người dùng VND (`synthetic`)"
        if dataset_name == "synthetic"
        else "Luồng B — Dữ liệu Công khai Kaggle (`real_public`)"
    )

    return "\n".join(
        [
            f"## {title_label}",
            "",
            f"- **Nguồn / Bộ sinh:** `{manifest.source_url_or_generator}`",
            f"- **Điều kiện sử dụng:** {manifest.usage_terms}",
            f"- **Số hồ sơ:** `{manifest.profile_count}` | **Khoảng thời gian:** `{manifest.min_date}` → `{manifest.max_date}`",
            f"- **Tổng giao dịch hợp lệ:** `{manifest.total_transactions:,}` | **Giao dịch chuyển khoản nội bộ (đã tách):** `{transfer_cnt:,}`",
            f"- **Tỷ lệ thiếu / lỗi bị loại:** `{manifest.missing_rate * 100:.2f}%` | **Tỷ lệ ngày chi = 0 VND:** `{zero_rate:.2f}%`",
            f"- **Ghi chú tiền tệ:** {manifest.currency_conversion_note or 'VND gốc'}",
            "",
            "### Phân bố chi tiêu theo danh mục (đã loại chuyển khoản nội bộ)",
            "",
            "| Danh mục | Số giao dịch | Tổng chi (VND) |",
            "| :--- | ---: | ---: |",
            *cat_lines,
            "",
            "### Biểu đồ EDA",
            f"- Xu hướng chi tiêu ngày: `{figures_rel_dir}/daily_spending_trend.png`",
            f"- Tỷ trọng danh mục: `{figures_rel_dir}/category_share.png`",
            f"- Phân phối log số tiền giao dịch: `{figures_rel_dir}/amount_log_distribution.png`",
            "",
        ]
    )


def generate_eda_artifacts(
    dataset_name: str,
    clean_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    manifest: DataManifest,
    figures_dir: Path,
    report_path: Path,
) -> list[Path]:
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    saved_figs: list[Path] = []
    exp_df = clean_df[(clean_df["type"] == "expense") & (~clean_df["is_internal_transfer"].astype(bool))]

    # 1. Daily total spending trend across tracked days
    p1 = figures_dir / "daily_spending_trend.png"
    fig, ax = plt.subplots(figsize=(9, 4))
    by_day = daily_df.groupby("date", as_index=False)["total_expense_vnd"].mean()
    ax.plot(pd.to_datetime(by_day["date"]), by_day["total_expense_vnd"] / 1e6, linewidth=1.2)
    ax.set_title(f"[{dataset_name}] Chi tiêu trung bình ngày trên mỗi hồ sơ (Triệu VND)")
    ax.set_xlabel("Ngày")
    ax.set_ylabel("Triệu VND")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(p1, dpi=140)
    plt.close(fig)
    saved_figs.append(p1)

    # 2. Category share bar chart
    p2 = figures_dir / "category_share.png"
    fig, ax = plt.subplots(figsize=(8, 4))
    cat_tot = exp_df.groupby("category")["amount_vnd"].sum().sort_values(ascending=True)
    ax.barh(cat_tot.index.astype(str), cat_tot.to_numpy() / 1e6)
    ax.set_title(f"[{dataset_name}] Tổng chi theo danh mục (Triệu VND)")
    ax.set_xlabel("Triệu VND")
    fig.tight_layout()
    fig.savefig(p2, dpi=140)
    plt.close(fig)
    saved_figs.append(p2)

    # 3. Log amount histogram
    p3 = figures_dir / "amount_log_distribution.png"
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(np.log10(np.maximum(exp_df["amount_vnd"].to_numpy(dtype=float), 1.0)), bins=30, edgecolor="black")
    ax.set_title(f"[{dataset_name}] Phân phối log10(amount_vnd) của giao dịch chi tiêu")
    ax.set_xlabel("log10(VND)")
    ax.set_ylabel("Số giao dịch")
    fig.tight_layout()
    fig.savefig(p3, dpi=140)
    plt.close(fig)
    saved_figs.append(p3)

    # Store per-stream markdown snippet so synthetic and real_public never overwrite each other
    sections_cache = report_path.parent / ".eda_sections.json"
    cache_data: dict[str, str] = {}
    if sections_cache.exists():
        cache_data = json.loads(sections_cache.read_text(encoding="utf-8"))

    cache_data[dataset_name] = _build_stream_section(
        dataset_name,
        clean_df,
        daily_df,
        manifest,
        figures_rel_dir=f"artifacts/{dataset_name}/figures",
    )
    sections_cache.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")

    syn_sec = cache_data.get("synthetic", "## Luồng A — Dữ liệu Mô phỏng (`synthetic`)\n\n*Chưa chạy EDA cho luồng này.*\n")
    pub_sec = cache_data.get(
        "real_public",
        "## Luồng B — Dữ liệu Công khai Kaggle (`real_public`)\n\n"
        "*Chưa có tệp `data/raw/daily_household_transactions.csv` — chạy `prepare_public_data.py` và `run_eda.py --dataset real_public` khi tải CSV về.*\n",
    )

    full_md = "\n".join(
        [
            "# Báo cáo Khám phá Dữ liệu (EDA)",
            "",
            "> **Nguyên tắc tách biệt:** Kết quả giữa dữ liệu mô phỏng (`synthetic`) và dữ liệu công khai (`real_public`) được báo cáo hoàn toàn độc lập; dữ liệu mô phỏng chỉ dùng để minh họa kỹ thuật và kiểm thử luồng đa người dùng VND.",
            "",
            syn_sec,
            "---",
            "",
            pub_sec,
        ]
    )
    report_path.write_text(full_md, encoding="utf-8")
    return saved_figs
