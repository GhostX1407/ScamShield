"""
scoring.py – Single source of truth for all flag weights,
             score capping, and verdict thresholds.
"""

# ── Verdict thresholds ─────────────────────────────────────────────────────
VERDICT_SAFE        = "Safe"
VERDICT_SUSPICIOUS  = "Suspicious"
VERDICT_DANGEROUS   = "Dangerous"

THRESHOLD_SAFE       = 29   # score 0-29  → Safe
THRESHOLD_SUSPICIOUS = 59   # score 30-59 → Suspicious
                             # score 60+   → Dangerous

SCORE_CAP = 100


# ── Flag weights (override per-flag defaults from data JSON) ───────────────
# These are the canonical weights used everywhere; the JSON files carry the
# same values for documentation but scoring.py always wins.
FLAG_WEIGHTS: dict[str, int] = {
    # Message rule flags
    "urgency":        15,
    "money":          20,
    "kyc":            25,
    "prize":          30,
    "refund":         18,
    "threats":        25,
    "personal_info":  22,
    "suspicious_link": 15,
    # URL rule flags
    "url_shortener":       20,
    "url_ip_host":         25,
    "url_at_sign":         25,
    "url_punycode":        20,
    "url_too_many_subs":   15,
    "url_very_long":       10,
    "url_no_https":        15,
    "url_suspicious_tld":  20,
    "url_many_hyphens":    15,
    "url_suspicious_word": 20,
    # Lookalike flags
    "lookalike_edit_distance": 30,
    "lookalike_brand_in_domain": 25,
    "lookalike_homoglyph":      25,
    # UPI flags
    "upi_prefilled_amount": 20,
    "upi_scam_note":        25,
    "upi_name_mismatch":    15,
}

# Categories (used for colour-coding in the frontend)
FLAG_CATEGORIES: dict[str, str] = {
    "urgency":               "urgency",
    "money":                 "money",
    "kyc":                   "kyc",
    "prize":                 "prize",
    "refund":                "refund",
    "threats":               "threats",
    "personal_info":         "personal_info",
    "suspicious_link":       "suspicious_link",
    "url_shortener":         "url",
    "url_ip_host":           "url",
    "url_at_sign":           "url",
    "url_punycode":          "url",
    "url_too_many_subs":     "url",
    "url_very_long":         "url",
    "url_no_https":          "url",
    "url_suspicious_tld":    "url",
    "url_many_hyphens":      "url",
    "url_suspicious_word":   "url",
    "lookalike_edit_distance":   "lookalike",
    "lookalike_brand_in_domain": "lookalike",
    "lookalike_homoglyph":       "lookalike",
    "upi_prefilled_amount":  "upi",
    "upi_scam_note":         "upi",
    "upi_name_mismatch":     "upi",
}


def calculate_score(flags: list[dict]) -> int:
    """Sum flag weights and cap at SCORE_CAP."""
    total = sum(FLAG_WEIGHTS.get(f["id"], f.get("weight", 0)) for f in flags)
    return min(total, SCORE_CAP)


def get_verdict(score: int) -> str:
    if score <= THRESHOLD_SAFE:
        return VERDICT_SAFE
    if score <= THRESHOLD_SUSPICIOUS:
        return VERDICT_SUSPICIOUS
    return VERDICT_DANGEROUS
