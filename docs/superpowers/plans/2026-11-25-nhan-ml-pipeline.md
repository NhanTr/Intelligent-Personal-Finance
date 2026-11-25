# Nhan Personal Finance ML Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Nhan's complete, leak-free personal finance data & ML package (`N1–N4`: dual-stream data pipeline, F3 7-day spending regression, F4 Isolation Forest anomaly detection, inference contract for FastAPI, retraining promotion gate, documentation/evidence, and a thin Google Colab notebook synced to `My Drive/PTHTTM_Nhan_ML_Colab/`).

**Architecture:** A single reproducible Python 3.12 package (`src/finance_ml/`) managed with `uv` shares identical cleaning, daily aggregation, and causal feature functions across offline training, evaluation, FastAPI inference, and a thin Google Colab wrapper notebook. All generated models, metrics, figures, locks, and review CSVs are isolated under `artifacts/<dataset>/` (`synthetic` vs `real_public`), with the `test` split strictly locked behind a one-shot audit guard (`2A`).

**Tech Stack:** Python 3.12, `uv`, `pandas`, `numpy`, `scikit-learn`, `joblib`, `pydantic`, `pyyaml`, `matplotlib`, `nbformat`, `pytest`, `gdrive` CLI.

**Spec:** `docs/superpowers/specs/2026-11-24-nhan-ml-pipeline-design.md`

## Global Constraints

- Python locked to `3.12` via `uv` (`pyproject.toml` + `uv.lock`) with exact `==` pins exported to `requirements-ml.txt` for FastAPI and Google Colab parity.
- Currency unit is strictly **VND** (`amount_vnd > 0`); rows with `is_internal_transfer == True` or `type == "income"` are excluded from expense totals and F4 expense anomaly scoring.
- Daily aggregation zero-fills `0.0` **only** for dates inside each user's confirmed `[tracking_start_date, tracking_end_date]` window; dates outside that window are never zero-filled.
- Evaluation profiles for F3 require `>= 180` continuous tracked days (target `>= 1,000` total transactions); inference requests for users with `< 28` available days return `status = "insufficient_data"`.
- Chronological split is `60% train / 20% validation / 20% test` using shared calendar cutoffs; F3 origins purge any 7-day label window crossing split boundaries and enforce `>= 7` days spacing per user.
- All scalers, encoders, user baseline stats, and models fit **only** on `train`; model/threshold selection happens **only** on `validation`; `test` remains locked during initial build (`2A`) and opens only via `--unlock-test --reason`.
- F3 compares `Last7DaysBaseline`, `LinearRegression`, and `RandomForestRegressor` (regression only) using **MAE** and **RMSE** in VND (never MAPE as primary metric), reports `meets_10pct_target`, and falls back to `Last7DaysBaseline` if neither ML model beats baseline on validation.
- F4 fits `IsolationForest` on `train`, selects threshold on `validation`, outputs human-readable Vietnamese context reasons without blocking/deleting transactions, exports top-30 + 30 random rows for Khoa & Duy's manual review, and keeps synthetic injected-anomaly Precision/Recall/F1 strictly separate.
- Single-user inference latency after model load must be `<= 3.0` seconds across `>= 20` recorded runs.
- Zero un-anonymized personal data committed to git; `synthetic` and `real_public` artifacts/reports never mix or overwrite each other.

## Review Focus

1. **Internal transfers & income rows leaking into spending totals:** Transactions with `is_internal_transfer=True` (or Kaggle `"Transfer-Out"`) or `type="income"` must contribute `0` to `total_expense_vnd`, `tx_count`, and F4 anomaly candidates (pinned in Task 2 & Task 3 tests).
2. **Pre-registration / trailing silent days miscounted at inference:** `predict_next_7d` with `tracking_start_date=None` must zero-fill silent days between `min(tx_date <= as_of_date)` and `as_of_date` while never zero-filling dates before `min(tx_date <= as_of_date)`, and must return `insufficient_data` when `days_available < 28` or when all transactions occur after `as_of_date` (pinned in Task 2 & Task 7 tests).
3. **7-day target window bleeding across `train`/`validation`/`test` cutoffs:** Forecast origins within 6 days of `train_end` or `val_end` (whose `[t+1, t+7]` target touches the next split) or spaced `< 7` days apart must be dropped (pinned in Task 4 tests).
4. **Unseen / messy category values or zero-spend days causing `NaN` or encoder crash:** Unknown categories (`"CRYPTO"`, `""`, `None`) must normalize to `"other"` / encode cleanly via `handle_unknown="ignore"`, and days with `total_expense_vnd == 0` must yield `0.0` category shares rather than `NaN` (pinned in Task 1, Task 2 & Task 5 tests).
5. **Lookahead or zero-variance division in F4 user anomaly stats:** Computing F4 features at timestamp `t` must remain bit-for-bit unchanged when transactions at `t' > t` are modified, and users with `< 5` prior transactions or constant prior spend (`std == 0`) must fall back cleanly to global `train` statistics with finite values (pinned in Task 5 tests).

---

### Task 1: Project Scaffolding, Locked Dependencies, Config & Canonical Schemas

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `requirements-ml.txt`
- Create: `configs/default.yaml`
- Create: `src/finance_ml/__init__.py`
- Create: `src/finance_ml/config.py`
- Create: `src/finance_ml/schema.py`
- Test: `tests/test_schema_and_config.py`

**Interfaces:**
- Consumes: None
- Produces:
  - `CANONICAL_CATEGORIES: tuple[str, ...]`
  - `ESSENTIAL_CATEGORIES: frozenset[str]`
  - `normalize_category(raw: str | None) -> str`
  - `PipelineConfig` & `load_config(path: Path = Path("configs/default.yaml")) -> PipelineConfig`
  - Pydantic models in `finance_ml.schema`: `TransactionRecord`, `ProfileWindow`, `ForecastResult`, `AnomalyItem`, `AnomalyBatchResult`, `FeedbackRecord`, `DataManifest`

- [ ] **Step 1: Initialize git & Python 3.12 `uv` environment with `pyproject.toml`, `.gitignore`, `requirements-ml.txt`, and `configs/default.yaml`**

Run `git init` (if `.git` absent), pin Python `>=3.12,<3.13`, and configure exact dependencies (`numpy`, `pandas`, `scikit-learn`, `joblib`, `pydantic`, `pyyaml`, `matplotlib`, `nbformat`, plus dev `pytest`) in `pyproject.toml`, syncing `uv.lock` and exporting exact `==` runtime pins to `requirements-ml.txt`. Ignore `.venv/`, `__pycache__/`, `.pytest_cache/`, `data/raw/*` (except `.gitkeep`), and `private*` in `.gitignore`.

- [ ] **Step 2: Write the failing schema & config tests in `tests/test_schema_and_config.py`**

```python
from datetime import date, datetime
from pathlib import Path
import pytest
from pydantic import ValidationError
from finance_ml.config import load_config
from finance_ml.schema import TransactionRecord, ForecastResult, normalize_category


def test_load_default_config():
    cfg = load_config(Path("configs/default.yaml"))
    assert cfg.seed == 42
    assert cfg.split_ratios == (0.6, 0.2, 0.2)
    assert cfg.forecast.horizon_days == 7
    assert cfg.forecast.min_history_days == 28


def test_normalize_category_handles_unknown_and_aliases():
    assert normalize_category("Food & Dining") == "food"
    assert normalize_category("CRYPTO_MEME") == "other"
    assert normalize_category("") == "other"
    assert normalize_category(None) == "other"


def test_transaction_record_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        TransactionRecord(
            transaction_id="tx_1",
            user_id="user_001",
            timestamp=datetime.fromisoformat("2026-03-01T10:00:00+07:00"),
            type="expense",
            amount_vnd=0.0,
            category="food",
        )


def test_forecast_result_insufficient_data_contract():
    res = ForecastResult(
        status="insufficient_data",
        user_id="user_short_001",
        as_of_date=date(2026, 2, 10),
        horizon_days=7,
        forecast_start_date=date(2026, 2, 11),
        forecast_end_date=date(2026, 2, 17),
        predicted_total_vnd=None,
        unit="VND",
        model_name="none",
        model_version="v1.0.0",
        days_available=14,
        min_days_required=28,
        limitations_note="Cần tối thiểu 28 ngày lịch sử để dự báo chi tiêu 7 ngày tới.",
    )
    assert res.unit == "VND"
    assert res.predicted_total_vnd is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_schema_and_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'finance_ml'`

- [ ] **Step 4: Implement `src/finance_ml/config.py` and `src/finance_ml/schema.py`**

Define `CANONICAL_CATEGORIES = ("food", "transport", "housing", "utilities", "shopping", "entertainment", "health", "education", "salary", "bonus", "transfer", "other")`, `ESSENTIAL_CATEGORIES = frozenset({"food", "transport", "housing", "utilities", "health", "education"})`, case-insensitive alias mapping in `normalize_category` (mapping common English/Vietnamese/Kaggle labels to canonical categories, defaulting unknown/empty/`None` to `"other"`), `PipelineConfig` (seed, split_ratios, synthetic params, RF tuning grid, IF n_estimators & validation_alert_quantile `0.95`, currency conversion `inr_to_vnd_rate: 300.0`), and all Pydantic contract models enforcing `amount_vnd > 0` and Vietnam timezone normalization (`UTC+07:00`).

- [ ] **Step 5: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_schema_and_config.py -v`
Expected: PASS

```bash
git add .gitignore pyproject.toml uv.lock requirements-ml.txt configs/default.yaml src/finance_ml/__init__.py src/finance_ml/config.py src/finance_ml/schema.py tests/test_schema_and_config.py
git commit -m "feat: initialize Python 3.12 project, config, and canonical ML schemas"
```

---

### Task 2: Transaction Cleaning, Deduplication & Strict Windowed Daily Aggregation

**Files:**
- Create: `src/finance_ml/data/__init__.py`
- Create: `src/finance_ml/data/cleaning.py`
- Create: `src/finance_ml/data/daily.py`
- Test: `tests/test_cleaning_and_daily.py`

**Interfaces:**
- Consumes: `TransactionRecord`, `ProfileWindow`, `CANONICAL_CATEGORIES`, `ESSENTIAL_CATEGORIES`, `normalize_category` from `finance_ml.schema`
- Produces:
  - `CleaningReport` (Pydantic model: `input_rows: int`, `valid_rows: int`, `dropped_invalid_rows: int`, `deduplicated_rows: int`, `internal_transfer_rows: int`, `error_breakdown: dict[str, int]`)
  - `clean_transactions(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]`
  - `aggregate_daily_spending(clean_df: pd.DataFrame, profile_windows: dict[str, ProfileWindow]) -> pd.DataFrame`

- [ ] **Step 1: Write the failing cleaning & daily aggregation tests in `tests/test_cleaning_and_daily.py`**

```python
from datetime import date
import pandas as pd
from finance_ml.data.cleaning import clean_transactions
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.schema import ProfileWindow


def test_clean_transactions_deduplicates_and_rejects_bad_rows():
    raw = pd.DataFrame([
        {"transaction_id": "t1", "user_id": "u1", "timestamp": "2026-01-02T08:00:00+07:00", "type": "expense", "amount_vnd": 50000, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t1", "user_id": "u1", "timestamp": "2026-01-02T08:00:00+07:00", "type": "expense", "amount_vnd": 50000, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t2", "user_id": "u1", "timestamp": "2026-01-02T09:00:00+07:00", "type": "expense", "amount_vnd": -100, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t3", "user_id": "u1", "timestamp": "2026-01-03T12:00:00+07:00", "type": "expense", "amount_vnd": 200000, "category": "transfer", "is_internal_transfer": True},
    ])
    clean_df, report = clean_transactions(raw)
    assert report.input_rows == 4
    assert report.deduplicated_rows == 1
    assert report.dropped_invalid_rows == 1
    assert report.internal_transfer_rows == 1
    assert len(clean_df) == 2


def test_daily_aggregation_zero_fills_only_inside_window_and_excludes_transfers_and_income():
    raw = pd.DataFrame([
        {"transaction_id": "t0", "user_id": "u1", "timestamp": "2025-12-31T10:00:00+07:00", "type": "expense", "amount_vnd": 99999, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t1", "user_id": "u1", "timestamp": "2026-01-01T10:00:00+07:00", "type": "expense", "amount_vnd": 100000, "category": "food", "is_internal_transfer": False},
        {"transaction_id": "t2", "user_id": "u1", "timestamp": "2026-01-01T12:00:00+07:00", "type": "expense", "amount_vnd": 500000, "category": "transfer", "is_internal_transfer": True},
        {"transaction_id": "t3", "user_id": "u1", "timestamp": "2026-01-01T15:00:00+07:00", "type": "income", "amount_vnd": 10000000, "category": "salary", "is_internal_transfer": False},
    ])
    clean_df, _ = clean_transactions(raw)
    windows = {"u1": ProfileWindow(user_id="u1", tracking_start_date=date(2026, 1, 1), tracking_end_date=date(2026, 1, 3))}
    daily = aggregate_daily_spending(clean_df, windows)

    assert list(daily["date"]) == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    assert list(daily["total_expense_vnd"]) == [100000.0, 0.0, 0.0]
    assert list(daily["tx_count"]) == [1, 0, 0]
    assert not daily.isna().any().any()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cleaning_and_daily.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/finance_ml/data/cleaning.py` and `src/finance_ml/data/daily.py`**

In `clean_transactions`, validate required columns, drop rows with missing/unparseable timestamps, invalid `type` not in `{"income", "expense"}`, non-positive/NaN `amount_vnd`, or missing IDs (counting each reason in `error_breakdown`), normalize categories via `normalize_category`, force `is_internal_transfer = True` whenever `category == "transfer"` or `is_internal_transfer` is truthy, deduplicate by `transaction_id` (`keep="first"`), and sort by `(user_id, timestamp, transaction_id)`. In `aggregate_daily_spending`, generate exact daily grids `[tracking_start_date, tracking_end_date]` per user in `profile_windows`, filter qualifying expenses (`type == "expense"` and `not is_internal_transfer` and date inside window), compute `total_expense_vnd`, `tx_count`, `essential_expense_vnd`, and per-category ratios (`0.0` on zero-spend days).

- [ ] **Step 4: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_cleaning_and_daily.py -v`
Expected: PASS

```bash
git add src/finance_ml/data/__init__.py src/finance_ml/data/cleaning.py src/finance_ml/data/daily.py tests/test_cleaning_and_daily.py
git commit -m "feat: add transaction cleaning, deduplication, and strict windowed daily aggregation"
```

---

### Task 3: Synthetic Multi-User VND Generator & Public Kaggle Adapter (`N1`)

**Files:**
- Create: `src/finance_ml/data/synthetic.py`
- Create: `src/finance_ml/data/public_adapter.py`
- Create: `scripts/generate_data.py`
- Create: `scripts/prepare_public_data.py`
- Create: `data/raw/.gitkeep`
- Test: `tests/test_data_streams.py`

**Interfaces:**
- Consumes: `PipelineConfig`, `ProfileWindow`, `DataManifest`, `clean_transactions`
- Produces:
  - `SyntheticBundle` (dataclass: `transactions_df: pd.DataFrame`, `profile_windows: dict[str, ProfileWindow]`, `anomaly_eval_df: pd.DataFrame`, `manifest: DataManifest`)
  - `generate_synthetic_dataset(config: PipelineConfig) -> SyntheticBundle`
  - `adapt_kaggle_daily_transactions(csv_path: Path, inr_to_vnd_rate: float = 300.0) -> tuple[pd.DataFrame, dict[str, ProfileWindow], DataManifest]`

- [ ] **Step 1: Write the failing tests for both data streams in `tests/test_data_streams.py`**

```python
from pathlib import Path
import pandas as pd
from finance_ml.config import load_config
from finance_ml.data.synthetic import generate_synthetic_dataset
from finance_ml.data.public_adapter import adapt_kaggle_daily_transactions
from finance_ml.data.daily import aggregate_daily_spending


def test_synthetic_generator_is_deterministic_and_meets_spec_bounds():
    cfg = load_config(Path("configs/default.yaml"))
    b1 = generate_synthetic_dataset(cfg)
    b2 = generate_synthetic_dataset(cfg)
    pd.testing.assert_frame_equal(b1.transactions_df, b2.transactions_df)

    core_users = [u for u in b1.profile_windows if not u.startswith("user_short")]
    assert len(core_users) == 8
    assert "user_short_001" in b1.profile_windows
    short_w = b1.profile_windows["user_short_001"]
    assert (short_w.tracking_end_date - short_w.tracking_start_date).days + 1 == 14

    assert len(b1.transactions_df) >= 2000
    assert b1.transactions_df["is_internal_transfer"].any()
    daily = aggregate_daily_spending(
        b1.transactions_df[b1.transactions_df["user_id"].isin(core_users)],
        {u: b1.profile_windows[u] for u in core_users},
    )
    for u, grp in daily.groupby("user_id"):
        assert len(grp) >= 180
        assert (grp["total_expense_vnd"] == 0).any()

    assert "is_injected_anomaly" in b1.anomaly_eval_df.columns
    assert b1.anomaly_eval_df["is_injected_anomaly"].sum() >= 15


def test_kaggle_public_adapter_maps_transfers_and_currency(tmp_path: Path):
    sample_csv = tmp_path / "daily_household_transactions.csv"
    pd.DataFrame([
        {"Date": "20/09/2018 12:00:00", "Mode": "Cash", "Category": "Food", "Subcategory": "Lunch", "Note": "Rice", "Amount": 120.0, "Income/Expense": "Expense", "Currency": "INR"},
        {"Date": "21/09/2018 09:00:00", "Mode": "Bank", "Category": "Savings", "Subcategory": "", "Note": "Move", "Amount": 5000.0, "Income/Expense": "Transfer-Out", "Currency": "INR"},
        {"Date": "25/09/2018 09:00:00", "Mode": "Bank", "Category": "Salary", "Subcategory": "", "Note": "Pay", "Amount": 30000.0, "Income/Expense": "Income", "Currency": "INR"},
    ]).to_csv(sample_csv, index=False)

    clean_df, windows, manifest = adapt_kaggle_daily_transactions(sample_csv, inr_to_vnd_rate=300.0)
    assert manifest.source_type == "real_public"
    assert set(clean_df["user_id"]) == {"public_hh_001"}
    transfer_row = clean_df[clean_df["amount_vnd"] == 1500000.0].iloc[0]
    assert bool(transfer_row["is_internal_transfer"]) is True
    assert transfer_row["type"] == "expense"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data_streams.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `synthetic.py`, `public_adapter.py`, `scripts/generate_data.py`, and `scripts/prepare_public_data.py`**

Implement `generate_synthetic_dataset` using `np.random.default_rng(config.seed)` with 8 realistic archetypes (`300` days `2026-01-01`..`2026-10-27` having strong weekly/monthly/habit autocorrelation so lag/rolling features genuinely carry predictive signal over naive 7-day persistence, 15–30% zero-spend days, ~5% internal transfers), `user_short_001` (`14` days), and a separate `anomaly_eval_df` (`~3%` injected spikes/category outliers/24h bursts). Have `scripts/generate_data.py` write `data/processed/synthetic/`, `data/demo/demo_transactions_valid.csv`, `data/demo/demo_transactions_invalid_samples.csv`, and `data/manifest.json`. Have `scripts/prepare_public_data.py` check `data/raw/daily_household_transactions.csv` (exiting `0` with an informative message if absent, or writing `data/processed/real_public/` if present).

- [ ] **Step 4: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_data_streams.py -v`
Expected: PASS

```bash
git add data/raw/.gitkeep src/finance_ml/data/synthetic.py src/finance_ml/data/public_adapter.py scripts/generate_data.py scripts/prepare_public_data.py tests/test_data_streams.py
git commit -m "feat: add synthetic VND multi-user generator and public Kaggle adapter"
```

---

### Task 4: Chronological Split, Anti-Leakage Origin Purging, Rolling CV & 1-Shot Test Guard

**Files:**
- Create: `src/finance_ml/evaluation/__init__.py`
- Create: `src/finance_ml/evaluation/split.py`
- Create: `src/finance_ml/evaluation/metrics.py`
- Create: `src/finance_ml/evaluation/rolling_cv.py`
- Create: `src/finance_ml/evaluation/test_guard.py`
- Test: `tests/test_split_and_leakage.py`

**Interfaces:**
- Consumes: `PipelineConfig`
- Produces:
  - `TimeSplitCutoffs` (`train_start: date`, `train_end: date`, `val_start: date`, `val_end: date`, `test_start: date`, `test_end: date`)
  - `compute_time_cutoffs(daily_df: pd.DataFrame, ratios: tuple[float, float, float] = (0.6, 0.2, 0.2)) -> TimeSplitCutoffs`
  - `assign_forecast_origins(origins_df: pd.DataFrame, cutoffs: TimeSplitCutoffs, horizon_days: int = 7, min_step_days: int = 7) -> pd.DataFrame`
  - `assign_transaction_splits(tx_df: pd.DataFrame, cutoffs: TimeSplitCutoffs) -> pd.DataFrame`
  - `generate_expanding_cv_splits(daily_df: pd.DataFrame, cutoffs: TimeSplitCutoffs, n_splits: int = 3) -> list[TimeSplitCutoffs]`
  - `compute_forecast_metrics(y_true: np.ndarray, y_pred: np.ndarray, user_ids: pd.Series, baseline_mae: float | None = None) -> dict[str, Any]`
  - `compute_anomaly_injection_metrics(y_true: np.ndarray, is_flagged: np.ndarray) -> dict[str, Any]`
  - `TestLockGuard(lock_path: Path)` with `.verify_and_record(unlock: bool, reason: str | None, config_hash: str) -> dict[str, Any]`

- [ ] **Step 1: Write the failing anti-leakage, rolling CV, metrics & test-guard tests in `tests/test_split_and_leakage.py`**

```python
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from finance_ml.evaluation.split import compute_time_cutoffs, assign_forecast_origins
from finance_ml.evaluation.rolling_cv import generate_expanding_cv_splits
from finance_ml.evaluation.metrics import compute_forecast_metrics
from finance_ml.evaluation.test_guard import TestLockGuard


def test_forecast_origins_purge_boundary_overlap_and_enforce_7d_spacing():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(300)]
    daily = pd.DataFrame({"user_id": ["u1"] * 300, "date": dates, "total_expense_vnd": 100000.0})
    cutoffs = compute_time_cutoffs(daily, (0.6, 0.2, 0.2))

    origins = pd.DataFrame({"user_id": ["u1"] * 260, "origin_date": dates[28:288]})
    assigned = assign_forecast_origins(origins, cutoffs, horizon_days=7, min_step_days=7)

    train_rows = assigned[assigned["split"] == "train"]
    val_rows = assigned[assigned["split"] == "validation"]
    test_rows = assigned[assigned["split"] == "test"]

    assert (train_rows["origin_date"] + timedelta(days=7) <= cutoffs.train_end).all()
    assert (val_rows["origin_date"] >= cutoffs.val_start).all()
    assert (val_rows["origin_date"] + timedelta(days=7) <= cutoffs.val_end).all()
    assert (test_rows["origin_date"] >= cutoffs.test_start).all()
    for _, grp in assigned.groupby(["user_id", "split"]):
        diffs = grp["origin_date"].sort_values().diff().dropna().apply(lambda d: d.days)
        assert (diffs >= 7).all()


def test_expanding_cv_never_touches_test_period():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(300)]
    daily = pd.DataFrame({"user_id": ["u1"] * 300, "date": dates, "total_expense_vnd": 100000.0})
    cutoffs = compute_time_cutoffs(daily, (0.6, 0.2, 0.2))
    folds = generate_expanding_cv_splits(daily, cutoffs, n_splits=3)
    assert len(folds) == 3
    assert all(f.val_end <= cutoffs.val_end for f in folds)


def test_forecast_metrics_computes_mae_rmse_and_10pct_target_without_mape():
    y_true = np.array([0.0, 1000000.0, 500000.0])
    y_pred = np.array([100000.0, 900000.0, 500000.0])
    users = pd.Series(["u1", "u1", "u2"])
    m = compute_forecast_metrics(y_true, y_pred, users, baseline_mae=100000.0)
    assert "mape" not in m
    assert m["meets_10pct_target"] is True
    assert set(m["per_user"].keys()) == {"u1", "u2"}


def test_one_shot_test_lock_guard(tmp_path: Path):
    guard = TestLockGuard(tmp_path / "test_evaluation_lock.json")
    with pytest.raises(PermissionError):
        guard.verify_and_record(unlock=False, reason=None, config_hash="abc")

    rec1 = guard.verify_and_record(unlock=True, reason="Initial Day-14 test run", config_hash="abc")
    assert rec1["unlock_count"] == 1

    with pytest.raises(PermissionError):
        guard.verify_and_record(unlock=True, reason="", config_hash="abc")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_split_and_leakage.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `split.py`, `metrics.py`, `rolling_cv.py`, and `test_guard.py`**

Implement `compute_time_cutoffs` over sorted unique calendar dates (`60/20/20`), `assign_forecast_origins` (purging any sample whose `[origin_date + 1d, origin_date + horizon_days]` crosses `train_end`, `val_end`, or `test_end`, then greedily selecting origins spaced `>= min_step_days` within each `(user_id, split)`), `generate_expanding_cv_splits` confined strictly to `date <= cutoffs.val_end`, `compute_forecast_metrics` / `compute_anomaly_injection_metrics`, and `TestLockGuard` requiring `--unlock-test` + explicit non-empty `reason` (requiring a `bugfix:`-prefixed or explicit re-run reason if `unlock_count >= 1`).

- [ ] **Step 4: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_split_and_leakage.py -v`
Expected: PASS

```bash
git add src/finance_ml/evaluation/__init__.py src/finance_ml/evaluation/split.py src/finance_ml/evaluation/metrics.py src/finance_ml/evaluation/rolling_cv.py src/finance_ml/evaluation/test_guard.py tests/test_split_and_leakage.py
git commit -m "feat: add time-series split, boundary purge, rolling CV, and 1-shot test lock"
```

---

### Task 5: Shared Causal Feature Builders for F3 & F4

**Files:**
- Create: `src/finance_ml/features/__init__.py`
- Create: `src/finance_ml/features/forecast_features.py`
- Create: `src/finance_ml/features/anomaly_features.py`
- Test: `tests/test_causal_features.py`

**Interfaces:**
- Consumes: `ProfileWindow`, `CANONICAL_CATEGORIES` from `finance_ml.schema`
- Produces:
  - `FORECAST_FEATURE_COLUMNS: tuple[str, ...]`
  - `build_forecast_dataset(daily_df: pd.DataFrame, profile_windows: dict[str, ProfileWindow], horizon_days: int = 7, min_history_days: int = 28) -> pd.DataFrame`
  - `build_single_forecast_features(daily_df: pd.DataFrame, user_id: str, as_of_date: date, min_history_days: int = 28) -> pd.DataFrame`
  - `AnomalyFeatureFitState`
  - `fit_anomaly_feature_state(train_expense_df: pd.DataFrame) -> AnomalyFeatureFitState`
  - `transform_anomaly_features(expense_df: pd.DataFrame, state: AnomalyFeatureFitState, history_expense_df: pd.DataFrame | None = None) -> tuple[np.ndarray, pd.DataFrame]`

- [ ] **Step 1: Write the failing causal invariance & edge-case tests in `tests/test_causal_features.py`**

```python
from datetime import date, timedelta
import numpy as np
import pandas as pd
from finance_ml.schema import ProfileWindow
from finance_ml.features.forecast_features import build_forecast_dataset, build_single_forecast_features, FORECAST_FEATURE_COLUMNS
from finance_ml.features.anomaly_features import fit_anomaly_feature_state, transform_anomaly_features


def test_forecast_features_are_strictly_causal_and_match_single_inference():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(60)]
    daily_a = pd.DataFrame({
        "user_id": ["u1"] * 60,
        "date": dates,
        "total_expense_vnd": [100000.0 + (i % 7) * 10000.0 for i in range(60)],
        "tx_count": [2] * 60,
        "essential_expense_vnd": [70000.0] * 60,
    })
    daily_b = daily_a.copy()
    daily_b.loc[daily_b["date"] > date(2026, 2, 5), "total_expense_vnd"] = 99999999.0

    windows = {"u1": ProfileWindow(user_id="u1", tracking_start_date=dates[0], tracking_end_date=dates[-1])}
    ds_a = build_forecast_dataset(daily_a, windows, horizon_days=7, min_history_days=28)
    row_a = ds_a[ds_a["origin_date"] == date(2026, 2, 5)][list(FORECAST_FEATURE_COLUMNS)].reset_index(drop=True)
    single_b = build_single_forecast_features(daily_b, "u1", date(2026, 2, 5), min_history_days=28)[list(FORECAST_FEATURE_COLUMNS)].reset_index(drop=True)

    pd.testing.assert_frame_equal(row_a, single_b)


def test_anomaly_features_causal_invariance_and_cold_user_unknown_category():
    train_tx = pd.DataFrame([
        {"transaction_id": f"t{i}", "user_id": "u1", "timestamp": pd.Timestamp("2026-01-01T10:00:00+07:00") + pd.Timedelta(days=i), "type": "expense", "amount_vnd": 100000.0, "category": "food", "is_internal_transfer": False}
        for i in range(10)
    ])
    state = fit_anomaly_feature_state(train_tx)

    eval_a = pd.DataFrame([
        {"transaction_id": "e1", "user_id": "new_user", "timestamp": pd.Timestamp("2026-02-01T10:00:00+07:00"), "type": "expense", "amount_vnd": 500000.0, "category": "unseen_cat", "is_internal_transfer": False},
        {"transaction_id": "e2", "user_id": "new_user", "timestamp": pd.Timestamp("2026-02-02T10:00:00+07:00"), "type": "expense", "amount_vnd": 50000000.0, "category": "food", "is_internal_transfer": False},
    ])
    eval_b = eval_a.copy()
    eval_b.loc[1, "amount_vnd"] = 1.0

    X_a, ctx_a = transform_anomaly_features(eval_a, state)
    X_b, ctx_b = transform_anomaly_features(eval_b, state)

    assert np.isfinite(X_a).all()
    np.testing.assert_allclose(X_a[0], X_b[0])
    assert ctx_a.iloc[0]["user_amount_ratio"] == ctx_b.iloc[0]["user_amount_ratio"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_causal_features.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `forecast_features.py` and `anomaly_features.py`**

Implement one shared causal helper computing `FORECAST_FEATURE_COLUMNS = ("spend_last_7d", "spend_last_14d", "spend_last_28d", "daily_mean_7d", "daily_std_7d", "daily_mean_28d", "daily_std_28d", "tx_count_7d", "tx_count_28d", "zero_spend_days_28d", "essential_share_28d", "origin_day_of_week", "origin_day_of_month", "days_to_month_end", "spans_month_start", "spans_month_end")` from `date <= origin_date` only, invoked by both `build_forecast_dataset` and `build_single_forecast_features`. In `anomaly_features.py`, fit `OneHotEncoder(categories=[list(CANONICAL_CATEGORIES)], handle_unknown="ignore", sparse_output=False)` and global `train` median/log-mean/log-std in `fit_anomaly_feature_state`; in `transform_anomaly_features`, compute per-transaction features (`log_amount`, `user_amount_ratio`, `user_amount_zscore`, `user_cat_amount_ratio`, `tx_freq_24h`, `tx_freq_7d`, `hour_of_day`, `is_weekend` + one-hot category) strictly from prior transactions (`timestamp < current_tx.timestamp`), falling back to `state` globals when prior count `< 5` and clamping std floor to `0.1`.

- [ ] **Step 4: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_causal_features.py -v`
Expected: PASS

```bash
git add src/finance_ml/features/__init__.py src/finance_ml/features/forecast_features.py src/finance_ml/features/anomaly_features.py tests/test_causal_features.py
git commit -m "feat: add shared causal feature builders for 7-day forecast and anomaly detection"
```

---

### Task 6: F3 Regressors, F4 Isolation Forest, Bundle Registry & Train/Eval CLIs

**Files:**
- Create: `src/finance_ml/models/__init__.py`
- Create: `src/finance_ml/models/forecast.py`
- Create: `src/finance_ml/models/anomaly.py`
- Create: `src/finance_ml/models/registry.py`
- Create: `scripts/train.py`
- Create: `scripts/evaluate.py`
- Test: `tests/test_models_and_registry.py`

**Interfaces:**
- Consumes: Tasks 1–5 interfaces
- Produces:
  - `Last7DaysBaseline` (sklearn-compatible estimator `.fit(X, y)` / `.predict(X)`)
  - `ForecastSelectionOutput` (`selected_name: str`, `selected_estimator: Any`, `all_models: dict[str, Any]`, `val_comparison: dict[str, dict[str, Any]]`, `fallback_used: bool`)
  - `train_and_select_forecast_models(train_df: pd.DataFrame, val_df: pd.DataFrame, config: PipelineConfig) -> ForecastSelectionOutput`
  - `TrainedAnomalyDetector` (`feature_state: AnomalyFeatureFitState`, `isolation_forest: IsolationForest`, `threshold: float`, `validation_alert_rate: float`)
  - `train_anomaly_detector(train_expense_df: pd.DataFrame, val_expense_df: pd.DataFrame, config: PipelineConfig, confirmed_anomaly_ids: set[str] | None = None, val_feedback_df: pd.DataFrame | None = None) -> TrainedAnomalyDetector`
  - `score_expense_anomalies(expense_df: pd.DataFrame, detector: TrainedAnomalyDetector, history_expense_df: pd.DataFrame | None = None) -> pd.DataFrame`
  - `save_model_bundle(dataset_dir: Path, version: str, forecast_out: ForecastSelectionOutput, anomaly_det: TrainedAnomalyDetector, metadata: dict[str, Any]) -> Path`
  - `set_active_pointer(pointer_path: Path, bundle_dir: Path, version: str, dataset_name: str) -> None`

- [ ] **Step 1: Write the failing model selection, fallback, Isolation Forest & registry tests in `tests/test_models_and_registry.py`**

```python
from pathlib import Path
import numpy as np
import pandas as pd
from finance_ml.config import load_config
from finance_ml.data.synthetic import generate_synthetic_dataset
from finance_ml.data.daily import aggregate_daily_spending
from finance_ml.evaluation.split import compute_time_cutoffs, assign_forecast_origins, assign_transaction_splits
from finance_ml.features.forecast_features import build_forecast_dataset, FORECAST_FEATURE_COLUMNS
from finance_ml.models.forecast import train_and_select_forecast_models
from finance_ml.models.anomaly import train_anomaly_detector, score_expense_anomalies
from finance_ml.models.registry import save_model_bundle, set_active_pointer


def test_forecast_training_fallback_when_noise_beats_ml():
    cfg = load_config(Path("configs/default.yaml"))
    rng = np.random.default_rng(0)
    cols = list(FORECAST_FEATURE_COLUMNS)
    train_df = pd.DataFrame(rng.normal(100, 10, size=(40, len(cols))), columns=cols)
    train_df["user_id"] = "u1"
    train_df["target_next_7d_vnd"] = rng.uniform(1e6, 5e6, size=40)

    val_df = pd.DataFrame(rng.normal(100, 10, size=(15, len(cols))), columns=cols)
    val_df["user_id"] = "u1"
    val_df["spend_last_7d"] = 2000000.0
    val_df["target_next_7d_vnd"] = 2000000.0

    out = train_and_select_forecast_models(train_df, val_df, cfg)
    assert out.selected_name == "baseline_last_7d"
    assert out.fallback_used is True


def test_end_to_end_synthetic_train_and_bundle_save(tmp_path: Path):
    cfg = load_config(Path("configs/default.yaml"))
    syn = generate_synthetic_dataset(cfg)
    core_windows = {k: v for k, v in syn.profile_windows.items() if not k.startswith("user_short")}
    core_tx = syn.transactions_df[syn.transactions_df["user_id"].isin(core_windows)]
    daily = aggregate_daily_spending(core_tx, core_windows)
    cutoffs = compute_time_cutoffs(daily, cfg.split_ratios)

    f_ds = assign_forecast_origins(build_forecast_dataset(daily, core_windows), cutoffs)
    f_out = train_and_select_forecast_models(
        f_ds[f_ds["split"] == "train"], f_ds[f_ds["split"] == "validation"], cfg
    )
    assert set(f_out.val_comparison.keys()) == {"baseline_last_7d", "linear_regression", "random_forest"}

    exp_tx = core_tx[(core_tx["type"] == "expense") & (~core_tx["is_internal_transfer"])]
    exp_split = assign_transaction_splits(exp_tx, cutoffs)
    det = train_anomaly_detector(
        exp_split[exp_split["split"] == "train"], exp_split[exp_split["split"] == "validation"], cfg
    )
    scored = score_expense_anomalies(exp_split[exp_split["split"] == "validation"], det, exp_split[exp_split["split"] == "train"])
    assert 0.01 <= scored["is_anomaly"].mean() <= 0.10
    flagged = scored[scored["is_anomaly"]]
    assert all(len(r) >= 1 for r in flagged["reasons"])

    bdir = save_model_bundle(tmp_path / "synthetic", "v1.0.0", f_out, det, {"seed": cfg.seed})
    set_active_pointer(tmp_path / "models" / "active.json", bdir, "v1.0.0", "synthetic")
    assert (bdir / "bundle.joblib").exists()
    assert (bdir / "metadata.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models_and_registry.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `forecast.py`, `anomaly.py`, `registry.py`, `scripts/train.py`, and `scripts/evaluate.py`**

Implement `Last7DaysBaseline`, `LinearRegression` pipeline (`SimpleImputer` + `StandardScaler` + `LinearRegression`), and `RandomForestRegressor` grid search evaluated strictly on `val_df` (predictions clipped `>= 0.0`), automatically picking lowest validation MAE and setting `fallback_used=True` when `selected_name == "baseline_last_7d"`. Implement `train_anomaly_detector` (`IsolationForest(n_estimators=200, random_state=config.seed, contamination="auto")`, `anomaly_score = -decision_function(X)`, threshold at `np.quantile(val_scores, config.anomaly.validation_quantile)` or feedback-guarded quantile, plus plain Vietnamese `reasons` generation). Wire `scripts/train.py --dataset synthetic|real_public` and `scripts/evaluate.py --dataset synthetic|real_public [--unlock-test --reason ...]` writing namespaced outputs under `artifacts/<dataset>/` and keeping `test` locked unless `--unlock-test` is passed.

- [ ] **Step 4: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_models_and_registry.py -v`
Expected: PASS

```bash
git add src/finance_ml/models/__init__.py src/finance_ml/models/forecast.py src/finance_ml/models/anomaly.py src/finance_ml/models/registry.py scripts/train.py scripts/evaluate.py tests/test_models_and_registry.py
git commit -m "feat: add F3 forecast regressors, F4 Isolation Forest, registry, and train/evaluate CLIs"
```

---

### Task 7: Inference API, Missing-Model Fallback, Retraining Gate & Latency Benchmark (`N3`)

**Files:**
- Create: `src/finance_ml/inference/__init__.py`
- Create: `src/finance_ml/inference/loader.py`
- Create: `src/finance_ml/inference/predictor.py`
- Create: `src/finance_ml/inference/benchmark.py`
- Create: `scripts/retrain.py`
- Test: `tests/test_inference_and_retrain.py`

**Interfaces:**
- Consumes: Tasks 1–6 interfaces
- Produces:
  - `LoadedBundle` & `ModelBundleLoader(pointer_or_dir: Path, allow_baseline_fallback: bool = True)` with `.load() -> LoadedBundle`
  - `predict_next_7d(transactions_df: pd.DataFrame, user_id: str, as_of_date: date, bundle: LoadedBundle, tracking_start_date: date | None = None) -> ForecastResult`
  - `detect_anomalies(transactions_df: pd.DataFrame, user_id: str, bundle: LoadedBundle, target_transaction_ids: list[str] | None = None) -> AnomalyBatchResult`
  - `run_latency_benchmark(bundle: LoadedBundle, transactions_df: pd.DataFrame, user_id: str, as_of_date: date, n_runs: int = 25) -> dict[str, Any]`
  - `retrain_and_maybe_promote(transactions_df: pd.DataFrame, profile_windows: dict[str, ProfileWindow], feedback_df: pd.DataFrame | None, dataset_dir: Path, global_active_pointer: Path | None, config: PipelineConfig, new_version: str, force_promote: bool = False) -> dict[str, Any]`

- [ ] **Step 1: Write the failing inference, cold-start, corrupt-bundle fallback, latency & retraining tests in `tests/test_inference_and_retrain.py`**

```python
from datetime import date
from pathlib import Path
import pandas as pd
from finance_ml.config import load_config
from finance_ml.data.synthetic import generate_synthetic_dataset
from finance_ml.inference.loader import ModelBundleLoader
from finance_ml.inference.predictor import predict_next_7d, detect_anomalies
from finance_ml.inference.benchmark import run_latency_benchmark
from scripts.retrain import retrain_and_maybe_promote


def test_missing_model_falls_back_to_baseline_and_short_history_returns_insufficient(tmp_path: Path):
    cfg = load_config(Path("configs/default.yaml"))
    syn = generate_synthetic_dataset(cfg)
    fallback_bundle = ModelBundleLoader(tmp_path / "missing_active.json", allow_baseline_fallback=True).load()
    assert fallback_bundle.fallback_only is True

    short_res = predict_next_7d(syn.transactions_df, "user_short_001", date(2026, 1, 14), fallback_bundle)
    assert short_res.status == "insufficient_data"
    assert short_res.days_available == 14

    ok_res = predict_next_7d(syn.transactions_df, "user_001", date(2026, 6, 15), fallback_bundle)
    assert ok_res.status == "fallback_baseline"
    assert ok_res.predicted_total_vnd is not None and ok_res.predicted_total_vnd >= 0.0


def test_retrain_atomic_promotion_and_latency_under_3_seconds(tmp_path: Path):
    cfg = load_config(Path("configs/default.yaml"))
    syn = generate_synthetic_dataset(cfg)
    ds_dir = tmp_path / "synthetic"
    active_ptr = tmp_path / "models" / "active.json"

    r1 = retrain_and_maybe_promote(syn.transactions_df, syn.profile_windows, None, ds_dir, active_ptr, cfg, "v1.0.0")
    assert r1["promoted"] is True

    flagged_tx_id = syn.transactions_df[
        (syn.transactions_df["user_id"] == "user_001") & (syn.transactions_df["type"] == "expense")
    ].iloc[0]["transaction_id"]
    fb = pd.DataFrame([{
        "transaction_id": flagged_tx_id,
        "user_id": "user_001",
        "is_confirmed_anomaly": True,
        "model_version": "v1.0.0",
        "created_at": "2026-05-01T10:00:00+07:00",
    }])
    r2 = retrain_and_maybe_promote(syn.transactions_df, syn.profile_windows, fb, ds_dir, active_ptr, cfg, "v1.1.0")
    assert "candidate_val_mae" in r2 and "active_val_mae_on_new_window" in r2

    bundle = ModelBundleLoader(active_ptr).load()
    anom = detect_anomalies(syn.transactions_df, "user_001", bundle)
    assert anom.model_version in {"v1.0.0", "v1.1.0"}

    bench = run_latency_benchmark(bundle, syn.transactions_df, "user_001", date(2026, 9, 1), n_runs=25)
    assert bench["n_runs"] == 25
    assert bench["max_latency_sec"] <= 3.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_inference_and_retrain.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `loader.py`, `predictor.py`, `benchmark.py`, and `scripts/retrain.py`**

Implement `ModelBundleLoader` (catching `FileNotFoundError` / corrupt pickle errors cleanly into `LoadedBundle(fallback_only=True)` when `allow_baseline_fallback=True`), `predict_next_7d` (resolving `effective_start = tracking_start_date or min(tx_date <= as_of_date)`, computing `days_available`, returning `insufficient_data` when `< 28` or no prior transactions, otherwise calling `aggregate_daily_spending` + `build_single_forecast_features`), `detect_anomalies` (filtering qualifying expense rows for `user_id`, scoring causally, optionally filtering output to `target_transaction_ids`), `run_latency_benchmark` (timing `>= 20` sequential single-user forecast + anomaly inference calls and capturing OS/CPU/Python specs), and `retrain_and_maybe_promote` + CLI in `scripts/retrain.py` (re-evaluating active bundle on the exact same new validation split and promoting atomically only when F3 & F4 gates pass).

- [ ] **Step 4: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_inference_and_retrain.py -v`
Expected: PASS

```bash
git add src/finance_ml/inference/__init__.py src/finance_ml/inference/loader.py src/finance_ml/inference/predictor.py src/finance_ml/inference/benchmark.py scripts/retrain.py tests/test_inference_and_retrain.py
git commit -m "feat: add inference API, missing-model fallback, retraining gate, and latency benchmark"
```

---

### Task 8: EDA, Manual Review CSV, Model Card, ML Integration Contract & README (`N1/N3/N4`)

**Files:**
- Create: `src/finance_ml/reporting/__init__.py`
- Create: `src/finance_ml/reporting/eda.py`
- Create: `src/finance_ml/reporting/review_export.py`
- Create: `src/finance_ml/reporting/model_card.py`
- Create: `scripts/run_eda.py`
- Create: `docs/data_dictionary.md`
- Create: `contracts/ML_INTEGRATION_CONTRACT.md`
- Create: `contracts/samples/forecast_request.json`
- Create: `contracts/samples/forecast_response_ok.json`
- Create: `contracts/samples/forecast_response_insufficient.json`
- Create: `contracts/samples/anomaly_request.json`
- Create: `contracts/samples/anomaly_response.json`
- Create: `README.md`
- Test: `tests/test_reporting_and_contracts.py`

**Interfaces:**
- Consumes: Tasks 1–7 interfaces
- Produces:
  - `generate_eda_artifacts(dataset_name: str, clean_df: pd.DataFrame, daily_df: pd.DataFrame, manifest: DataManifest, figures_dir: Path, report_path: Path) -> list[Path]`
  - `export_manual_review_sample(scored_df: pd.DataFrame, out_path: Path, top_k: int = 30, random_k: int = 30, seed: int = 42) -> Path`
  - `render_model_card(out_path: Path, artifacts_root: Path) -> Path`

- [ ] **Step 1: Write the failing reporting & JSON contract validation tests in `tests/test_reporting_and_contracts.py`**

```python
import json
from pathlib import Path
import pandas as pd
from finance_ml.schema import ForecastResult, AnomalyBatchResult
from finance_ml.reporting.review_export import export_manual_review_sample


def test_manual_review_export_has_top30_and_random30_with_reviewer_columns(tmp_path: Path):
    df = pd.DataFrame([
        {
            "transaction_id": f"tx_{i}",
            "user_id": "user_001",
            "timestamp": f"2026-08-{(i % 28) + 1:02d}T12:00:00+07:00",
            "amount_vnd": float((i + 1) * 10000),
            "category": "shopping",
            "anomaly_score": float(i) / 100.0,
            "is_anomaly": i >= 85,
            "reasons": ["Cao bất thường"] if i >= 85 else [],
        }
        for i in range(100)
    ])
    out_csv = export_manual_review_sample(df, tmp_path / "review.csv", top_k=30, random_k=30, seed=42)
    saved = pd.read_csv(out_csv)
    assert len(saved) == 60
    assert {"sample_group", "khoa_label", "duy_label", "reviewer_notes"}.issubset(saved.columns)
    assert (saved["sample_group"] == "top_alert").sum() == 30
    assert (saved["sample_group"] == "random_sample").sum() == 30


def test_contract_sample_jsons_validate_against_pydantic_schemas():
    ok = json.loads(Path("contracts/samples/forecast_response_ok.json").read_text(encoding="utf-8"))
    insuf = json.loads(Path("contracts/samples/forecast_response_insufficient.json").read_text(encoding="utf-8"))
    anom = json.loads(Path("contracts/samples/anomaly_response.json").read_text(encoding="utf-8"))
    ForecastResult.model_validate(ok)
    ForecastResult.model_validate(insuf)
    AnomalyBatchResult.model_validate(anom)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_reporting_and_contracts.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `eda.py`, `review_export.py`, `model_card.py`, `scripts/run_eda.py`, `docs/data_dictionary.md`, `contracts/*`, and `README.md`**

Implement `generate_eda_artifacts` (saving daily spend trend, category share bar chart, and amount distribution PNGs under `artifacts/<dataset>/figures/` and updating the clearly separated `synthetic` / `real_public` sections in `docs/eda_report.md`), `export_manual_review_sample` (selecting up to 30 highest-scored alerts + 30 random non-overlapping rows with reviewer columns, also wired into `scripts/evaluate.py`), `render_model_card` (populating `docs/model_card.md` from `artifacts/*/models/active.json` and `artifacts/*/metrics/*.json`, clearly marking Test as *Locked per 2A* when `test_metrics.json` is absent and auto-filling when unlocked), `docs/data_dictionary.md`, `contracts/ML_INTEGRATION_CONTRACT.md` + validated `contracts/samples/*.json` for Khoa & Duy, and `README.md` with clean-machine setup & exact one-shot `--unlock-test` command.

- [ ] **Step 4: Run tests to verify they pass and commit**

Run: `uv run pytest tests/test_reporting_and_contracts.py -v`
Expected: PASS

```bash
git add src/finance_ml/reporting/__init__.py src/finance_ml/reporting/eda.py src/finance_ml/reporting/review_export.py src/finance_ml/reporting/model_card.py scripts/run_eda.py scripts/evaluate.py docs/data_dictionary.md contracts/ README.md tests/test_reporting_and_contracts.py
git commit -m "feat: add EDA reporting, manual review exporter, model card, and FastAPI ML contracts"
```

---

### Task 9: Thin Google Colab Notebook Builder, Full Validation Run & Google Drive Upload (`1A` + `2A`)

**Files:**
- Create: `scripts/build_colab_notebook.py`
- Test: `tests/test_colab_package.py`

**Interfaces:**
- Consumes: Entire `src/finance_ml`, `configs/default.yaml`, `requirements-ml.txt`, `scripts/*`
- Produces:
  - `build_colab_artifacts(notebook_path: Path, zip_path: Path) -> None`
  - Generated `notebooks/finance_ml_colab.ipynb` & `artifacts/colab/finance_ml_colab_package.zip`
  - Full `synthetic` validation/rolling-CV/EDA/model-card artifacts (with `test` kept locked per `2A`)
  - Uploaded Google Drive folder `My Drive/PTHTTM_Nhan_ML_Colab/` containing native Colab notebook + source zip (`1A`)

- [ ] **Step 1: Write the failing Colab notebook & zip package test in `tests/test_colab_package.py`**

```python
import zipfile
from pathlib import Path
import nbformat
from scripts.build_colab_notebook import build_colab_artifacts


def test_build_colab_artifacts_creates_valid_thin_notebook_and_complete_zip(tmp_path: Path):
    nb_path = tmp_path / "finance_ml_colab.ipynb"
    zip_path = tmp_path / "finance_ml_colab_package.zip"
    build_colab_artifacts(nb_path, zip_path)

    nb = nbformat.read(nb_path, as_version=4)
    nbformat.validate(nb)
    full_source = "\n".join(c.source for c in nb.cells if c.cell_type == "code")
    assert "finance_ml" in full_source
    assert "requirements-ml.txt" in full_source
    assert "--unlock-test" not in "\n".join(
        line for line in full_source.splitlines() if not line.strip().startswith("#")
    )

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "pyproject.toml" in names
        assert "requirements-ml.txt" in names
        assert "configs/default.yaml" in names
        assert any(n.startswith("src/finance_ml/") for n in names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_colab_package.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `scripts/build_colab_notebook.py` using `nbformat`**

Generate the 5-cell thin notebook specified in Section 5.7 of the design doc (Cell 1: mount Drive `/content/drive/MyDrive/PTHTTM_Nhan_ML_Colab`, unzip `finance_ml_colab_package.zip`, `pip install -q -r requirements-ml.txt` + `pip install -q --no-deps -e .`, print GPU/CPU & library versions; Cell 2: synthetic/public data + EDA plots; Cell 3: F3 rolling CV & validation comparison; Cell 4: F4 Isolation Forest validation threshold, Vietnamese reasons & synthetic injection benchmark; Cell 5: export `.joblib` bundle & review CSV to Drive, with final 1-shot test unlock commented out per `2A`) and bundle `pyproject.toml`, `requirements-ml.txt`, `configs/`, `src/`, `scripts/` into `artifacts/colab/finance_ml_colab_package.zip`.

- [ ] **Step 4: Run full `pytest` suite & execute end-to-end local pipeline up to Validation (`2A`)**

Run:
```bash
uv run pytest -v && \
uv run python scripts/generate_data.py && \
uv run python scripts/prepare_public_data.py && \
uv run python scripts/run_eda.py --dataset synthetic && \
uv run python scripts/train.py --dataset synthetic && \
uv run python scripts/evaluate.py --dataset synthetic && \
uv run python scripts/build_colab_notebook.py
```
Expected: All tests PASS; `artifacts/synthetic/models/active.json`, `artifacts/synthetic/metrics/validation_metrics.json`, `artifacts/synthetic/metrics/latency_benchmark.json`, `artifacts/synthetic/anomaly_manual_review_validation.csv`, `docs/eda_report.md`, and `docs/model_card.md` exist; `artifacts/synthetic/metrics/test_evaluation_lock.json` does **NOT** exist (`test` remains locked).

- [ ] **Step 5: Upload Colab notebook & package to `My Drive/PTHTTM_Nhan_ML_Colab/` via `gdrive` (`1A`) and commit**

Create folder `PTHTTM_Nhan_ML_Colab` in My Drive (or reuse if existing), upload `notebooks/finance_ml_colab.ipynb` with `--mime-type "application/vnd.google.colaboratory"` and `artifacts/colab/finance_ml_colab_package.zip`, verify URLs via `gdrive readonly url`, then commit all source, docs, contracts, and notebook files.

```bash
git add scripts/build_colab_notebook.py notebooks/finance_ml_colab.ipynb docs/eda_report.md docs/model_card.md tests/test_colab_package.py
git commit -m "feat: add thin Google Colab notebook builder and complete validation pipeline"
```
