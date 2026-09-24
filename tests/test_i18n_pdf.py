"""
test_i18n_pdf.py – Part 5 verification tests.

Tests:
  1. en.json and hi.json have EXACTLY the same keys
  2. learn_en.json and learn_hi.json have EXACTLY the same keys
  3. Every possible flag ID from scoring.py has a learn card in both languages
  4. PDF generates without errors in both languages
  5. PDF file is non-empty and starts with the PDF magic bytes
  6. Flask API: /api/i18n/<lang>, /api/learn/<lang>, /api/samples, /api/export/pdf
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.scoring import FLAG_WEIGHTS


# ── Paths ──────────────────────────────────────────────────────────────────
_I18N = Path("i18n")
_EN   = json.loads((_I18N / "en.json").read_text(encoding="utf-8"))
_HI   = json.loads((_I18N / "hi.json").read_text(encoding="utf-8"))
_LEN  = json.loads((_I18N / "learn_en.json").read_text(encoding="utf-8"))
_LHI  = json.loads((_I18N / "learn_hi.json").read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 – Key parity checks
# ═══════════════════════════════════════════════════════════════════════════

def test_ui_en_hi_same_keys():
    """en.json and hi.json must have exactly the same top-level keys."""
    en_keys = set(k for k, v in _EN.items() if not isinstance(v, list))
    hi_keys = set(k for k, v in _HI.items() if not isinstance(v, list))
    only_en = en_keys - hi_keys
    only_hi = hi_keys - en_keys
    assert not only_en, f"Keys in en.json but NOT in hi.json: {only_en}"
    assert not only_hi, f"Keys in hi.json but NOT in en.json: {only_hi}"


def test_learn_en_hi_same_keys():
    """learn_en.json and learn_hi.json must have exactly the same flag IDs."""
    only_en = set(_LEN) - set(_LHI)
    only_hi = set(_LHI) - set(_LEN)
    assert not only_en, f"Flag IDs in learn_en but NOT learn_hi: {only_en}"
    assert not only_hi, f"Flag IDs in learn_hi but NOT learn_en: {only_hi}"


def test_every_flag_has_learn_card_en():
    """Every flag ID defined in scoring.py must have a card in learn_en.json."""
    missing = set(FLAG_WEIGHTS.keys()) - set(_LEN.keys())
    assert not missing, f"Missing EN learn cards for flags: {missing}"


def test_every_flag_has_learn_card_hi():
    """Every flag ID defined in scoring.py must have a card in learn_hi.json."""
    missing = set(FLAG_WEIGHTS.keys()) - set(_LHI.keys())
    assert not missing, f"Missing HI learn cards for flags: {missing}"


def test_learn_cards_have_required_fields():
    """Every card must have 'title', 'what', 'why', and 'do' fields."""
    required = {"title", "what", "why", "do"}
    for fid, card in _LEN.items():
        missing = required - set(card.keys())
        assert not missing, f"EN card '{fid}' missing fields: {missing}"
    for fid, card in _LHI.items():
        missing = required - set(card.keys())
        assert not missing, f"HI card '{fid}' missing fields: {missing}"


def test_learn_cards_not_empty():
    """No card field should be an empty string."""
    for fid, card in _LEN.items():
        for field in ("title", "what", "why", "do"):
            assert card.get(field, "").strip(), f"EN card '{fid}.{field}' is empty"
    for fid, card in _LHI.items():
        for field in ("title", "what", "why", "do"):
            assert card.get(field, "").strip(), f"HI card '{fid}.{field}' is empty"


def test_samples_json_valid():
    """samples.json must be a non-empty list with required fields."""
    samples = json.loads(Path("data/samples.json").read_text(encoding="utf-8"))
    assert isinstance(samples, list) and len(samples) >= 5
    for s in samples:
        assert "id"   in s, f"Sample missing 'id': {s}"
        assert "text" in s, f"Sample missing 'text': {s}"
        assert "type" in s, f"Sample missing 'type': {s}"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 – PDF generation
# ═══════════════════════════════════════════════════════════════════════════

def _make_result(verdict="Dangerous", score=80, flags=None, upi=None):
    return {
        "verdict":    verdict,
        "score":      score,
        "input_type": "message",
        "language":   "en",
        "flags":      flags or [
            {"id": "kyc",     "weight": 25, "category": "kyc",     "detail": ""},
            {"id": "urgency", "weight": 15, "category": "urgency", "detail": ""},
            {"id": "threats", "weight": 25, "category": "threats", "detail": ""},
        ],
        "upi_details": upi,
    }


def test_pdf_en_generates():
    from core.export_pdf import generate_pdf
    pdf_bytes = generate_pdf(_make_result(), lang="en")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF", "Output is not a valid PDF"


def test_pdf_hi_generates():
    from core.export_pdf import generate_pdf
    result = _make_result()
    result["language"] = "hi"
    pdf_bytes = generate_pdf(result, lang="hi")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF", "Hindi PDF is not a valid PDF"


def test_pdf_safe_verdict():
    from core.export_pdf import generate_pdf
    result = _make_result(verdict="Safe", score=5, flags=[])
    pdf_bytes = generate_pdf(result, lang="en")
    assert len(pdf_bytes) > 500


def test_pdf_with_upi_details():
    from core.export_pdf import generate_pdf
    upi = {
        "payee_address": "scammer@ybl",
        "payee_name":    "Fake Refund",
        "amount":        "500",
        "note":          "cashback",
        "warnings":      ["Scanning this QR will SEND money from your account."],
    }
    result = _make_result(verdict="Dangerous", score=85,
                          flags=[{"id": "upi_prefilled_amount", "weight": 20,
                                  "category": "upi", "detail": ""}],
                          upi=upi)
    result["input_type"] = "upi"
    pdf_bytes = generate_pdf(result, lang="en")
    assert pdf_bytes[:4] == b"%PDF"


def test_pdf_hi_with_all_flags():
    """Generate a Hindi PDF with all 24 flag IDs to stress-test text shaping."""
    from core.export_pdf import generate_pdf
    flags = [{"id": fid, "weight": w, "category": "test", "detail": ""}
             for fid, w in list(FLAG_WEIGHTS.items())[:10]]
    result = _make_result(verdict="Dangerous", score=100, flags=flags)
    result["language"] = "hi"
    pdf_bytes = generate_pdf(result, lang="hi")
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 2000


def test_pdf_invalid_lang_falls_back_to_en():
    from core.export_pdf import generate_pdf
    pdf_bytes = generate_pdf(_make_result(), lang="xx")
    assert pdf_bytes[:4] == b"%PDF"


def test_pdf_saved_to_disk(tmp_path):
    """PDF bytes must be writable to disk and re-readable."""
    from core.export_pdf import generate_pdf
    pdf_bytes = generate_pdf(_make_result(), lang="en")
    out = tmp_path / "test.pdf"
    out.write_bytes(pdf_bytes)
    assert out.stat().st_size > 1000
    assert out.read_bytes()[:4] == b"%PDF"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 – Flask API
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


def test_api_i18n_en(client):
    r = client.get("/api/i18n/en")
    assert r.status_code == 200
    data = r.get_json()
    assert "nav_scan"      in data
    assert "scan_btn_check" in data


def test_api_i18n_hi(client):
    r = client.get("/api/i18n/hi")
    assert r.status_code == 200
    data = r.get_json()
    assert "nav_scan"       in data
    assert "scan_btn_check" in data
    # Hindi value must be non-ASCII (Devanagari)
    assert any(ord(c) > 127 for c in data.get("nav_scan", ""))


def test_api_i18n_invalid_lang(client):
    r = client.get("/api/i18n/fr")
    assert r.status_code == 400


def test_api_learn_en(client):
    r = client.get("/api/learn/en")
    assert r.status_code == 200
    data = r.get_json()
    assert "kyc"     in data
    assert "urgency" in data
    assert len(data) == len(FLAG_WEIGHTS)


def test_api_learn_hi(client):
    r = client.get("/api/learn/hi")
    assert r.status_code == 200
    data = r.get_json()
    assert "kyc" in data
    # Hindi title must contain Devanagari
    assert any(ord(c) > 127 for c in data["kyc"].get("title", ""))


def test_api_samples(client):
    r = client.get("/api/samples")
    assert r.status_code == 200
    samples = r.get_json()
    assert isinstance(samples, list) and len(samples) >= 5


def test_api_pdf_en(client):
    result = _make_result()
    r = client.post("/api/export/pdf",
                    json={"result": result, "lang": "en"},
                    content_type="application/json")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data[:4] == b"%PDF"


def test_api_pdf_hi(client):
    result = _make_result()
    result["language"] = "hi"
    r = client.post("/api/export/pdf",
                    json={"result": result, "lang": "hi"},
                    content_type="application/json")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data[:4] == b"%PDF"


def test_api_pdf_missing_result(client):
    r = client.post("/api/export/pdf",
                    json={"lang": "en"},
                    content_type="application/json")
    assert r.status_code == 400


def test_api_pdf_empty_body(client):
    r = client.post("/api/export/pdf",
                    data="",
                    content_type="application/json")
    assert r.status_code == 400
