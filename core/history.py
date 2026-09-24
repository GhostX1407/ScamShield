"""
history.py – SQLite-backed scan history.
Full implementation in Part 4. This stub prevents import errors in Part 3.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent.parent / "scamshield.db"
_PREVIEW_LEN = 60


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                input_type TEXT NOT NULL,
                preview    TEXT NOT NULL,
                verdict    TEXT NOT NULL,
                score      INTEGER NOT NULL,
                flags      TEXT NOT NULL,
                language   TEXT NOT NULL
            )
        """)
        conn.commit()


_ensure_table()


def save_scan(result: dict, preview_text: str = "") -> int:
    preview = preview_text[:_PREVIEW_LEN].strip()
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
                result.get("score", 0),
                json.dumps(flag_ids),
                result.get("language", "en"),
            ),
        )
        conn.commit()
        return cur.lastrowid


def list_scans(verdict=None, input_type=None, date=None) -> list[dict]:
    query  = "SELECT * FROM scans WHERE 1=1"
    params = []
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


def delete_scan(scan_id: int) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        conn.commit()
        return cur.rowcount > 0


def delete_all_scans() -> int:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM scans")
        conn.commit()
        return cur.rowcount


def get_stats() -> dict:
    with _get_conn() as conn:
        verdict_rows = conn.execute(
            "SELECT verdict, COUNT(*) as count FROM scans GROUP BY verdict"
        ).fetchall()
        flag_rows = conn.execute("SELECT flags FROM scans").fetchall()

    verdict_counts = {r["verdict"]: r["count"] for r in verdict_rows}

    flag_freq: dict[str, int] = {}
    for row in flag_rows:
        for fid in json.loads(row["flags"]):
            flag_freq[fid] = flag_freq.get(fid, 0) + 1

    top_flags = sorted(flag_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total":          sum(verdict_counts.values()),
        "by_verdict":     verdict_counts,
        "top_flags":      [{"id": k, "count": v} for k, v in top_flags],
    }
