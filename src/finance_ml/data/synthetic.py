"""Deterministic synthetic multi-user VND personal finance dataset generator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
import numpy as np
import pandas as pd

from finance_ml.config import PipelineConfig
from finance_ml.data.cleaning import clean_transactions
from finance_ml.schema import DataManifest, ProfileWindow, VN_TZ


@dataclass
class SyntheticBundle:
    transactions_df: pd.DataFrame
    profile_windows: dict[str, ProfileWindow]
    anomaly_eval_df: pd.DataFrame
    manifest: DataManifest


_ARCHETYPES: list[dict[str, object]] = [
    {"name": "student_dorm", "daily_food": 65_000, "monthly_rent": 1_800_000, "monthly_util": 250_000, "salary": 4_500_000, "zero_prob": 0.24},
    {"name": "student_parttime", "daily_food": 80_000, "monthly_rent": 2_200_000, "monthly_util": 300_000, "salary": 6_000_000, "zero_prob": 0.22},
    {"name": "junior_office", "daily_food": 120_000, "monthly_rent": 3_800_000, "monthly_util": 550_000, "salary": 12_000_000, "zero_prob": 0.20},
    {"name": "mid_engineer", "daily_food": 160_000, "monthly_rent": 5_500_000, "monthly_util": 800_000, "salary": 22_000_000, "zero_prob": 0.18},
    {"name": "freelancer", "daily_food": 140_000, "monthly_rent": 4_500_000, "monthly_util": 650_000, "salary": 18_000_000, "zero_prob": 0.25},
    {"name": "sales_exec", "daily_food": 150_000, "monthly_rent": 5_000_000, "monthly_util": 700_000, "salary": 19_000_000, "zero_prob": 0.19},
    {"name": "young_couple", "daily_food": 220_000, "monthly_rent": 7_500_000, "monthly_util": 1_200_000, "salary": 30_000_000, "zero_prob": 0.16},
    {"name": "family_saver", "daily_food": 200_000, "monthly_rent": 6_500_000, "monthly_util": 1_000_000, "salary": 26_000_000, "zero_prob": 0.20},
]


def _make_ts(d: date, hour: int, minute: int) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(d, time(hour=hour % 24, minute=minute % 60), tzinfo=VN_TZ))


def _simulate_profile_rows(
    rng: np.random.Generator,
    user_id: str,
    start_date: date,
    n_days: int,
    arch: dict[str, object],
    transfer_prob: float,
    tx_prefix: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    counter = 1
    daily_food = float(arch["daily_food"])
    rent = float(arch["monthly_rent"])
    util = float(arch["monthly_util"])
    salary = float(arch["salary"])
    zero_prob = float(arch["zero_prob"])

    for offset in range(n_days):
        cur = start_date + timedelta(days=offset)
        dom = cur.day
        dow = cur.weekday()

        # Monthly salary on day 5
        if dom == 5:
            rows.append(
                {
                    "transaction_id": f"{tx_prefix}_{user_id}_{counter:05d}",
                    "user_id": user_id,
                    "timestamp": _make_ts(cur, 9, int(rng.integers(0, 59))),
                    "type": "income",
                    "amount_vnd": round(salary * float(rng.uniform(0.97, 1.05)), -3),
                    "category": "salary",
                    "is_internal_transfer": False,
                    "note": "Lương tháng",
                }
            )
            counter += 1

        # Monthly rent on day 2 (strong calendar seasonality)
        if dom == 2:
            rows.append(
                {
                    "transaction_id": f"{tx_prefix}_{user_id}_{counter:05d}",
                    "user_id": user_id,
                    "timestamp": _make_ts(cur, 10, int(rng.integers(0, 59))),
                    "type": "expense",
                    "amount_vnd": round(rent * float(rng.uniform(0.99, 1.01)), -3),
                    "category": "housing",
                    "is_internal_transfer": False,
                    "note": "Tiền thuê nhà đầu tháng",
                }
            )
            counter += 1

        # Monthly utilities on day 26
        if dom == 26:
            rows.append(
                {
                    "transaction_id": f"{tx_prefix}_{user_id}_{counter:05d}",
                    "user_id": user_id,
                    "timestamp": _make_ts(cur, 19, int(rng.integers(0, 59))),
                    "type": "expense",
                    "amount_vnd": round(util * float(rng.uniform(0.90, 1.12)), -3),
                    "category": "utilities",
                    "is_internal_transfer": False,
                    "note": "Điện nước internet cuối tháng",
                }
            )
            counter += 1

        # Internal transfer occasionally (excluded from spending totals)
        if rng.random() < transfer_prob:
            rows.append(
                {
                    "transaction_id": f"{tx_prefix}_{user_id}_{counter:05d}",
                    "user_id": user_id,
                    "timestamp": _make_ts(cur, 20, int(rng.integers(0, 59))),
                    "type": "expense",
                    "amount_vnd": round(daily_food * float(rng.uniform(3.0, 8.0)), -3),
                    "category": "transfer",
                    "is_internal_transfer": True,
                    "note": "Chuyển tiền ví nội bộ / tiết kiệm",
                }
            )
            counter += 1

        # Zero-spend day check (only on non-bill days so zero-spend days remain realistic & plentiful)
        if dom not in {2, 26} and rng.random() < zero_prob:
            continue

        # Regular daily expenses
        n_food = int(rng.integers(1, 3))
        weekend_mult = 1.25 if dow >= 5 else 1.0
        for _ in range(n_food):
            amt = max(15_000.0, round(daily_food * weekend_mult * float(rng.lognormal(0.0, 0.22)) / n_food, -3))
            rows.append(
                {
                    "transaction_id": f"{tx_prefix}_{user_id}_{counter:05d}",
                    "user_id": user_id,
                    "timestamp": _make_ts(cur, int(rng.choice([7, 12, 19])), int(rng.integers(0, 59))),
                    "type": "expense",
                    "amount_vnd": amt,
                    "category": "food",
                    "is_internal_transfer": False,
                    "note": "Ăn uống hàng ngày",
                }
            )
            counter += 1

        if rng.random() < 0.35:
            rows.append(
                {
                    "transaction_id": f"{tx_prefix}_{user_id}_{counter:05d}",
                    "user_id": user_id,
                    "timestamp": _make_ts(cur, 8, int(rng.integers(0, 59))),
                    "type": "expense",
                    "amount_vnd": max(15_000.0, round(daily_food * 0.45 * float(rng.uniform(0.8, 1.4)), -3)),
                    "category": "transport",
                    "is_internal_transfer": False,
                    "note": "Xăng xe / di chuyển",
                }
            )
            counter += 1

        if dow >= 5 and rng.random() < 0.45:
            disc_cat = str(rng.choice(["shopping", "entertainment", "health", "education"]))
            rows.append(
                {
                    "transaction_id": f"{tx_prefix}_{user_id}_{counter:05d}",
                    "user_id": user_id,
                    "timestamp": _make_ts(cur, int(rng.integers(14, 22)), int(rng.integers(0, 59))),
                    "type": "expense",
                    "amount_vnd": max(30_000.0, round(daily_food * float(rng.uniform(1.1, 2.4)), -3)),
                    "category": disc_cat,
                    "is_internal_transfer": False,
                    "note": f"Chi tiêu cuối tuần ({disc_cat})",
                }
            )
            counter += 1

    return rows


def _build_anomaly_eval_df(
    rng: np.random.Generator,
    start_date: date,
    n_users: int,
    n_days: int,
    injection_rate: float,
) -> pd.DataFrame:
    eval_rows: list[dict[str, object]] = []
    for idx in range(n_users):
        arch = _ARCHETYPES[idx % len(_ARCHETYPES)]
        uid = f"user_{idx + 1:03d}"
        base_rows = _simulate_profile_rows(
            rng=rng,
            user_id=uid,
            start_date=start_date,
            n_days=n_days,
            arch=arch,
            transfer_prob=0.0,
            tx_prefix="aeval",
        )
        exp_rows = [r for r in base_rows if r["type"] == "expense" and not r["is_internal_transfer"]]
        for r in exp_rows:
            r["is_injected_anomaly"] = False
            r["anomaly_type"] = "normal"
        eval_rows.extend(exp_rows)

    n_inject = max(18, int(len(eval_rows) * injection_rate))
    chosen_indices = rng.choice(len(eval_rows), size=min(n_inject, len(eval_rows) // 3), replace=False)
    extra_burst_rows: list[dict[str, object]] = []

    for k, row_idx in enumerate(chosen_indices):
        target = eval_rows[int(row_idx)]
        mode = k % 3
        if mode == 0:
            # Extreme amount spike (8x-14x)
            target["amount_vnd"] = round(float(target["amount_vnd"]) * float(rng.uniform(8.0, 14.0)), -3)
            target["category"] = "shopping"
            target["is_injected_anomaly"] = True
            target["anomaly_type"] = "extreme_amount_spike"
            target["note"] = "Ca mô phỏng: chi mua sắm đột biến"
        elif mode == 1:
            # Category-specific spike in transport/health
            target["category"] = "transport"
            target["amount_vnd"] = round(max(2_500_000.0, float(target["amount_vnd"]) * 9.0), -3)
            target["is_injected_anomaly"] = True
            target["anomaly_type"] = "category_outlier"
            target["note"] = "Ca mô phỏng: chi bất thường theo danh mục"
        else:
            # High-frequency burst within 1 hour + elevated amount
            base_ts = pd.Timestamp(target["timestamp"])
            target["amount_vnd"] = round(float(target["amount_vnd"]) * 5.5, -3)
            target["category"] = "entertainment"
            target["is_injected_anomaly"] = True
            target["anomaly_type"] = "burst_24h"
            for b in range(5):
                extra_burst_rows.append(
                    {
                        "transaction_id": f"{target['transaction_id']}_burst_{b}",
                        "user_id": target["user_id"],
                        "timestamp": base_ts + pd.Timedelta(minutes=8 * (b + 1)),
                        "type": "expense",
                        "amount_vnd": round(max(600_000.0, float(target["amount_vnd"]) * 0.8), -3),
                        "category": "entertainment",
                        "is_internal_transfer": False,
                        "note": "Ca mô phỏng: chuỗi giao dịch dồn dập",
                        "is_injected_anomaly": True,
                        "anomaly_type": "burst_24h",
                    }
                )

    eval_df = pd.DataFrame(eval_rows + extra_burst_rows)
    eval_df = eval_df.sort_values(["user_id", "timestamp", "transaction_id"], kind="mergesort").reset_index(drop=True)
    return eval_df


def generate_synthetic_dataset(config: PipelineConfig) -> SyntheticBundle:
    rng = np.random.default_rng(config.seed)
    scfg = config.synthetic

    all_rows: list[dict[str, object]] = []
    windows: dict[str, ProfileWindow] = {}

    for idx in range(scfg.n_core_users):
        uid = f"user_{idx + 1:03d}"
        arch = _ARCHETYPES[idx % len(_ARCHETYPES)]
        end_date = scfg.start_date + timedelta(days=scfg.core_days - 1)
        windows[uid] = ProfileWindow(user_id=uid, tracking_start_date=scfg.start_date, tracking_end_date=end_date)
        all_rows.extend(
            _simulate_profile_rows(
                rng=rng,
                user_id=uid,
                start_date=scfg.start_date,
                n_days=scfg.core_days,
                arch=arch,
                transfer_prob=scfg.internal_transfer_prob,
                tx_prefix="syn",
            )
        )

    # Cold-start short history profile (< 28 days)
    short_uid = scfg.short_user_id
    short_end = scfg.start_date + timedelta(days=scfg.short_user_days - 1)
    windows[short_uid] = ProfileWindow(
        user_id=short_uid,
        tracking_start_date=scfg.start_date,
        tracking_end_date=short_end,
    )
    all_rows.extend(
        _simulate_profile_rows(
            rng=rng,
            user_id=short_uid,
            start_date=scfg.start_date,
            n_days=scfg.short_user_days,
            arch=_ARCHETYPES[0],
            transfer_prob=scfg.internal_transfer_prob,
            tx_prefix="syn",
        )
    )

    raw_df = pd.DataFrame(all_rows)
    clean_df, report = clean_transactions(raw_df)

    # Separate synthetic anomaly evaluation suite (strictly isolated from training/main stream)
    eval_start = scfg.start_date + timedelta(days=int(scfg.core_days * 0.8))
    anomaly_eval_df = _build_anomaly_eval_df(
        rng=rng,
        start_date=eval_start,
        n_users=min(scfg.anomaly_eval_users, scfg.n_core_users),
        n_days=60,
        injection_rate=scfg.anomaly_injection_rate,
    )

    manifest = DataManifest(
        dataset_name="synthetic_multi_user_vnd",
        source_type="synthetic",
        source_url_or_generator="finance_ml.data.synthetic.generate_synthetic_dataset",
        usage_terms="Internal academic simulation dataset; technical illustration only (not real-world efficacy proof).",
        generated_or_fetched_at="2026-11-25T00:00:00+07:00",
        version="1.0.0",
        seed=config.seed,
        currency_unit="VND",
        currency_conversion_note="Generated natively in VND.",
        profile_count=len(windows),
        min_date=scfg.start_date,
        max_date=scfg.start_date + timedelta(days=scfg.core_days - 1),
        total_transactions=int(len(clean_df)),
        missing_rate=0.0,
        cleaning_summary=report.model_dump(),
        notes=[
            f"{scfg.n_core_users} core profiles with {scfg.core_days} continuous days each (>= 180 days requirement).",
            f"1 cold-start profile ({short_uid}) with {scfg.short_user_days} days (< 28 days insufficient-data test).",
            "Includes internal transfers (is_internal_transfer=True) and genuine zero-spend days.",
            "Injected anomalies are isolated in anomaly_eval_df for simulated benchmark evaluation only.",
        ],
    )
    return SyntheticBundle(
        transactions_df=clean_df,
        profile_windows=windows,
        anomaly_eval_df=anomaly_eval_df,
        manifest=manifest,
    )


def save_synthetic_bundle(bundle: SyntheticBundle, root_dir: Path = Path(".")) -> dict[str, Path]:
    proc_dir = root_dir / "data" / "processed" / "synthetic"
    demo_dir = root_dir / "data" / "demo"
    proc_dir.mkdir(parents=True, exist_ok=True)
    demo_dir.mkdir(parents=True, exist_ok=True)

    tx_path = proc_dir / "transactions.csv"
    win_path = proc_dir / "profile_windows.json"
    anom_path = proc_dir / "anomaly_eval.csv"
    man_path = proc_dir / "manifest.json"
    root_man_path = root_dir / "data" / "manifest.json"

    bundle.transactions_df.to_csv(tx_path, index=False)
    bundle.anomaly_eval_df.to_csv(anom_path, index=False)
    win_payload = {k: v.model_dump(mode="json") for k, v in bundle.profile_windows.items()}
    win_path.write_text(json.dumps(win_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    man_json = json.dumps(bundle.manifest.model_dump(mode="json"), indent=2, ensure_ascii=False)
    man_path.write_text(man_json, encoding="utf-8")
    root_man_path.write_text(man_json, encoding="utf-8")

    # Export demo CSVs for Khoa (backend seed) & Duy (valid + invalid CSV import test cases)
    valid_demo_path = demo_dir / "demo_transactions_valid.csv"
    bundle.transactions_df.head(200).to_csv(valid_demo_path, index=False)

    invalid_demo_path = demo_dir / "demo_transactions_invalid_samples.csv"
    pd.DataFrame(
        [
            {"transaction_id": "bad_01", "user_id": "user_001", "timestamp": "2026-03-01T08:00:00+07:00", "type": "expense", "amount_vnd": -50000, "category": "food", "is_internal_transfer": False, "note": "Lỗi số tiền âm"},
            {"transaction_id": "bad_02", "user_id": "user_001", "timestamp": "not-a-date", "type": "expense", "amount_vnd": 45000, "category": "food", "is_internal_transfer": False, "note": "Lỗi định dạng ngày"},
            {"transaction_id": "bad_03", "user_id": "user_001", "timestamp": "2026-03-02T09:00:00+07:00", "type": "refund_unknown", "amount_vnd": 30000, "category": "shopping", "is_internal_transfer": False, "note": "Lỗi loại giao dịch"},
            {"transaction_id": "syn_user_001_00001", "user_id": "user_001", "timestamp": "2026-01-02T10:00:00+07:00", "type": "expense", "amount_vnd": 1800000, "category": "housing", "is_internal_transfer": False, "note": "Bản ghi trùng transaction_id"},
        ]
    ).to_csv(invalid_demo_path, index=False)

    return {
        "transactions": tx_path,
        "windows": win_path,
        "anomaly_eval": anom_path,
        "manifest": man_path,
        "demo_valid": valid_demo_path,
        "demo_invalid": invalid_demo_path,
    }
