"""
SciLeads Cache Layer — reduces API calls to portal.scileads.com
================================================================

Strategy:
- Every SciLeads search result is cached in platform.db (scileads_cache table)
- Subsequent searches for the same keyword serve from cache (< 24h)
- Global cooldown: max 1 real API call per 30 seconds
- Use ?refresh=true to bypass cache and force a fresh fetch
"""

import time
import json
import logging
from pathlib import Path
from typing import List, Optional
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "platform.db"
COOLDOWN_SECONDS = 30       # min interval between real SciLeads API calls
CACHE_TTL_SECONDS = 86400   # 24h before cache is considered stale

_last_api_call = 0.0


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def save_to_cache(keyword: str, researchers: list):
    """Store search results in local cache."""
    conn = _get_conn()
    now = int(time.time())
    count = 0
    for r in researchers:
        rid = r.get("id") or r.get("researcher_id", 0)
        if not rid:
            continue
        try:
            data_json = json.dumps(r, default=str)
            conn.execute(
                """INSERT OR REPLACE INTO scileads_cache 
                   (search_keyword, researcher_id, data_json, fetched_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (keyword.lower().strip(), int(rid), data_json),
            )
            count += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    if count:
        logger.info(f"SciLeads cache: saved {count} results for '{keyword}'")


def get_from_cache(keyword: str, max_age_seconds: int = CACHE_TTL_SECONDS) -> Optional[List[dict]]:
    """Get cached search results. Returns None if cache miss or stale."""
    conn = _get_conn()
    cutoff = int(time.time()) - max_age_seconds
    rows = conn.execute(
        """SELECT data_json FROM scileads_cache 
           WHERE search_keyword = ? 
           AND CAST(strftime('%s', fetched_at) AS INTEGER) > ?
           ORDER BY fetched_at DESC""",
        (keyword.lower().strip(), cutoff),
    ).fetchall()
    conn.close()

    if not rows:
        return None

    results = []
    for row in rows:
        try:
            results.append(json.loads(row["data_json"]))
        except Exception:
            pass
    return results if results else None


def cache_is_fresh(keyword: str) -> bool:
    """Check if cache exists and is recent (< 24h)."""
    conn = _get_conn()
    cutoff = int(time.time()) - CACHE_TTL_SECONDS
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM scileads_cache 
           WHERE search_keyword = ? 
           AND CAST(strftime('%s', fetched_at) AS INTEGER) > ?""",
        (keyword.lower().strip(), cutoff),
    ).fetchone()
    conn.close()
    return (row["cnt"] if row else 0) > 0


def should_throttle() -> float:
    """Check if we're within the global cooldown window.
    Returns 0 if OK to proceed, or seconds to wait.
    """
    global _last_api_call
    elapsed = time.time() - _last_api_call
    if elapsed < COOLDOWN_SECONDS:
        return COOLDOWN_SECONDS - elapsed
    return 0


def mark_api_call():
    """Record that a real SciLeads API call was made."""
    global _last_api_call
    _last_api_call = time.time()


def get_cache_stats() -> dict:
    """Get cache statistics for dashboard info."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) as cnt FROM scileads_cache").fetchone()
    keywords = conn.execute(
        "SELECT search_keyword, COUNT(*) as cnt, MAX(fetched_at) as last_fetch FROM scileads_cache GROUP BY search_keyword ORDER BY last_fetch DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return {
        "total_cached": total["cnt"] if total else 0,
        "recent_searches": [
            {"keyword": k["search_keyword"], "results": k["cnt"], "last_fetch": k["last_fetch"]}
            for k in keywords
        ],
        "cooldown_seconds": COOLDOWN_SECONDS,
        "cache_ttl_hours": CACHE_TTL_SECONDS // 3600,
        "last_api_call": time.strftime("%H:%M:%S", time.localtime(_last_api_call)) if _last_api_call else "never",
    }
