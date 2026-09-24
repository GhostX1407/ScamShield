"""
lookalike.py – Brand lookalike domain detection.

Checks for:
  (a) edit distance ≤ 2 from a known brand domain (e.g. paytrn.com)
  (b) brand name embedded in a different domain (e.g. sbi-kyc-update.in)
  (c) homoglyph character swaps (rn→m, 0→o, 1→l, etc.)

The allowlist in brands.json is always checked FIRST — real brand domains
are NEVER flagged.

tldextract is configured to use its bundled snapshot only (no network calls).
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import tldextract
from rapidfuzz.distance import Levenshtein

from core.scoring import FLAG_WEIGHTS, FLAG_CATEGORIES

# ── Configure tldextract to work fully offline ─────────────────────────────
_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=None)   # bundled snapshot only

# ── Load brand data ────────────────────────────────────────────────────────
_DATA = Path(__file__).parent.parent / "data"

with open(_DATA / "brands.json", encoding="utf-8") as _f:
    _BRAND_DATA: list[dict] = json.load(_f)["brands"]

# Build two look-up structures:
#   _ALLOWLIST  – set of all known-good registered domains (e.g. "sbi.co.in")
#   _BRAND_MAP  – { brand_name_lower: [registered_domain, ...] }
_ALLOWLIST: set[str] = set()
_BRAND_MAP: dict[str, list[str]] = {}

for _b in _BRAND_DATA:
    _brand_key = _b["name"].lower().replace(" ", "")
    _brand_registered = []
    for _d in _b["domains"]:
        ext = _EXTRACTOR(_d)
        if ext.registered_domain:
            _ALLOWLIST.add(ext.registered_domain.lower())
            _brand_registered.append(ext.registered_domain.lower())
    _BRAND_MAP[_brand_key] = _brand_registered


# ── Homoglyph normalisation ────────────────────────────────────────────────
_HOMOGLYPHS = str.maketrans({
    "0": "o", "1": "l", "3": "e", "5": "s", "8": "b",
    "@": "a", "$": "s",
})

# Common look-alike letter sequences to collapse before comparison
_GLYPH_PATTERNS = [
    (re.compile(r"rn"), "m"),
    (re.compile(r"vv"), "w"),
    (re.compile(r"cl"), "d"),
    (re.compile(r"li"), "h"),
    (re.compile(r"lj"), "h"),
]


def _normalise_glyph(s: str) -> str:
    s = s.lower().translate(_HOMOGLYPHS)
    for pattern, replacement in _GLYPH_PATTERNS:
        s = pattern.sub(replacement, s)
    return s


# ── Helpers ────────────────────────────────────────────────────────────────

def _extract_registered(url_or_host: str) -> str | None:
    """Return the registered domain (e.g. 'sbi-kyc.in') from a URL or hostname."""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", url_or_host):
        url_or_host = "http://" + url_or_host
    try:
        parsed = urlparse(url_or_host)
        host = parsed.hostname or ""
        ext = _EXTRACTOR(host)
        return ext.registered_domain.lower() if ext.registered_domain else None
    except Exception:
        return None


def _make_flag(flag_id: str, detail: str = "") -> dict:
    return {
        "id":       flag_id,
        "weight":   FLAG_WEIGHTS.get(flag_id, 10),
        "category": FLAG_CATEGORIES.get(flag_id, "lookalike"),
        "spans":    [],
        "detail":   detail,
    }


# ── Individual checks ──────────────────────────────────────────────────────

def _check_edit_distance(registered: str) -> dict | None:
    """
    Flag if the registered domain is within edit distance 2 of any known brand
    domain — but is NOT in the allowlist.
    """
    for brand_key, brand_domains in _BRAND_MAP.items():
        for bd in brand_domains:
            if registered == bd:
                return None   # exact match → it's in the allowlist, already cleared
            dist = Levenshtein.distance(registered, bd, score_cutoff=2)
            if dist is not None and dist <= 2:
                return _make_flag(
                    "lookalike_edit_distance",
                    f"looks like {bd}",
                )
    return None


def _check_brand_in_domain(registered: str) -> dict | None:
    """
    Flag if a brand name appears as a substring of the registered domain but
    the domain itself is not in the allowlist.
    """
    domain_clean = re.sub(r"[.\-]", "", registered.lower())
    for brand_key, brand_domains in _BRAND_MAP.items():
        if brand_key in domain_clean:
            # Make sure it's not a real brand domain
            if registered not in _ALLOWLIST:
                return _make_flag(
                    "lookalike_brand_in_domain",
                    f"contains brand name '{brand_key}'",
                )
    return None


def _check_homoglyph(registered: str) -> dict | None:
    """
    Normalise the domain with glyph substitutions, then compare to brand domains.
    """
    norm = _normalise_glyph(registered.split(".")[0])   # only the SLD part
    for brand_key, brand_domains in _BRAND_MAP.items():
        for bd in brand_domains:
            bd_norm = _normalise_glyph(bd.split(".")[0])
            if norm == bd_norm and registered not in _ALLOWLIST:
                return _make_flag(
                    "lookalike_homoglyph",
                    f"looks like {bd} via character substitution",
                )
    return None


# ── Public API ─────────────────────────────────────────────────────────────

def analyse_lookalike(url_or_host: str) -> list[dict]:
    """
    Run all lookalike checks against a URL or hostname.
    Returns a list of FLAG dicts (empty if clean or on allowlist).
    """
    registered = _extract_registered(url_or_host)
    if not registered:
        return []

    # If the domain is on the allowlist, skip everything
    if registered in _ALLOWLIST:
        return []

    flags: list[dict] = []

    hit = _check_edit_distance(registered)
    if hit:
        flags.append(hit)
        return flags   # edit distance match is definitive — no need to check further

    hit = _check_brand_in_domain(registered)
    if hit:
        flags.append(hit)

    hit = _check_homoglyph(registered)
    if hit:
        flags.append(hit)

    return flags
