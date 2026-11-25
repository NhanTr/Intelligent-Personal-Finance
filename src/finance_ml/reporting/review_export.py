"""Manual review sample exporter (top-K alerts + random-K background) for Khoa & Duy."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def export_manual_review_sample(
    scored_df: pd.DataFrame,
    out_path: Path,
    top_k: int = 30,
    random_k: int = 30,
    seed: int = 42,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if scored_df.empty:
        empty = pd.DataFrame(
            columns=[
                "sample_group",
                "transaction_id",
                "user_id",
                "timestamp",
                "amount_vnd",
                "category",
                "anomaly_score",
                "is_anomaly",
                "reasons_text",
                "khoa_label",
                "duy_label",
                "reviewer_notes",
            ]
        )
        empty.to_csv(out_path, index=False)
        return out_path

    df = scored_df.sort_values(["anomaly_score", "transaction_id"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    top_part = df.head(min(top_k, len(df))).copy()
    top_part["sample_group"] = "top_alert"

    remaining = df.iloc[len(top_part) :].copy()
    rng = np.random.default_rng(seed)
    if len(remaining) > 0 and random_k > 0:
        n_pick = min(random_k, len(remaining))
        picked_idx = np.sort(rng.choice(len(remaining), size=n_pick, replace=False))
        rand_part = remaining.iloc[picked_idx].copy()
        rand_part["sample_group"] = "random_sample"
        combined = pd.concat([top_part, rand_part], ignore_index=True)
    else:
        combined = top_part

    combined["reasons_text"] = combined["reasons"].apply(
        lambda r: " | ".join(r) if isinstance(r, list) else str(r or "")
    )
    combined["khoa_label"] = ""
    combined["duy_label"] = ""
    combined["reviewer_notes"] = ""

    cols = [
        "sample_group",
        "transaction_id",
        "user_id",
        "timestamp",
        "amount_vnd",
        "category",
        "anomaly_score",
        "is_anomaly",
        "reasons_text",
        "khoa_label",
        "duy_label",
        "reviewer_notes",
    ]
    combined[cols].to_csv(out_path, index=False)
    return out_path
