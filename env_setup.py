"""Load environment variables from project root and optional ``app/.env`` (later file overrides)."""

from __future__ import annotations

import os
from pathlib import Path


def _load_env_file_simple(path: Path, *, override: bool) -> None:
    """Minimal ``.env`` reader when ``python-dotenv`` is not installed (Streamlit does not bundle it)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].lstrip()
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        val = val.strip()
        if not (val.startswith('"') or val.startswith("'")):
            if " #" in val:
                val = val.split(" #", 1)[0].rstrip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if not key:
            continue
        if override:
            os.environ[key] = val
        elif key not in os.environ:
            os.environ[key] = val


def load_pop_dotenv() -> None:
    root = Path(__file__).resolve().parent
    env_root = root / ".env"
    env_app = root / "app" / ".env"

    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # type: ignore[assignment]

    # override=True: project files win over empty shell exports (e.g. OPENAI_API_KEY= in .zshrc).
    def _load(path: Path, *, override: bool) -> None:
        if not path.is_file():
            return
        if load_dotenv is not None:
            load_dotenv(path, override=override)
        else:
            _load_env_file_simple(path, override=override)

    _load(env_root, override=True)
    _load(env_app, override=True)
