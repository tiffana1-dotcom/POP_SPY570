"""Read/write cache.json with TTL metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config


def _parse_generated_at(raw: str | None) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def is_stale(payload: dict[str, Any]) -> bool:
    gen = _parse_generated_at(str(payload.get("generated_at") or ""))
    if not gen:
        return True
    age_h = (datetime.now(timezone.utc) - gen).total_seconds() / 3600.0
    ttl = float(payload.get("cache_ttl_hours") or config.CACHE_TTL_HOURS)
    return age_h >= ttl


def read_cache() -> dict[str, Any] | None:
    path: Path = config.CACHE_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_cache(payload: dict[str, Any]) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def ensure_cache() -> dict[str, Any]:
    """Return valid cache dict, seeding demo data if missing."""
    existing = read_cache()
    if existing and isinstance(existing.get("opportunities"), list):
        return existing
    import pipeline

    payload = pipeline.build_feed()
    write_cache(payload)
    return payload
