"""One-shot test split evaluation guard with audit trail."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from finance_ml.schema import VN_TZ


class TestLockGuard:
    __test__ = False

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = Path(lock_path)

    def is_locked(self) -> bool:
        return not self.lock_path.exists()

    def verify_and_record(
        self,
        unlock: bool,
        reason: str | None,
        config_hash: str,
    ) -> dict[str, Any]:
        if not unlock:
            raise PermissionError(
                "Test split is locked (policy 2A). Pass --unlock-test --reason '<reason>' "
                "only when configuration is frozen for the one-shot test evaluation."
            )

        clean_reason = (reason or "").strip()
        if not clean_reason:
            raise PermissionError("A non-empty --reason is required to unlock or re-evaluate the test split.")

        existing: dict[str, Any] = {"unlock_count": 0, "history": []}
        if self.lock_path.exists():
            existing = json.loads(self.lock_path.read_text(encoding="utf-8"))

        is_rerun = int(existing.get("unlock_count", 0)) >= 1
        if is_rerun:
            if not clean_reason.lower().startswith("bugfix:") or not clean_reason.split(":", 1)[1].strip():
                raise PermissionError(
                    "Test split was already unlocked once. Any subsequent run must be justified as an "
                    "implementation bugfix prefixed with 'bugfix: <explanation>'."
                )
        entry = {
            "timestamp": datetime.now(timezone.utc).astimezone(VN_TZ).isoformat(),
            "reason": clean_reason,
            "config_hash": config_hash,
            "is_implementation_bugfix_rerun": is_rerun,
        }
        existing["unlock_count"] = int(existing.get("unlock_count", 0)) + 1
        existing.setdefault("history", []).append(entry)

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return existing
