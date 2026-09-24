"""
message_rules.py – Keyword/pattern detection for English, Hindi and Hinglish.

Each rule returns a FLAG dict:
  { "id": str, "weight": int, "category": str,
    "spans": [(start, end), ...] }   ← character positions in original text
"""

import json
import re
import unicodedata
from pathlib import Path

from core.scoring import FLAG_WEIGHTS, FLAG_CATEGORIES

# ── Load keyword data ──────────────────────────────────────────────────────
_DATA = Path(__file__).parent.parent / "data"

def _load(filename: str) -> dict:
    with open(_DATA / filename, encoding="utf-8") as f:
        return json.load(f)

_KW_EN        = _load("keywords_en.json")
_KW_HI        = _load("keywords_hi.json")
_KW_HINGLISH  = _load("keywords_hinglish.json")

# ── Helpers ────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_spans(original: str, keyword: str) -> list[tuple[int, int]]:
    """
    Find all non-overlapping occurrences of keyword in original (case-insensitive).
    Returns list of (start, end) tuples on the ORIGINAL string.
    """
    spans = []
    lower_original = original.lower()
    lower_kw = keyword.lower()
    start = 0
    while True:
        pos = lower_original.find(lower_kw, start)
        if pos == -1:
            break
        spans.append((pos, pos + len(lower_kw)))
        start = pos + len(lower_kw)
    return spans


def _scan_keyword_dict(original: str, normalised: str, kw_dict: dict) -> list[dict]:
    """
    Scan a keyword dictionary against the text.
    Returns one flag per matched category (union of all spans for that category).
    """
    flags: dict[str, dict] = {}

    for category, data in kw_dict.items():
        flag_id = data["flag_id"]
        all_spans: list[tuple[int, int]] = []

        for kw in data["keywords"]:
            kw_norm = _normalise(kw)
            if kw_norm in normalised:
                spans = _find_spans(original, kw)
                all_spans.extend(spans)

        if all_spans:
            if flag_id not in flags:
                flags[flag_id] = {
                    "id": flag_id,
                    "weight": FLAG_WEIGHTS.get(flag_id, data.get("weight", 10)),
                    "category": FLAG_CATEGORIES.get(flag_id, category),
                    "spans": [],
                }
            flags[flag_id]["spans"].extend(all_spans)

    return list(flags.values())


# ── Language detection ─────────────────────────────────────────────────────
# Very lightweight heuristic — full Unicode analysis is expensive and
# unnecessary given our domain. Order matters: Hindi script → "hi";
# ASCII + Hindi words → "hinglish"; otherwise → "en".

_HINDI_SCRIPT_RE = re.compile(r"[\u0900-\u097F]")

# Words that ONLY occur in transliterated Hindi, not in standard English.
# Requiring >=2 matches avoids false positives on English text.
_HINGLISH_ONLY_WORDS = re.compile(
    r"\b(karo|karein|karna|hai|hain|nahi|nahin|aur|ka|ki|ke|"
    r"mein|par|yeh|woh|aap|hum|tum|bhi|kya|kyun|kaise|"
    r"paisa|paise|rupaye|band|blok|turant|abhi|jaldi|"
    r"inaam|jeeta|jayega|hoga|batao|bhejo|milega|wapas|"
    r"seedha|fauran|tatkal|jaldi)\b",
    re.IGNORECASE,
)


def detect_language(text: str) -> str:
    if _HINDI_SCRIPT_RE.search(text):
        return "hi"
    # Need at least 2 Hinglish-only words to avoid false positives on English text.
    hinglish_hits = _HINGLISH_ONLY_WORDS.findall(text)
    if len(hinglish_hits) >= 2:
        return "hinglish"
    return "en"


# ── Public API ─────────────────────────────────────────────────────────────

def analyse_message(text: str) -> dict:
    """
    Run all keyword rules against text.
    Returns:
      { "flags": [...], "language": "en"|"hi"|"hinglish" }
    """
    language  = detect_language(text)
    normalised = _normalise(text)
    flags: list[dict] = []

    # Always run English rules (scammers mix languages)
    flags.extend(_scan_keyword_dict(text, normalised, _KW_EN))

    if language == "hi":
        flags.extend(_scan_keyword_dict(text, normalised, _KW_HI))
    elif language == "hinglish":
        flags.extend(_scan_keyword_dict(text, normalised, _KW_HINGLISH))
        # Also run English rules (Hinglish messages often contain English scam words)
    else:
        # Pure English — also try Hinglish keywords to catch mixed inputs
        flags.extend(_scan_keyword_dict(text, normalised, _KW_HINGLISH))

    # Deduplicate flags by id (merge spans)
    merged: dict[str, dict] = {}
    for f in flags:
        if f["id"] not in merged:
            merged[f["id"]] = f
        else:
            merged[f["id"]]["spans"].extend(f["spans"])

    # Deduplicate spans within each flag
    for f in merged.values():
        f["spans"] = list(dict.fromkeys(f["spans"]))

    return {
        "flags": list(merged.values()),
        "language": language,
    }
