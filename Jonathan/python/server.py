"""
Static site + JSON API for Beverage Trend Scout.

Run from repo root:
  cd BeverageTrendScout/python
  pip install -r requirements.txt
  python server.py

Then open http://127.0.0.1:5055/
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import cache_manager
import config
import pipeline

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[1]
_PUBLIC = _ROOT / "public"

app = Flask(__name__, static_folder=str(_PUBLIC), static_url_path="")


@app.after_request
def cors(resp):
    origin = request.headers.get("Origin") or ""
    if origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost"):
        resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "beverage-trend-scout"})


@app.route("/api/feed", methods=["GET"])
def feed():
    """
    Returns cached opportunities for fast loads.
    Use POST /api/refresh to rebuild from Rainforest + Trends + Walmart + Reddit.
    """
    payload = cache_manager.read_cache()
    if not payload:
        if config.RAINFOREST_API_KEY:
            try:
                payload = pipeline.build_feed()
                cache_manager.write_cache(payload)
            except Exception as e:
                LOG.exception("Initial build failed: %s", e)
                payload = pipeline.build_feed()
                cache_manager.write_cache(payload)
        else:
            payload = pipeline.build_feed()
            cache_manager.write_cache(payload)
    stale = cache_manager.is_stale(payload)
    body = dict(payload)
    body["cache_stale"] = stale
    return jsonify(body)


@app.route("/api/refresh", methods=["POST", "OPTIONS"])
def refresh():
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        if not config.RAINFOREST_API_KEY:
            payload = pipeline.build_feed()
            cache_manager.write_cache(payload)
            return jsonify({"ok": True, "mode": "demo", "count": len(payload.get("opportunities") or [])})
        payload = pipeline.build_feed()
        cache_manager.write_cache(payload)
        return jsonify({"ok": True, "mode": "live", "count": len(payload.get("opportunities") or [])})
    except Exception as e:
        LOG.exception("Refresh failed")
        return jsonify({"ok": False, "error": str(e)}), 502


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:filename>")
def static_files(filename: str):
    target = Path(app.static_folder) / filename
    if target.is_file():
        return send_from_directory(app.static_folder, filename)
    return send_from_directory(app.static_folder, "index.html")


def main():
    cache_manager.ensure_cache()
    app.run(host="127.0.0.1", port=config.PORT, debug=False)


if __name__ == "__main__":
    main()
