"""Single-user post-load inference latency benchmark (>= 20 runs, <= 3.0s SLA)."""

from __future__ import annotations

from datetime import date
import platform
import sys
import time
from typing import Any
import numpy as np
import pandas as pd

from finance_ml.inference.loader import LoadedBundle
from finance_ml.inference.predictor import detect_anomalies, predict_next_7d


def run_latency_benchmark(
    bundle: LoadedBundle,
    transactions_df: pd.DataFrame,
    user_id: str,
    as_of_date: date,
    n_runs: int = 25,
) -> dict[str, Any]:
    if n_runs < 20:
        raise ValueError("Benchmark requires at least 20 runs per project QA specification.")

    # Pre-slice single user's rows as FastAPI DB query (`WHERE user_id = ?`) does in production
    user_slice = transactions_df[transactions_df["user_id"].astype(str) == str(user_id)].copy()

    latencies: list[float] = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        _ = predict_next_7d(user_slice, user_id, as_of_date, bundle)
        _ = detect_anomalies(user_slice, user_id, bundle)
        latencies.append(time.perf_counter() - t0)

    arr = np.asarray(latencies, dtype=float)
    max_lat = float(np.max(arr))
    return {
        "n_runs": int(n_runs),
        "mean_latency_sec": float(np.mean(arr)),
        "p50_latency_sec": float(np.percentile(arr, 50)),
        "p95_latency_sec": float(np.percentile(arr, 95)),
        "max_latency_sec": max_lat,
        "sla_limit_sec": 3.0,
        "meets_3s_sla": bool(max_lat <= 3.0),
        "machine_info": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version.split()[0],
        },
    }
