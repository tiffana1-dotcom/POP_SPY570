"""Load configuration from environment (.env optional)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

DATA_DIR = Path(os.environ.get("BEVERAGE_DATA_DIR", str(_ROOT / "data"))).resolve()
CACHE_FILE = DATA_DIR / "cache.json"

RAINFOREST_API_KEY = (os.environ.get("RAINFOREST_API_KEY") or "").strip()
AMAZON_DOMAIN = (os.environ.get("AMAZON_DOMAIN") or "amazon.com").strip()

# Walmart — either legacy-style key (WM_CONSUMER.ID) or OAuth client credentials
WALMART_KEY = (os.environ.get("WALMART_KEY") or "").strip()
WALMART_CLIENT_ID = (os.environ.get("WALMART_CLIENT_ID") or "").strip()
WALMART_CLIENT_SECRET = (os.environ.get("WALMART_CLIENT_SECRET") or "").strip()
WALMART_PUBLISHER_ID = (os.environ.get("WALMART_PUBLISHER_ID") or "").strip()

# Reddit: public JSON — descriptive User-Agent required; optional comma-separated subreddits
REDDIT_USER_AGENT = (
    os.environ.get("REDDIT_USER_AGENT") or "BeverageTrendScout/1.0 (educational; contact@localhost)"
).strip()
_REDDIT_SUBS_RAW = os.environ.get(
    "REDDIT_SUBREDDITS",
    "asianeats,tea,casualuk,EatCheapAndHealthy,xxkpop",
)
REDDIT_SUBREDDITS: list[str] = [s.strip() for s in _REDDIT_SUBS_RAW.split(",") if s.strip()]
REDDIT_SUB_SLEEP_SEC = float(os.environ.get("REDDIT_SUB_SLEEP_SEC") or "0.5")
REDDIT_SUB_LIMIT = int(os.environ.get("REDDIT_SUB_LIMIT") or "10")
REDDIT_MAX_SUBREDDITS = int(os.environ.get("REDDIT_MAX_SUBREDDITS") or "5")
REDDIT_MAX_TOTAL_MENTIONS = int(os.environ.get("REDDIT_MAX_TOTAL_MENTIONS") or "40")
REDDIT_MAX_SAMPLE_TITLES = int(os.environ.get("REDDIT_MAX_SAMPLE_TITLES") or "12")

CACHE_TTL_HOURS = float(os.environ.get("CACHE_TTL_HOURS") or "6")
MAX_PRODUCTS = int(os.environ.get("MAX_PRODUCTS") or "24")
RAINFOREST_SEARCH_PAGES = int(os.environ.get("RAINFOREST_SEARCH_PAGES") or "2")
RAINFOREST_MAX_RESULTS = int(os.environ.get("RAINFOREST_MAX_RESULTS") or "5")
PORT = int(os.environ.get("PORT") or "5055")
