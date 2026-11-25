"""Processed dataset stream I/O helpers."""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from finance_ml.data.cleaning import clean_transactions
from finance_ml.schema import ProfileWindow


def load_processed_stream(proc_dir: Path) -> tuple[pd.DataFrame, dict[str, ProfileWindow]]:
    tx_path = Path(proc_dir) / "transactions.csv"
    win_path = Path(proc_dir) / "profile_windows.json"
    if not tx_path.exists() or not win_path.exists():
        raise FileNotFoundError(f"Processed stream not found in {proc_dir}. Run data preparation first.")
    raw_tx = pd.read_csv(tx_path)
    clean_df, _ = clean_transactions(raw_tx)
    raw_win = json.loads(win_path.read_text(encoding="utf-8"))
    windows = {k: ProfileWindow.model_validate(v) for k, v in raw_win.items()}
    return clean_df, windows


def filter_eligible_windows(
    windows: dict[str, ProfileWindow],
    min_days: int = 180,
) -> dict[str, ProfileWindow]:
    return {
        u: w
        for u, w in windows.items()
        if (w.tracking_end_date - w.tracking_start_date).days + 1 >= min_days
    }
