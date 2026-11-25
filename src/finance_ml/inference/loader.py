"""Safe model bundle loader with missing/corrupt fallback support."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import joblib

from finance_ml.models.registry import ModelBundle, resolve_pointer_bundle_dir


@dataclass
class LoadedBundle:
    bundle: ModelBundle | None
    fallback_only: bool
    version: str
    error_message: str | None = None


class ModelBundleLoader:
    def __init__(self, pointer_or_dir: Path, allow_baseline_fallback: bool = True) -> None:
        self.pointer_or_dir = Path(pointer_or_dir)
        self.allow_baseline_fallback = allow_baseline_fallback

    def load(self) -> LoadedBundle:
        try:
            target = self.pointer_or_dir
            if target.suffix == ".json":
                bundle_dir = resolve_pointer_bundle_dir(target)
            else:
                bundle_dir = target

            joblib_path = bundle_dir / "bundle.joblib"
            loaded: ModelBundle = joblib.load(joblib_path)
            return LoadedBundle(
                bundle=loaded,
                fallback_only=False,
                version=loaded.version,
                error_message=None,
            )
        except Exception as exc:
            if not self.allow_baseline_fallback:
                raise RuntimeError(f"Failed to load model bundle from {self.pointer_or_dir}: {exc}") from exc
            return LoadedBundle(
                bundle=None,
                fallback_only=True,
                version="fallback-baseline",
                error_message=str(exc),
            )
