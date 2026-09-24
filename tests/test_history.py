"""
test_history.py – Unit + integration tests for the history module and API.

Tests cover:
  - DB auto-creation
  - save_scan with preview truncation
  - list_scans: no filter, verdict filter, type filter, date filter
  - get_scan: existing and non-existing id
  - delete_scan: existing and non-existing id
  - delete_all_scans
  - get_stats: totals, by_verdict, by_type, top_flags
  - SQL injection resistance
  - Flask API: GET /api/history, DELETE /api/history/<id>, DELETE /api/history, GET /api/history/stats
"""

import json
import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import core.history as _hist_module


# ─── Fixture: redirect the DB to a temp file so tests are isolated ─────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets a fresh, empty SQLite database."""
    db_file = tmp_path / "test_scamshield.db"
    monkeypatch.setattr(_hist_module, "DB_PATH", db_file)

    # Re-create table in the new DB
    _hist_module._ensure_table()
    yield db_file


# ─── Helpers ───────────────────────────────────────────────────────────────

def _make_result(
    verdict="Dangerous",
    score=80,
    input_type="message",
    language="en",
    flag_ids=None,
):
    return {
        "verdict":    verdict,
        "score":      score,
        "input_type": input_type,
        "language":   language,
        "flags":      [{"id": fid} for fid in (flag_ids or ["kyc", "urgency"])],
    }


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 – save_scan
# ═══════════════════════════════════════════════════════════════════════════

def test_save_returns_positive_id():
    rid = _hist_module.save_scan(_make_result(), preview_text="Test message")
    assert isinstance(rid, int) and rid > 0


def test_save_multiple_increments_id():
    id1 = _hist_module.save_scan(_make_result(), preview_text="First")
    id2 = _hist_module.save_scan(_make_result(), preview_text="Second")
    assert id2 > id1


def test_preview_truncated_to_60_chars():
    long_text = "A" * 200
    _hist_module.save_scan(_make_result(), preview_text=long_text)
    rows = _hist_module.list_scans()
    assert len(rows[0]["preview"]) <= 60


def test_preview_exactly_60():
    text = "X" * 60
    _hist_module.save_scan(_make_result(), preview_text=text)
    rows = _hist_module.list_scans()
    assert rows[0]["preview"] == text


def test_preview_shorter_than_60_stored_as_is():
    text = "Short message"
    _hist_module.save_scan(_make_result(), preview_text=text)
    rows = _hist_module.list_scans()
    assert rows[0]["preview"] == text


def test_flags_stored_as_flag_ids_only():
    """Flags must be stored as IDs (strings), not translated text."""
    result = _make_result(flag_ids=["kyc", "threats"])
    _hist_module.save_scan(result, preview_text="test")
    row = _hist_module.list_scans()[0]
    stored = json.loads(row["flags"])
    assert stored == ["kyc", "threats"]


def test_score_stored_as_integer():
    _hist_module.save_scan(_make_result(score=75), preview_text="test")
    row = _hist_module.list_scans()[0]
    assert row["score"] == 75


def test_empty_flags_stored():
    result = _make_result()
    result["flags"] = []
    _hist_module.save_scan(result, preview_text="no flags")
    row = _hist_module.list_scans()[0]
    assert json.loads(row["flags"]) == []


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 – list_scans (no filter)
# ═══════════════════════════════════════════════════════════════════════════

def test_list_empty_db():
    assert _hist_module.list_scans() == []


def test_list_returns_all_rows():
    for i in range(5):
        _hist_module.save_scan(_make_result(), preview_text=f"msg {i}")
    rows = _hist_module.list_scans()
    assert len(rows) == 5


def test_list_newest_first():
    _hist_module.save_scan(_make_result(), preview_text="first")
    _hist_module.save_scan(_make_result(), preview_text="second")
    rows = _hist_module.list_scans()
    assert rows[0]["preview"] == "second"
    assert rows[1]["preview"] == "first"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 – list_scans filters
# ═══════════════════════════════════════════════════════════════════════════

def test_filter_by_verdict():
    _hist_module.save_scan(_make_result(verdict="Dangerous"),   preview_text="d")
    _hist_module.save_scan(_make_result(verdict="Safe"),        preview_text="s")
    _hist_module.save_scan(_make_result(verdict="Suspicious"),  preview_text="su")

    assert len(_hist_module.list_scans(verdict="Dangerous"))  == 1
    assert len(_hist_module.list_scans(verdict="Safe"))       == 1
    assert len(_hist_module.list_scans(verdict="Suspicious")) == 1
    assert len(_hist_module.list_scans(verdict="Nonexistent")) == 0


def test_filter_by_input_type():
    _hist_module.save_scan(_make_result(input_type="message"), preview_text="m")
    _hist_module.save_scan(_make_result(input_type="link"),    preview_text="l")
    _hist_module.save_scan(_make_result(input_type="qr"),      preview_text="q")
    _hist_module.save_scan(_make_result(input_type="upi"),     preview_text="u")

    assert len(_hist_module.list_scans(input_type="message")) == 1
    assert len(_hist_module.list_scans(input_type="link"))    == 1
    assert len(_hist_module.list_scans(input_type="qr"))      == 1
    assert len(_hist_module.list_scans(input_type="upi"))     == 1


def test_filter_by_date_today():
    _hist_module.save_scan(_make_result(), preview_text="today")
    today = datetime.now(timezone.utc).date().isoformat()
    rows  = _hist_module.list_scans(date=today)
    assert len(rows) == 1


def test_filter_by_date_tomorrow_returns_empty():
    _hist_module.save_scan(_make_result(), preview_text="today")
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    rows = _hist_module.list_scans(date=tomorrow)
    assert rows == []


def test_filter_combined_verdict_and_type():
    _hist_module.save_scan(_make_result(verdict="Dangerous", input_type="message"), preview_text="dm")
    _hist_module.save_scan(_make_result(verdict="Safe",      input_type="message"), preview_text="sm")
    _hist_module.save_scan(_make_result(verdict="Dangerous", input_type="link"),    preview_text="dl")

    rows = _hist_module.list_scans(verdict="Dangerous", input_type="message")
    assert len(rows) == 1
    assert rows[0]["preview"] == "dm"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 – get_scan
# ═══════════════════════════════════════════════════════════════════════════

def test_get_scan_existing():
    rid = _hist_module.save_scan(_make_result(), preview_text="hello")
    row = _hist_module.get_scan(rid)
    assert row is not None
    assert row["preview"] == "hello"
    assert row["id"] == rid


def test_get_scan_nonexistent():
    assert _hist_module.get_scan(9999) is None


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 – delete_scan
# ═══════════════════════════════════════════════════════════════════════════

def test_delete_scan_returns_true():
    rid = _hist_module.save_scan(_make_result(), preview_text="to delete")
    assert _hist_module.delete_scan(rid) is True


def test_delete_scan_row_gone():
    rid = _hist_module.save_scan(_make_result(), preview_text="gone")
    _hist_module.delete_scan(rid)
    assert _hist_module.get_scan(rid) is None


def test_delete_scan_nonexistent_returns_false():
    assert _hist_module.delete_scan(99999) is False


def test_delete_one_leaves_others():
    id1 = _hist_module.save_scan(_make_result(), preview_text="keep")
    id2 = _hist_module.save_scan(_make_result(), preview_text="delete me")
    _hist_module.delete_scan(id2)
    remaining = _hist_module.list_scans()
    assert len(remaining) == 1
    assert remaining[0]["id"] == id1


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 – delete_all_scans
# ═══════════════════════════════════════════════════════════════════════════

def test_delete_all_returns_count():
    for i in range(4):
        _hist_module.save_scan(_make_result(), preview_text=f"msg{i}")
    count = _hist_module.delete_all_scans()
    assert count == 4


def test_delete_all_empties_table():
    for i in range(3):
        _hist_module.save_scan(_make_result(), preview_text=f"msg{i}")
    _hist_module.delete_all_scans()
    assert _hist_module.list_scans() == []


def test_delete_all_empty_db_returns_zero():
    assert _hist_module.delete_all_scans() == 0


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 – get_stats
# ═══════════════════════════════════════════════════════════════════════════

def test_stats_empty_db():
    stats = _hist_module.get_stats()
    assert stats["total"] == 0
    assert stats["by_verdict"] == {}
    assert stats["by_type"]    == {}
    assert stats["top_flags"]  == []


def test_stats_total():
    for i in range(3):
        _hist_module.save_scan(_make_result(), preview_text=f"m{i}")
    assert _hist_module.get_stats()["total"] == 3


def test_stats_by_verdict():
    _hist_module.save_scan(_make_result(verdict="Dangerous"),  preview_text="d1")
    _hist_module.save_scan(_make_result(verdict="Dangerous"),  preview_text="d2")
    _hist_module.save_scan(_make_result(verdict="Safe"),       preview_text="s")
    stats = _hist_module.get_stats()
    assert stats["by_verdict"]["Dangerous"] == 2
    assert stats["by_verdict"]["Safe"]      == 1


def test_stats_by_type():
    _hist_module.save_scan(_make_result(input_type="message"), preview_text="m")
    _hist_module.save_scan(_make_result(input_type="link"),    preview_text="l")
    _hist_module.save_scan(_make_result(input_type="link"),    preview_text="l2")
    stats = _hist_module.get_stats()
    assert stats["by_type"]["message"] == 1
    assert stats["by_type"]["link"]    == 2


def test_stats_top_flags():
    _hist_module.save_scan(_make_result(flag_ids=["kyc", "urgency"]), preview_text="a")
    _hist_module.save_scan(_make_result(flag_ids=["kyc", "prize"]),   preview_text="b")
    _hist_module.save_scan(_make_result(flag_ids=["kyc"]),            preview_text="c")
    stats  = _hist_module.get_stats()
    top    = {f["id"]: f["count"] for f in stats["top_flags"]}
    assert top["kyc"]     == 3
    assert top["urgency"] == 1
    assert top["prize"]   == 1


def test_stats_top_flags_max_10():
    """top_flags must never return more than 10 entries."""
    flags = [f"flag_{i}" for i in range(15)]
    result = {"verdict": "Dangerous", "score": 80,
              "input_type": "message", "language": "en",
              "flags": [{"id": f} for f in flags]}
    _hist_module.save_scan(result, preview_text="many flags")
    stats = _hist_module.get_stats()
    assert len(stats["top_flags"]) <= 10


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 – SQL injection resistance
# ═══════════════════════════════════════════════════════════════════════════

def test_sql_injection_verdict_filter():
    """Injecting SQL in the verdict filter must not crash or leak data."""
    _hist_module.save_scan(_make_result(verdict="Dangerous"), preview_text="real")
    # This would break a naive f-string query; parameterized queries handle it safely
    result = _hist_module.list_scans(verdict="' OR '1'='1")
    assert result == []


def test_sql_injection_preview_content():
    """SQL-like content in preview text must be stored safely."""
    evil = "'; DROP TABLE scans; --"
    _hist_module.save_scan(_make_result(), preview_text=evil)
    rows = _hist_module.list_scans()
    # Table must still exist and row must be there (truncated to 60 chars)
    assert len(rows) == 1


def test_sql_injection_date_filter():
    result = _hist_module.list_scans(date="2024-01-01' OR '1'='1")
    assert isinstance(result, list)  # no crash


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9 – Flask API integration tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client(isolated_db):
    """Flask test client with isolated DB."""
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


def test_api_history_list_empty(client):
    r = client.get("/api/history")
    assert r.status_code == 200
    assert r.get_json() == []


def test_api_history_list_after_scan(client):
    client.post("/api/scan/text",
                json={"text": "Your account will be blocked. Complete KYC immediately."},
                content_type="application/json")
    r = client.get("/api/history")
    assert r.status_code == 200
    rows = r.get_json()
    assert len(rows) >= 1


def test_api_history_filter_verdict(client):
    # This message triggers kyc(25)+urgency(15)+threats(25) = 65 → Dangerous
    scam_msg = (
        "URGENT: Your SBI account will be blocked. Complete KYC immediately. "
        "FIR will be filed if you do not respond."
    )
    client.post("/api/scan/text",
                json={"text": scam_msg},
                content_type="application/json")
    r_dangerous  = client.get("/api/history?verdict=Dangerous")
    r_safe       = client.get("/api/history?verdict=Safe")
    assert r_dangerous.status_code == 200
    assert r_safe.status_code      == 200
    dangerous_rows = r_dangerous.get_json()
    safe_rows      = r_safe.get_json()
    assert len(dangerous_rows) >= 1
    assert len(safe_rows)      == 0


def test_api_history_filter_type(client):
    client.post("/api/scan/text",
                json={"text": "https://bit.ly/scam"},
                content_type="application/json")
    r = client.get("/api/history?type=link")
    assert r.status_code == 200
    rows = r.get_json()
    assert all(row["input_type"] == "link" for row in rows)


def test_api_history_delete_one(client):
    # Create a scan
    client.post("/api/scan/text",
                json={"text": "Congratulations you won!"},
                content_type="application/json")
    rows   = client.get("/api/history").get_json()
    assert len(rows) >= 1
    scan_id = rows[0]["id"]

    # Delete it
    r = client.delete(f"/api/history/{scan_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["deleted"] == scan_id

    # Verify it's gone
    rows_after = client.get("/api/history").get_json()
    ids_after = [row["id"] for row in rows_after]
    assert scan_id not in ids_after


def test_api_history_delete_nonexistent(client):
    r = client.delete("/api/history/99999")
    assert r.status_code == 404


def test_api_history_delete_all(client):
    for _ in range(3):
        client.post("/api/scan/text",
                    json={"text": "Test scam message KYC urgent"},
                    content_type="application/json")
    r = client.delete("/api/history")
    assert r.status_code == 200
    data = r.get_json()
    assert data["deleted_count"] >= 1
    assert client.get("/api/history").get_json() == []


def test_api_history_stats(client):
    client.post("/api/scan/text",
                json={"text": "Your account will be blocked. Complete KYC now."},
                content_type="application/json")
    r = client.get("/api/history/stats")
    assert r.status_code == 200
    stats = r.get_json()
    assert "total"      in stats
    assert "by_verdict" in stats
    assert "by_type"    in stats
    assert "top_flags"  in stats
    assert stats["total"] >= 1


def test_api_history_preview_privacy(client):
    """The stored preview must never exceed 60 characters."""
    long_msg = "This is a very long message that exceeds sixty characters by quite a margin indeed."
    client.post("/api/scan/text",
                json={"text": long_msg},
                content_type="application/json")
    rows = client.get("/api/history").get_json()
    assert len(rows) >= 1
    assert len(rows[0]["preview"]) <= 60
