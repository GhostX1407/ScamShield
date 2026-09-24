"""
url_rules.py – URL-based scam detection rules.

Each rule returns a FLAG dict or None.
The public entry point is analyse_url(url: str) -> list[dict].
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from core.scoring import FLAG_WEIGHTS, FLAG_CATEGORIES

# ── Load shortener list ────────────────────────────────────────────────────
_DATA = Path(__file__).parent.parent / "data"

with open(_DATA / "shorteners.json", encoding="utf-8") as _f:
    _SHORTENERS: set[str] = set(json.load(_f)["shorteners"])

# ── Constants ──────────────────────────────────────────────────────────────
_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".icu", ".club", ".online", ".site", ".live",
    ".click", ".loan", ".work", ".bid", ".win", ".gq", ".cf",
    ".ml", ".ga", ".tk", ".buzz", ".monster", ".cfd", ".fun",
    ".cheap", ".info", ".biz",
}

_SUSPICIOUS_PATH_WORDS = {
    "login", "signin", "verify", "kyc", "update", "secure", "account",
    "confirm", "validation", "authenticate", "banking", "netbanking",
    "otp", "password", "credential", "reward", "prize", "claim",
    "free", "cashback", "refund", "payment", "pay", "wallet",
}

_MAX_SUBDOMAINS   = 3    # more than this is suspicious
_MAX_URL_LENGTH   = 100  # characters
_MAX_HYPHENS      = 3    # in the registered domain part


def _make_flag(flag_id: str, extra: dict | None = None) -> dict:
    f = {
        "id":       flag_id,
        "weight":   FLAG_WEIGHTS.get(flag_id, 10),
        "category": FLAG_CATEGORIES.get(flag_id, "url"),
        "spans":    [],
    }
    if extra:
        f.update(extra)
    return f


def _is_ip_host(hostname: str) -> bool:
    ipv4 = re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname)
    ipv6 = hostname.startswith("[")
    return bool(ipv4 or ipv6)


def _count_subdomains(hostname: str) -> int:
    parts = hostname.rstrip(".").split(".")
    # registered domain = last two parts (or more for co.in, gov.in etc.)
    return max(0, len(parts) - 2)


# ── Individual rule functions ──────────────────────────────────────────────

def _rule_shortener(parsed) -> dict | None:
    host = parsed.netloc.lstrip("www.").lower()
    if host in _SHORTENERS:
        return _make_flag("url_shortener")
    return None


def _rule_ip_host(parsed) -> dict | None:
    if _is_ip_host(parsed.hostname or ""):
        return _make_flag("url_ip_host")
    return None


def _rule_at_sign(url: str) -> dict | None:
    if "@" in urlparse(url).netloc:
        return _make_flag("url_at_sign")
    return None


def _rule_punycode(parsed) -> dict | None:
    host = parsed.hostname or ""
    if "xn--" in host:
        return _make_flag("url_punycode")
    return None


def _rule_too_many_subdomains(parsed) -> dict | None:
    host = parsed.hostname or ""
    if _count_subdomains(host) > _MAX_SUBDOMAINS:
        return _make_flag("url_too_many_subs")
    return None


def _rule_very_long(url: str) -> dict | None:
    if len(url) > _MAX_URL_LENGTH:
        return _make_flag("url_very_long")
    return None


def _rule_no_https(parsed) -> dict | None:
    if parsed.scheme and parsed.scheme.lower() != "https":
        return _make_flag("url_no_https")
    return None


def _rule_suspicious_tld(parsed) -> dict | None:
    host = parsed.hostname or ""
    for tld in _SUSPICIOUS_TLDS:
        if host.endswith(tld):
            return _make_flag("url_suspicious_tld")
    return None


def _rule_many_hyphens(parsed) -> dict | None:
    host = parsed.hostname or ""
    # count hyphens in the main registered domain (not subdomains)
    parts = host.split(".")
    domain_part = parts[-2] if len(parts) >= 2 else host
    if domain_part.count("-") >= _MAX_HYPHENS:
        return _make_flag("url_many_hyphens")
    return None


def _rule_suspicious_path_word(parsed) -> dict | None:
    path_and_query = (parsed.path + " " + (parsed.query or "")).lower()
    # also check the full hostname
    full = (parsed.hostname or "") + " " + path_and_query
    for word in _SUSPICIOUS_PATH_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", full):
            return _make_flag("url_suspicious_word")
    return None


# ── Public API ─────────────────────────────────────────────────────────────

def analyse_url(url: str) -> list[dict]:
    """
    Run all URL rules against url.
    Returns list of FLAG dicts (may be empty for a clean URL).
    """
    url = url.strip()

    # Ensure the URL has a scheme so urlparse works correctly
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", url):
        url = "http://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        return []

    if not parsed.hostname:
        return []

    flags: list[dict] = []
    rules = [
        _rule_shortener(parsed),
        _rule_ip_host(parsed),
        _rule_at_sign(url),
        _rule_punycode(parsed),
        _rule_too_many_subdomains(parsed),
        _rule_very_long(url),
        _rule_no_https(parsed),
        _rule_suspicious_tld(parsed),
        _rule_many_hyphens(parsed),
        _rule_suspicious_path_word(parsed),
    ]
    flags = [r for r in rules if r is not None]
    return flags
