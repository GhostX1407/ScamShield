"""
test_analyzer.py – Full test suite (Parts 2 & 3).
Tests: message_rules, url_rules, lookalike, scoring,
       analyzer pipeline, QR reader, UPI parser, Flask API.
Run with:  pytest tests/test_analyzer.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.message_rules import analyse_message, detect_language
from core.url_rules import analyse_url
from core.lookalike import analyse_lookalike
from core.scoring import calculate_score, get_verdict, VERDICT_SAFE, VERDICT_SUSPICIOUS, VERDICT_DANGEROUS
from core.analyzer import analyse_text, analyse_image
from core.qr_reader import decode_qr_from_bytes, QRDecodeError
from core.upi_parser import parse_upi


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 – Language detection
# ═══════════════════════════════════════════════════════════════════════════

def test_lang_english():
    assert detect_language("Your account will be blocked. Click here to verify.") == "en"

def test_lang_hindi_script():
    assert detect_language("आपका खाता बंद हो जाएगा, तुरंत केवाईसी करें।") == "hi"

def test_lang_hinglish():
    assert detect_language("Aapka account band ho jayega, abhi kyc karo.") == "hinglish"

def test_lang_safe_english():
    assert detect_language("Hi, are we meeting at 5 pm today?") == "en"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 – Message rules: SCAM
# ═══════════════════════════════════════════════════════════════════════════

def test_msg_en_kyc_urgency():
    r = analyse_message("URGENT: Your SBI account will be blocked. Complete your KYC immediately.")
    ids = [f["id"] for f in r["flags"]]
    assert "kyc" in ids or "urgency" in ids

def test_msg_en_prize():
    r = analyse_message("Congratulations! You have WON a cash prize of ₹50,000 in our lucky draw.")
    assert "prize" in [f["id"] for f in r["flags"]]

def test_msg_en_personal_info():
    r = analyse_message("Please share your OTP and CVV to verify your account.")
    assert "personal_info" in [f["id"] for f in r["flags"]]

def test_msg_en_threats():
    r = analyse_message("Income tax notice issued. FIR will be filed if you do not call immediately.")
    assert "threats" in [f["id"] for f in r["flags"]]

def test_msg_en_money():
    r = analyse_message("Send money now. Pay ₹499 registration fee to claim your reward.")
    ids = [f["id"] for f in r["flags"]]
    assert "money" in ids or "prize" in ids

def test_msg_en_refund():
    r = analyse_message("Your refund of ₹2000 is approved. Click to claim cashback immediately.")
    assert "refund" in [f["id"] for f in r["flags"]]

def test_msg_hi_kyc():
    r = analyse_message("आपका बैंक खाता बंद हो जाएगा। तुरंत केवाईसी करें और आधार जमा करें।")
    assert len(r["flags"]) >= 1
    assert r["language"] == "hi"

def test_msg_hi_prize():
    r = analyse_message("बधाई हो! आपने लकी ड्रा में ₹1,00,000 का नकद पुरस्कार जीता।")
    assert "prize" in [f["id"] for f in r["flags"]]

def test_msg_hinglish_kyc():
    r = analyse_message("Aapka account band ho jayega. Abhi kyc karo aur aadhar do.")
    assert len(r["flags"]) >= 1
    assert r["language"] == "hinglish"

def test_msg_hinglish_prize():
    r = analyse_message("Aap lucky draw mein jeete! Inaam claim karo aur otp share karo.")
    ids = [f["id"] for f in r["flags"]]
    assert "prize" in ids or "personal_info" in ids

def test_msg_hinglish_threat():
    r = analyse_message("Police case hoga agar aapne abhi call nahi kiya. Turant call karo.")
    assert "threats" in [f["id"] for f in r["flags"]]

def test_msg_hinglish_variant_blok():
    r = analyse_message("Tumhara account blok ho jayega. Otp batao abhi.")
    assert len(r["flags"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 – Message rules: SAFE
# ═══════════════════════════════════════════════════════════════════════════

def test_msg_safe_casual():
    r = analyse_message("Hi, are we meeting at 5 pm today?")
    assert get_verdict(calculate_score(r["flags"])) == VERDICT_SAFE

def test_msg_safe_otp_from_bank():
    r = analyse_message("123456 is your OTP for SBI login. Valid for 5 minutes. Do not share.")
    assert get_verdict(calculate_score(r["flags"])) != VERDICT_DANGEROUS

def test_msg_safe_family():
    r = analyse_message("Mom, I'll be home by 8. Can you make dinner?")
    assert get_verdict(calculate_score(r["flags"])) == VERDICT_SAFE

def test_msg_safe_hindi_greeting():
    r = analyse_message("नमस्ते! कैसे हो? कल मिलते हैं।")
    assert get_verdict(calculate_score(r["flags"])) == VERDICT_SAFE


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 – URL rules
# ═══════════════════════════════════════════════════════════════════════════

def test_url_shortener():
    assert "url_shortener" in [f["id"] for f in analyse_url("https://bit.ly/abc123")]

def test_url_ip_host():
    assert "url_ip_host" in [f["id"] for f in analyse_url("http://192.168.1.1/login")]

def test_url_at_sign():
    assert "url_at_sign" in [f["id"] for f in analyse_url("http://sbi.co.in@evil.com/phish")]

def test_url_no_https():
    assert "url_no_https" in [f["id"] for f in analyse_url("http://sbi-secure-login.com/kyc")]

def test_url_suspicious_tld():
    assert "url_suspicious_tld" in [f["id"] for f in analyse_url("https://sbilogin.xyz")]

def test_url_suspicious_word_kyc():
    ids = [f["id"] for f in analyse_url("https://secure-bank-kyc-update.com/verify")]
    assert "url_suspicious_word" in ids or "url_many_hyphens" in ids

def test_url_safe_amazon():
    ids = [f["id"] for f in analyse_url("https://www.amazon.in/dp/B09XYZ")]
    assert "url_ip_host"     not in ids
    assert "url_shortener"   not in ids
    assert "url_suspicious_tld" not in ids


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 – Lookalike
# ═══════════════════════════════════════════════════════════════════════════

def test_lookalike_edit_distance_paytm():
    assert "lookalike_edit_distance" in [f["id"] for f in analyse_lookalike("https://paytrn.com/pay")]

def test_lookalike_brand_in_domain_sbi():
    assert "lookalike_brand_in_domain" in [f["id"] for f in analyse_lookalike("https://sbi-kyc-update.in")]

def test_lookalike_allowlist_sbi():
    assert analyse_lookalike("https://sbi.co.in/personal/loans") == []

def test_lookalike_allowlist_amazon():
    assert analyse_lookalike("https://www.amazon.in") == []

def test_lookalike_allowlist_hdfc():
    assert analyse_lookalike("https://www.hdfcbank.com") == []


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 – Scoring
# ═══════════════════════════════════════════════════════════════════════════

def test_score_cap():
    huge = [{"id": f"fake_{i}", "weight": 30} for i in range(10)]
    assert calculate_score(huge) == 100

def test_verdict_safe():
    assert get_verdict(0)  == VERDICT_SAFE
    assert get_verdict(29) == VERDICT_SAFE

def test_verdict_suspicious():
    assert get_verdict(30) == VERDICT_SUSPICIOUS
    assert get_verdict(59) == VERDICT_SUSPICIOUS

def test_verdict_dangerous():
    assert get_verdict(60)  == VERDICT_DANGEROUS
    assert get_verdict(100) == VERDICT_DANGEROUS


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 – Analyzer pipeline (end-to-end)
# ═══════════════════════════════════════════════════════════════════════════

def test_analyzer_url_input():
    r = analyse_text("https://bit.ly/free-iphone-claim")
    assert r["input_type"] == "link"
    assert r["verdict"] in (VERDICT_SUSPICIOUS, VERDICT_DANGEROUS)

def test_analyzer_upi_input():
    r = analyse_text("upi://pay?pa=scammer@ybl&pn=FakeRefund&am=500&tn=cashback")
    assert r["input_type"] == "upi"
    assert r["upi_details"] is not None
    assert r["upi_details"]["amount"] == "500"

def test_analyzer_message_with_embedded_url():
    r = analyse_text("Click here to claim: https://bit.ly/prize99")
    assert r["input_type"] == "message"
    assert len(r["extracted_links"]) >= 1
    assert r["verdict"] in (VERDICT_SUSPICIOUS, VERDICT_DANGEROUS)

def test_analyzer_safe_message():
    r = analyse_text("Hi, dinner at 7?")
    assert r["verdict"] == VERDICT_SAFE

def test_analyzer_empty_input():
    r = analyse_text("")
    assert r["score"] == 0

def test_analyzer_xss_input():
    """XSS content must not crash the analyser."""
    r = analyse_text("<script>alert(1)</script>")
    assert "verdict" in r   # must return a valid result

def test_analyzer_very_long_input():
    """10k character input must not crash."""
    long_text = "click here " * 910
    r = analyse_text(long_text)
    assert r["score"] <= 100


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 – QR reader
# ═══════════════════════════════════════════════════════════════════════════

_QR_DIR = Path(__file__).parent / "qr_samples"

def test_qr_normal_url():
    img_bytes = (_QR_DIR / "normal_url.png").read_bytes()
    decoded = decode_qr_from_bytes(img_bytes)
    assert "google.com" in decoded

def test_qr_shortener():
    img_bytes = (_QR_DIR / "shortener.png").read_bytes()
    decoded = decode_qr_from_bytes(img_bytes)
    assert "bit.ly" in decoded

def test_qr_upi():
    img_bytes = (_QR_DIR / "upi_scam.png").read_bytes()
    decoded = decode_qr_from_bytes(img_bytes)
    assert decoded.startswith("upi://")

def test_qr_lookalike_sbi():
    img_bytes = (_QR_DIR / "lookalike_sbi.png").read_bytes()
    decoded = decode_qr_from_bytes(img_bytes)
    assert "sbi-kyc-login" in decoded

def test_qr_bad_image_bytes():
    with pytest.raises(QRDecodeError):
        decode_qr_from_bytes(b"this is not an image")

def test_qr_empty_bytes():
    with pytest.raises(QRDecodeError):
        decode_qr_from_bytes(b"")

def test_qr_image_no_qr_code():
    """A valid image that contains no QR code must raise QRDecodeError."""
    from PIL import Image
    import io
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    with pytest.raises(QRDecodeError):
        decode_qr_from_bytes(buf.getvalue())

def test_qr_analyse_image_pipeline():
    """analyse_image must return a full result dict for a valid QR."""
    img_bytes = (_QR_DIR / "upi_scam.png").read_bytes()
    r = analyse_image(img_bytes)
    assert r["input_type"] == "qr"
    assert r["verdict"] in (VERDICT_SAFE, VERDICT_SUSPICIOUS, VERDICT_DANGEROUS)

def test_qr_analyse_image_bad():
    """analyse_image must return error key, not crash, for a bad image."""
    r = analyse_image(b"not an image")
    assert "error" in r


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9 – UPI parser
# ═══════════════════════════════════════════════════════════════════════════

def test_upi_prefilled_amount():
    r = parse_upi("upi://pay?pa=scammer@ybl&pn=FakeAgent&am=500&tn=cashback")
    ids = [f["id"] for f in r["flags"]]
    assert "upi_prefilled_amount" in ids

def test_upi_scam_note():
    r = parse_upi("upi://pay?pa=x@ybl&pn=X&tn=claim your refund prize")
    ids = [f["id"] for f in r["flags"]]
    assert "upi_scam_note" in ids

def test_upi_always_has_core_warning():
    r = parse_upi("upi://pay?pa=shop@oksbi&pn=Shop&am=0")
    assert any("SEND money" in w for w in r["warnings"])

def test_upi_fields_parsed():
    r = parse_upi("upi://pay?pa=merchant@oksbi&pn=MyShop&am=100&tn=purchase")
    assert r["payee_address"] == "merchant@oksbi"
    assert r["payee_name"]    == "MyShop"
    assert r["amount"]        == "100"
    assert r["note"]          == "purchase"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10 – Test-cases.json driven tests
# ═══════════════════════════════════════════════════════════════════════════

_CASES_PATH = Path(__file__).parent / "test_cases.json"
with open(_CASES_PATH, encoding="utf-8") as _cf:
    _CASES = json.load(_cf)


@pytest.mark.parametrize("case", _CASES, ids=[f"case_{c['id']}" for c in _CASES])
def test_case_verdict(case):
    """Each labelled test case must produce the expected verdict or better."""
    result = analyse_text(case["input"])
    expected = case["expected_verdict"]
    actual   = result["verdict"]

    # Safe cases: must be exactly Safe
    if expected == VERDICT_SAFE:
        assert actual == VERDICT_SAFE, (
            f"Case {case['id']} ({case['notes']}): "
            f"expected Safe but got {actual} (score={result['score']})"
        )
    else:
        # Scam cases: must be Suspicious or Dangerous (not Safe)
        assert actual != VERDICT_SAFE, (
            f"Case {case['id']} ({case['notes']}): "
            f"expected {expected} but got Safe (score={result['score']})"
        )


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11 – Flask API tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c

def test_api_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"

def test_api_scan_text_scam(client):
    r = client.post("/api/scan/text",
                    json={"text": "Your account will be blocked. Complete KYC now."},
                    content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["verdict"] in (VERDICT_SUSPICIOUS, VERDICT_DANGEROUS)
    assert "flags" in data

def test_api_scan_text_safe(client):
    r = client.post("/api/scan/text",
                    json={"text": "Hi, see you tomorrow!"},
                    content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["verdict"] == VERDICT_SAFE

def test_api_scan_text_empty(client):
    r = client.post("/api/scan/text",
                    json={"text": ""},
                    content_type="application/json")
    assert r.status_code == 400

def test_api_scan_text_missing_field(client):
    r = client.post("/api/scan/text",
                    json={},
                    content_type="application/json")
    assert r.status_code == 400

def test_api_scan_image_no_qr(client):
    """Upload a white PNG with no QR code; should return error key."""
    from PIL import Image
    import io
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    r = client.post("/api/scan/image",
                    data={"image": (buf, "test.png", "image/png")},
                    content_type="multipart/form-data")
    assert r.status_code == 200
    data = r.get_json()
    assert "error" in data

def test_api_scan_image_bad_mimetype(client):
    """Upload a text file pretending to be an image; should return 415."""
    import io
    r = client.post("/api/scan/image",
                    data={"image": (io.BytesIO(b"hello"), "test.txt", "text/plain")},
                    content_type="multipart/form-data")
    assert r.status_code == 415

def test_api_scan_image_valid_qr(client):
    """Upload a real QR code image; should decode and return verdict."""
    img_bytes = (_QR_DIR / "upi_scam.png").read_bytes()
    import io
    r = client.post("/api/scan/image",
                    data={"image": (io.BytesIO(img_bytes), "upi.png", "image/png")},
                    content_type="multipart/form-data")
    assert r.status_code == 200
    data = r.get_json()
    assert data["input_type"] == "qr"
    assert "verdict" in data

def test_api_history_list(client):
    r = client.get("/api/history")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)

def test_api_history_stats(client):
    r = client.get("/api/history/stats")
    assert r.status_code == 200
    data = r.get_json()
    assert "total" in data
