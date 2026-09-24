"""
history.py – SQLite-backed scan history.

Table: scans
  id         – auto primary key
  timestamp  – ISO-8601 UTC
  input_type – message | link | qr | upi
  preview    – first 60 chars ONLY (privacy: never the full text)
  verdict    – Safe | Suspicious | Dangerous
  score      – 0-100
  flags      – JSON array of flag IDs (not translated strings)
  language   – en | hi | hinglish

All queries use parameterized statements (no SQL injection possible).
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH      = Path(__file__).parent.parent / "scamshield.db"
_PREVIEW_LEN = 60


# ── Connection helper ──────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent read performance
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────

def _ensure_table() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT    NOT NULL,
                input_type TEXT    NOT NULL,
                preview    TEXT    NOT NULL,
                verdict    TEXT    NOT NULL,
                score      INTEGER NOT NULL,
                flags      TEXT    NOT NULL DEFAULT '[]',
                language   TEXT    NOT NULL DEFAULT 'en'
            )
        """)
        # Index for the most common filter operations
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verdict    ON scans(verdict)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_input_type ON scans(input_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp  ON scans(timestamp)"
        )
        conn.commit()


_ensure_table()


# ── Write operations ───────────────────────────────────────────────────────

def save_scan(result: dict, preview_text: str = "") -> int:
    """
    Persist a scan result.  Returns the new row id.
    preview_text is truncated to _PREVIEW_LEN characters before storage.
    Only flag IDs (not translated strings) are stored.
    """
    preview  = preview_text.strip()[:_PREVIEW_LEN]
    flag_ids = [f["id"] for f in result.get("flags", [])]

    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO scans
               (timestamp, input_type, preview, verdict, score, flags, language)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                result.get("input_type", "message"),
                preview,
                result.get("verdict", "Safe"),
                int(result.get("score", 0)),
                json.dumps(flag_ids),
                result.get("language", "en"),
            ),
        )
        conn.commit()
        return cur.lastrowid


def delete_scan(scan_id: int) -> bool:
    """Delete one scan row.  Returns True if a row was actually deleted."""
    with _get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM scans WHERE id = ?", (scan_id,)
        )
        conn.commit()
        return cur.rowcount > 0


def delete_all_scans() -> int:
    """Delete every scan row.  Returns the number of rows deleted."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM scans")
        conn.commit()
        return cur.rowcount


# ── Read operations ────────────────────────────────────────────────────────

def get_scan(scan_id: int) -> dict | None:
    """Fetch a single scan row by id, or None if not found."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,)
        ).fetchone()
    return dict(row) if row else None


def list_scans(
    verdict:    str | None = None,
    input_type: str | None = None,
    date:       str | None = None,
) -> list[dict]:
    """
    Return all scans, newest first.

    Optional filters (all parameterized):
      verdict    – exact match ("Safe" | "Suspicious" | "Dangerous")
      input_type – exact match ("message" | "link" | "qr" | "upi")
      date       – ISO date string "YYYY-MM-DD", matches on UTC date
    """
    query  = "SELECT * FROM scans WHERE 1=1"
    params: list = []

    if verdict:
        query += " AND verdict = ?"
        params.append(verdict)
    if input_type:
        query += " AND input_type = ?"
        params.append(input_type)
    if date:
        query += " AND DATE(timestamp) = ?"
        params.append(date)

    query += " ORDER BY id DESC"

    with _get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# ── Stats ──────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """
    Return aggregate statistics:
      total        – total scan count
      by_verdict   – { "Safe": N, "Suspicious": N, "Dangerous": N }
      by_type      – { "message": N, "link": N, "qr": N, "upi": N }
      top_flags    – top-10 flag IDs by occurrence frequency
    """
    with _get_conn() as conn:
        verdict_rows = conn.execute(
            "SELECT verdict, COUNT(*) AS cnt FROM scans GROUP BY verdict"
        ).fetchall()
        type_rows = conn.execute(
            "SELECT input_type, COUNT(*) AS cnt FROM scans GROUP BY input_type"
        ).fetchall()
        flag_rows = conn.execute("SELECT flags FROM scans").fetchall()

    by_verdict = {r["verdict"]: r["cnt"] for r in verdict_rows}
    by_type    = {r["input_type"]: r["cnt"] for r in type_rows}

    flag_freq: dict[str, int] = {}
    for row in flag_rows:
        for fid in json.loads(row["flags"]):
            flag_freq[fid] = flag_freq.get(fid, 0) + 1

    top_flags = sorted(flag_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total":      sum(by_verdict.values()),
        "by_verdict": by_verdict,
        "by_type":    by_type,
        "top_flags":  [{"id": k, "count": v} for k, v in top_flags],
    }
