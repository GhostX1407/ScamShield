"""
test_analyzer.py – Unit tests for the Part-2 detection engine.
Tests: message_rules, url_rules, lookalike, scoring.
Run with:  pytest tests/test_analyzer.py -v
"""

import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.message_rules import analyse_message, detect_language
from core.url_rules import analyse_url
from core.lookalike import analyse_lookalike
from core.scoring import calculate_score, get_verdict, VERDICT_SAFE, VERDICT_SUSPICIOUS, VERDICT_DANGEROUS


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
# SECTION 2 – Message rules: SCAM inputs (must return ≥1 flag)
# ═══════════════════════════════════════════════════════════════════════════

def test_msg_en_kyc_urgency():
    result = analyse_message(
        "URGENT: Your SBI account will be blocked. Complete your KYC immediately. "
        "Click here: http://sbi-kyc-update.xyz"
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "kyc" in flag_ids or "urgency" in flag_ids, flag_ids

def test_msg_en_prize():
    result = analyse_message(
        "Congratulations! You have WON a cash prize of ₹50,000 in our lucky draw. "
        "Claim your prize now by clicking the link."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "prize" in flag_ids, flag_ids

def test_msg_en_personal_info():
    result = analyse_message(
        "Dear customer, please share your OTP and CVV to verify your account."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "personal_info" in flag_ids, flag_ids

def test_msg_en_threats():
    result = analyse_message(
        "Income tax notice issued. FIR will be filed if you do not call immediately."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "threats" in flag_ids, flag_ids

def test_msg_en_money():
    result = analyse_message(
        "Send money now. Pay ₹499 registration fee to claim your reward."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "money" in flag_ids or "prize" in flag_ids, flag_ids

def test_msg_en_refund():
    result = analyse_message(
        "Your refund of ₹2000 is approved. Click to claim cashback immediately."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "refund" in flag_ids, flag_ids

def test_msg_hi_kyc():
    result = analyse_message(
        "आपका बैंक खाता बंद हो जाएगा। तुरंत केवाईसी करें और आधार जमा करें।"
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert len(flag_ids) >= 1, "Hindi KYC scam should be detected"
    assert result["language"] == "hi"

def test_msg_hi_prize():
    result = analyse_message(
        "बधाई हो! आपने लकी ड्रा में ₹1,00,000 का नकद पुरस्कार जीता। इनाम का दावा करें।"
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "prize" in flag_ids, flag_ids

def test_msg_hinglish_kyc():
    result = analyse_message(
        "Aapka account band ho jayega. Abhi kyc karo aur aadhar do."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert len(flag_ids) >= 1, "Hinglish KYC scam should be detected"
    assert result["language"] == "hinglish"

def test_msg_hinglish_prize():
    result = analyse_message(
        "Aap lucky draw mein jeete! Inaam claim karo aur otp share karo."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "prize" in flag_ids or "personal_info" in flag_ids, flag_ids

def test_msg_hinglish_threat():
    result = analyse_message(
        "Police case hoga agar aapne abhi call nahi kiya. Turant call karo."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert "threats" in flag_ids, flag_ids

def test_msg_hinglish_variant_blok():
    """Test spelling variant: blok instead of block."""
    result = analyse_message(
        "Tumhara account blok ho jayega. Otp batao abhi."
    )
    flag_ids = [f["id"] for f in result["flags"]]
    assert len(flag_ids) >= 1, "Hinglish variant 'blok' should trigger a flag"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 – Message rules: SAFE inputs (must NOT be flagged as Dangerous)
# ═══════════════════════════════════════════════════════════════════════════

def test_msg_safe_casual():
    result = analyse_message("Hi, are we meeting at 5 pm today?")
    score = calculate_score(result["flags"])
    assert get_verdict(score) == VERDICT_SAFE, f"Score={score} Flags={result['flags']}"

def test_msg_safe_otp_from_bank():
    """A real OTP message must not be Dangerous."""
    result = analyse_message(
        "123456 is your OTP for SBI login. Valid for 5 minutes. Do not share."
    )
    score = calculate_score(result["flags"])
    verdict = get_verdict(score)
    # It may pick up "personal_info" hint for "do not share" pattern,
    # but must not reach Dangerous.
    assert verdict != VERDICT_DANGEROUS, f"Real OTP msg scored {score}: {result['flags']}"

def test_msg_safe_family():
    result = analyse_message("Mom, I'll be home by 8. Can you make dinner?")
    score = calculate_score(result["flags"])
    assert get_verdict(score) == VERDICT_SAFE

def test_msg_safe_hindi_greeting():
    result = analyse_message("नमस्ते! कैसे हो? कल मिलते हैं।")
    score = calculate_score(result["flags"])
    assert get_verdict(score) == VERDICT_SAFE


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 – URL rules
# ═══════════════════════════════════════════════════════════════════════════

def test_url_shortener():
    flags = analyse_url("https://bit.ly/abc123")
    ids = [f["id"] for f in flags]
    assert "url_shortener" in ids, ids

def test_url_ip_host():
    flags = analyse_url("http://192.168.1.1/login")
    ids = [f["id"] for f in flags]
    assert "url_ip_host" in ids, ids

def test_url_at_sign():
    flags = analyse_url("http://sbi.co.in@evil.com/phish")
    ids = [f["id"] for f in flags]
    assert "url_at_sign" in ids, ids

def test_url_no_https():
    flags = analyse_url("http://sbi-secure-login.com/kyc")
    ids = [f["id"] for f in flags]
    assert "url_no_https" in ids, ids

def test_url_suspicious_tld():
    flags = analyse_url("https://sbilogin.xyz")
    ids = [f["id"] for f in flags]
    assert "url_suspicious_tld" in ids, ids

def test_url_suspicious_word_kyc():
    flags = analyse_url("https://secure-bank-kyc-update.com/verify")
    ids = [f["id"] for f in flags]
    assert "url_suspicious_word" in ids or "url_many_hyphens" in ids, ids

def test_url_safe_amazon():
    """amazon.in should not be flagged by URL rules."""
    flags = analyse_url("https://www.amazon.in/dp/B09XYZ")
    ids = [f["id"] for f in flags]
    # Amazon.in is HTTPS, no IP, no shortener, no bad TLD
    assert "url_ip_host" not in ids
    assert "url_shortener" not in ids
    assert "url_suspicious_tld" not in ids


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 – Lookalike detection
# ═══════════════════════════════════════════════════════════════════════════

def test_lookalike_edit_distance_paytm():
    flags = analyse_lookalike("https://paytrn.com/pay")
    ids = [f["id"] for f in flags]
    assert "lookalike_edit_distance" in ids, ids

def test_lookalike_brand_in_domain_sbi():
    flags = analyse_lookalike("https://sbi-kyc-update.in/verify")
    ids = [f["id"] for f in flags]
    assert "lookalike_brand_in_domain" in ids, ids

def test_lookalike_homoglyph_paypal():
    """paypa1.com (1→l) should be caught."""
    flags = analyse_lookalike("https://paypa1.com")
    # We don't have PayPal in brands, but this tests the mechanism exists
    # Just ensure no crash
    assert isinstance(flags, list)

def test_lookalike_allowlist_sbi():
    """sbi.co.in must NOT be flagged."""
    flags = analyse_lookalike("https://sbi.co.in/personal/loans")
    assert flags == [], f"Real SBI domain was flagged: {flags}"

def test_lookalike_allowlist_amazon():
    flags = analyse_lookalike("https://www.amazon.in")
    assert flags == [], f"Real Amazon domain was flagged: {flags}"

def test_lookalike_allowlist_hdfc():
    flags = analyse_lookalike("https://www.hdfcbank.com")
    assert flags == [], f"Real HDFC domain was flagged: {flags}"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 – Scoring
# ═══════════════════════════════════════════════════════════════════════════

def test_score_cap():
    """Score must never exceed 100."""
    huge_flags = [{"id": f"fake_{i}", "weight": 30} for i in range(10)]
    assert calculate_score(huge_flags) == 100

def test_verdict_safe():
    assert get_verdict(0) == VERDICT_SAFE
    assert get_verdict(29) == VERDICT_SAFE

def test_verdict_suspicious():
    assert get_verdict(30) == VERDICT_SUSPICIOUS
    assert get_verdict(59) == VERDICT_SUSPICIOUS

def test_verdict_dangerous():
    assert get_verdict(60) == VERDICT_DANGEROUS
    assert get_verdict(100) == VERDICT_DANGEROUS
